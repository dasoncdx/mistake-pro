"""
错题Pro - 图像处理工具
文档展平 + 版面检测(PaddleOCR) + 手写擦除（本地 OpenCV）
"""

import cv2
import numpy as np

_layout_engine = None


def _get_layout_engine():
    """懒加载 PaddleOCR LayoutDetection，只初始化一次"""
    global _layout_engine
    if _layout_engine is None:
        from paddleocr import LayoutDetection
        _layout_engine = LayoutDetection()
    return _layout_engine


def flatten_page(image_bytes: bytes) -> bytes:
    """文档展平：透视矫正 + 对比度增强 + 锐化。失败时返回原图。"""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 高斯模糊降噪
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Canny 边缘检测
        edges = cv2.Canny(blurred, 50, 150)

        # 膨胀连接断边
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)

        # 找最大轮廓（文档区域）
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return _enhance(img, image_bytes)

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        doc_contour = None
        for c in contours[:5]:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                doc_contour = approx
                break

        if doc_contour is None:
            # 无四边形 → 不做透视矫正，只增强
            return _enhance(img, image_bytes)

        # 透视矫正
        pts = doc_contour.reshape(4, 2).astype(np.float32)
        rect = _order_points(pts)

        (tl, tr, br, bl) = rect
        width_a = np.linalg.norm(br - bl)
        width_b = np.linalg.norm(tr - tl)
        max_width = max(int(width_a), int(width_b))
        height_a = np.linalg.norm(tr - br)
        height_b = np.linalg.norm(tl - bl)
        max_height = max(int(height_a), int(height_b))

        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ], dtype=np.float32)

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (max_width, max_height))

        return _enhance(warped, image_bytes)

    except Exception:
        return image_bytes


def _order_points(pts):
    """按 左上/右上/右下/左下 排序四点"""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _enhance(img: np.ndarray, fallback_bytes: bytes) -> bytes:
    """对比度增强 + 锐化 + 尺寸限制，编码为 JPEG bytes"""
    try:
        h, w = img.shape[:2]
        max_dim = 2048
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        # CLAHE 对比度增强
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

        # 锐化
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        _, buf = cv2.imencode(".jpg", sharpened, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes()
    except Exception:
        return fallback_bytes


def detect_layout(image_bytes: bytes) -> list[dict]:
    """用 PaddleOCR PP-DocLayout 检测文字块区域。
    返回: [{"x1": 0.05, "y1": 0.10, "x2": 0.95, "y2": 0.25, "label": "text", "score": 0.88}, ...]
    坐标是比例值(0~1)，按 y 坐标从上到下排序。失败时返回空数组。
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return []
        h, w = img.shape[:2]

        # 保存临时文件（PaddleOCR 需要文件路径）
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            cv2.imwrite(f.name, img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            tmp_path = f.name

        try:
            engine = _get_layout_engine()
            result = engine.predict(tmp_path)
        finally:
            os.unlink(tmp_path)

        boxes = result[0].get('boxes', []) if isinstance(result, list) and result else []

        # 提取文字块坐标，过滤低置信度
        regions = []
        for box in boxes:
            coord = box['coordinate']
            x1, y1 = float(coord[0]), float(coord[1])
            x2, y2 = float(coord[2]), float(coord[3])
            score = float(box.get('score', 0))
            label = box.get('label', 'text')

            if score < 0.45:
                continue

            regions.append({
                'x1': round(max(0, x1) / w, 3),
                'y1': round(max(0, y1) / h, 3),
                'x2': round(min(w, x2) / w, 3),
                'y2': round(min(h, y2) / h, 3),
                'label': label,
                'score': round(score, 3),
            })

        regions.sort(key=lambda r: r['y1'])
        return regions
    except Exception:
        return []


def detect_question_regions(image_bytes: bytes) -> list[dict]:
    """检测题目区域——PaddleOCR 版面检测 + 大块细分 + 网格兜底。
    返回: [{"question_number": "1", "x1": 0.05, "y1": 0.10, "x2": 0.95, "y2": 0.25}, ...]
    坐标是比例值(0~1)。保证覆盖整个内容区域。
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return []
        h, w = img.shape

        # 先用 PaddleOCR 检测文字块
        layout_boxes = detect_layout(image_bytes)
        text_boxes = [b for b in layout_boxes if b['label'] in ('text', 'image')]

        # 如果 PaddleOCR 检测到足够的文字块，用版面结果 + 大块细分
        if len(text_boxes) >= 3:
            raw_regions = []
            for box in text_boxes:
                y1 = int(box['y1'] * h)
                y2 = int(box['y2'] * h)
                region_h = y2 - y1

                # 大块（>13% 页面）再细分
                if region_h > h * 0.13:
                    sub_count = max(2, int(region_h / (h * 0.10)))
                    sub_h = region_h / sub_count
                    for j in range(sub_count):
                        sy1 = int(y1 + j * sub_h)
                        sy2 = int(y1 + (j + 1) * sub_h)
                        if sy2 - sy1 > h / 100:
                            raw_regions.append((sy1, sy2))
                else:
                    raw_regions.append((y1, y2))
        else:
            raw_regions = []

        # PaddleOCR 结果可用，就用它（合并小碎片后）；否则用网格兜底
        if len(raw_regions) >= 3:
            # 只合并小碎片：gap 小 AND 至少一方是 tiny region
            raw_regions.sort(key=lambda r: r[0])
            merged = [raw_regions[0]]
            for y1, y2 in raw_regions[1:]:
                prev_y1, prev_y2 = merged[-1]
                gap = y1 - prev_y2
                prev_h = prev_y2 - prev_y1
                cur_h = y2 - y1
                tiny = h * 0.05
                if gap < h * 0.02 and (prev_h < tiny or cur_h < tiny):
                    merged[-1] = (prev_y1, max(prev_y2, y2))
                else:
                    merged.append((y1, y2))
            raw_regions = merged
        else:
            # 投影法找内容区域
            _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            row_text = np.sum(binary, axis=1) / 255 / w
            win = h // 30
            kernel = np.ones(win) / win
            row_smooth = np.convolve(row_text, kernel, mode='same')
            mean_val = np.mean(row_smooth)

            top = 0
            for i in range(h // 10, h):
                if row_smooth[i] > mean_val * 0.4:
                    top = max(0, i - h // 40)
                    break
            bottom = h
            for i in range(h - 1, h * 2 // 3, -1):
                if row_smooth[i] > mean_val * 0.4:
                    bottom = min(h, i + h // 40)
                    break
            content_h = bottom - top
            if content_h < h * 0.3:
                top, bottom = 0, h
                content_h = h

            target_h = h * 0.13
            target_count = max(5, min(10, int(content_h / target_h)))
            grid_h = content_h / target_count
            for i in range(target_count):
                y1 = int(top + i * grid_h)
                y2 = int(top + (i + 1) * grid_h)
                if y2 - y1 > h / 100:
                    raw_regions.append((y1, min(y2, bottom)))

        # 排序并去重
        raw_regions.sort(key=lambda r: r[0])
        final_regions = []
        for y1, y2 in raw_regions:
            if final_regions and y1 < final_regions[-1][1]:
                final_regions[-1] = (final_regions[-1][0], max(final_regions[-1][1], y2))
            else:
                final_regions.append((y1, y2))

        # 最终兜底：大块（>15%）再分一刀
        split_regions = []
        for y1, y2 in final_regions:
            if y2 - y1 > h * 0.15:
                mid = (y1 + y2) // 2
                split_regions.append((y1, mid))
                split_regions.append((mid, y2))
            else:
                split_regions.append((y1, y2))
        final_regions = split_regions

        # 生成输出
        regions = []
        x_margin = 0.04
        x_right = 0.96
        for i, (y1, y2) in enumerate(final_regions):
            regions.append({
                "question_number": str(i + 1),
                "label": "",
                "x1": round(x_margin, 3),
                "y1": round(y1 / h, 3),
                "x2": round(x_right, 3),
                "y2": round(y2 / h, 3),
            })

        return regions
    except Exception:
        return []


def erase_handwriting(image_bytes: bytes, regions: list[dict]) -> bytes:
    """根据手写区域坐标，用 inpaint 擦除手写。

    regions: [{"x1": float, "y1": float, "x2": float, "y2": float}, ...]
    坐标是比例值（0~1），会自动转换为像素坐标。
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None or not regions:
            return image_bytes

        h, w = img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        for r in regions:
            x1 = max(0, int(r["x1"] * w))
            y1 = max(0, int(r["y1"] * h))
            x2 = min(w, int(r["x2"] * w))
            y2 = min(h, int(r["y2"] * h))
            if x2 > x1 and y2 > y1:
                # 膨胀区域确保擦除完全
                cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)

        if cv2.countNonZero(mask) == 0:
            return image_bytes

        # 膨胀 mask 确保覆盖边缘
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)

        result = cv2.inpaint(img, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

        _, buf = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes()
    except Exception:
        return image_bytes

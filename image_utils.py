"""
错题Pro - 图像处理工具
文档展平 + 手写擦除（本地 OpenCV）
"""

import cv2
import numpy as np


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


def clean_question_crop(image_bytes: bytes) -> bytes:
    """擦除手写笔迹 + 展平增强。用连通分量统计识别印刷体 vs 手写体：
    图中绝大部分内容为印刷体（主导字体），连通分量尺寸集中在某个范围。
    尺寸/形状显著偏离主导范围的分量标记为手写体，擦除。
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 自适应二值化
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY_INV, 11, 3)

        # 连通分量分析
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(thresh, connectivity=8)

        # 收集每个分量特征，过滤极小噪点和超大色块
        comps = []
        for i in range(1, num_labels):
            a = stats[i, cv2.CC_STAT_AREA]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            if a < 15 or a > 8000 or w < 2 or h < 2:
                continue
            comps.append({'id': i, 'area': a, 'w': w, 'h': h,
                          'aspect': w / h if h > 0 else 1})

        if len(comps) < 20:
            return _enhance(img, image_bytes)

        # 用中位数找主导字符尺寸
        heights = np.array([c['h'] for c in comps])
        widths = np.array([c['w'] for c in comps])
        med_h = np.median(heights)
        med_w = np.median(widths)
        # 用中位数绝对偏差（MAD）衡量偏离程度
        mad_h = np.median(np.abs(heights - med_h)) + 1
        mad_w = np.median(np.abs(widths - med_w)) + 1

        # 标记偏离主导尺寸的分量为手写
        handwriting_mask = np.zeros(gray.shape, dtype=np.uint8)
        for c in comps:
            is_hw = False
            # 高度偏离 > 3x MAD
            if abs(c['h'] - med_h) / mad_h > 3.0:
                is_hw = True
            # 极度宽：连笔手写（宽 > 2.5x 主导宽 且 宽高比 > 3）
            if c['aspect'] > 2.8 and c['w'] > med_w * 1.8:
                is_hw = True
            # 密度过低（手写笔画稀疏不规则）
            density = c['area'] / (c['w'] * c['h']) if c['w'] * c['h'] > 0 else 0
            if density < 0.12 and c['area'] > 30:
                is_hw = True

            if is_hw:
                component_mask = (labels == c['id']).astype(np.uint8) * 255
                handwriting_mask = cv2.bitwise_or(handwriting_mask, component_mask)

        if cv2.countNonZero(handwriting_mask) > 0:
            kernel = np.ones((5, 5), np.uint8)
            handwriting_mask = cv2.dilate(handwriting_mask, kernel, iterations=1)
            handwriting_mask = cv2.morphologyEx(handwriting_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            img = cv2.inpaint(img, handwriting_mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

        return _enhance(img, image_bytes)
    except Exception:
        return image_bytes

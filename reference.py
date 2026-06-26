"""
教材目录解析器 — 读取 reference/{学科}/{年级}.docx 产出知识点列表。
"""

import re
import os
from docx import Document

_ROOT = os.path.dirname(os.path.abspath(__file__))

_cache: dict[str, list[dict]] = {}

GRADE_MAP = {
    "小一": "grade_1", "小二": "grade_2", "小三": "grade_3",
    "小四": "grade_4", "小五": "grade_5", "小六": "grade_6",
}


def _build_path(subject: str, grade: str) -> str:
    """根据学科+年级构造 docx 文件路径。"""
    grade_label_map = {
        "grade_1": "小一", "grade_2": "小二", "grade_3": "小三",
        "grade_4": "小四", "grade_5": "小五", "grade_6": "小六",
    }
    subject_dir = {"math": "数学", "english": "英语", "chinese": "语文"}.get(subject, subject)
    grade_label = grade_label_map.get(grade, "小四")
    return os.path.join(_ROOT, "reference", subject_dir, f"{grade_label}.docx")


def load_knowledge_points(subject: str, grade: str) -> list[dict]:
    """解析 docx 返回知识点列表。

    返回: [{"unit": "三角形", "topic": "三角形的内角和", "full": "三角形_三角形的内角和"}, ...]
    """
    cache_key = f"{subject}_{grade}"
    if cache_key in _cache:
        return _cache[cache_key]

    path = _build_path(subject, grade)
    try:
        doc = Document(path)
    except Exception:
        return []

    results: list[dict] = []
    current_unit = ""
    unit_pattern = re.compile(r"^\d+\s+\S")

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        if text.startswith("【"):
            continue
        if unit_pattern.match(text):
            current_unit = re.sub(r"^\d+\s+", "", text)
        elif current_unit:
            topic = text
            full = f"{current_unit}_{topic}"
            results.append({"unit": current_unit, "topic": topic, "full": full})

    _cache[cache_key] = results
    return results


def get_kp_names(subject: str, grade: str) -> list[str]:
    """返回 full name 列表，供 AI 匹配使用。"""
    return [kp["full"] for kp in load_knowledge_points(subject, grade)]


def clear_cache():
    _cache.clear()

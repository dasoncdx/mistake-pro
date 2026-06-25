"""
错题Pro - AI引擎
适配 OpenAI 兼容 API（DeepSeek）
"""

import json
import os
import re
from openai import OpenAI

from prompts import (
    SYSTEM_PROMPTS,
    diagnosis_prompt,
    variant_gen_prompt,
    answer_check_prompt,
)


def _get_vision_client() -> OpenAI:
    api_key = os.environ.get("VISION_API_KEY")
    if not api_key:
        raise RuntimeError("VISION_API_KEY 环境变量未设置")
    base_url = os.environ.get("VISION_BASE_URL", "https://api.siliconflow.cn/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def _get_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 环境变量未设置，请检查 .env 文件")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    return OpenAI(api_key=api_key, base_url=base_url)


def call_llm(system_prompt: str, user_prompt: str, model: str = "deepseek-chat") -> str:
    """调用 DeepSeek API，返回文本响应"""
    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        max_tokens=2048,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def _parse_json(text: str) -> dict | list:
    """从LLM返回的文本中提取JSON，带容错。使用json-repair处理畸形JSON。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        from json_repair import repair_json
        repaired = repair_json(text)
        return json.loads(repaired)
    except Exception:
        pass
    if text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
    elif text.startswith("["):
        match = re.search(r"\[.*\]", text, re.DOTALL)
    else:
        raise RuntimeError(f"无法解析JSON: {text[:200]}...")
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            from json_repair import repair_json
            return json.loads(repair_json(match.group(0)))
    raise RuntimeError(f"无法解析JSON: {text[:200]}...")


def analyze_crop(image_bytes: bytes, subject: str = "math", grade: str = "") -> dict:
    """一次 Vision API 调用：识别手写区域 + OCR提取文字 + 判断内容类型。
    返回 {"handwriting_regions": [...], "ocr_text": "...", "content_type": "pure_text|text_with_figure|mainly_figure"}
    """
    import base64
    client = _get_vision_client()
    model = os.environ.get("VISION_MODEL", "qwen-vl-max")
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    subject_name = {"math": "数学", "english": "英语", "chinese": "语文"}.get(subject, subject)

    response = client.chat.completions.create(
        model=model,
        max_tokens=2048,
        temperature=0.1,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    f"你是一位专业的教育OCR专家。请分析这张{grade}{subject_name}题目图片，完成三项任务：\n\n"
                    "任务1 - 识别手写笔迹区域：\n"
                    "找出学生手写的内容（答案、批注、涂改、草稿、填空处的笔迹）。手写体的特征：笔画粗细不一、排列不齐、字形不规则。\n"
                    "印刷体（原题文字、横线___、括号、表格线、插图）不是手写，不要标记。\n\n"
                    "任务2 - OCR提取题目原文：\n"
                    "逐字识别图片中的印刷文字，保留横线___、括号()、【】、选项A.B.C.D.等结构要素。\n"
                    "保留数学符号（∠⊥∥△□≌∽∴∵∈∪∩⊂⊃±×÷＝≠＜＞≤≥√∑∏∫∮∂∇）、分数、方程式。\n"
                    "英语题目保留大小写、标点、拼写。\n"
                    "排除学生手写答案和批改痕迹。\n\n"
                    "任务3 - 判断内容类型：\n"
                    "- pure_text: 纯文字题目，没有图\n"
                    "- text_with_figure: 图文混合（有插图、示意图、几何图、图表等），文字仍是主体\n"
                    "- mainly_figure: 主要是图（漫画、复杂几何图形、图表），文字仅辅助\n\n"
                    "返回一个JSON对象（不要markdown代码块，不要其他文字）：\n"
                    '{{"handwriting_regions":[{{"x1":0.1,"y1":0.2,"x2":0.3,"y2":0.4}}],"ocr_text":"完整题目文字","content_type":"pure_text"}}\n\n'
                    "坐标归一化到0-1范围，框紧紧贴合手写区域。没有手写则handwriting_regions为空数组[]。"
                )},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]
        }]
    )

    text = response.choices[0].message.content
    result = _parse_json(text)
    if isinstance(result, dict):
        regions = result.get("handwriting_regions", [])
        if isinstance(regions, list):
            regions = [r for r in regions if isinstance(r, dict) and all(k in r for k in ("x1","y1","x2","y2"))]
        return {
            "handwriting_regions": regions,
            "ocr_text": (result.get("ocr_text") or "").strip(),
            "content_type": result.get("content_type", "pure_text"),
        }
    return {"handwriting_regions": [], "ocr_text": "", "content_type": "pure_text"}


# ─── High-level Functions ───────────────────────────────────

def diagnose_mistake(problem: str, wrong_answer: str, grade_level: str,
                     curriculum: str = "人教版") -> dict:
    prompt = diagnosis_prompt(problem, wrong_answer, grade_level, curriculum)
    for attempt in range(3):
        try:
            response = call_llm(SYSTEM_PROMPTS["diagnosis"], prompt)
            result = _parse_json(response)
            for key in ["knowledge_point", "error_type", "error_analysis", "correct_answer"]:
                if key not in result:
                    raise KeyError(f"Missing key: {key}")
            if result["error_type"] not in ("knowledge_gap", "thinking_error", "careless"):
                result["error_type"] = "thinking_error"
            return result
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"AI诊断失败（重试3次后）: {e}")


def generate_variants(knowledge_point: str, error_type: str, error_analysis: str,
                      grade_level: str, curriculum: str = "人教版",
                      difficulty: str = "same", count: int = 3,
                      include_original: bool = False,
                      few_shot_examples: list[dict] = None) -> list[dict]:
    if few_shot_examples:
        from prompts import variant_gen_prompt_with_examples
        prompt = variant_gen_prompt_with_examples(knowledge_point, error_type, error_analysis,
                                                   grade_level, curriculum, difficulty, count,
                                                   few_shot_examples)
    else:
        prompt = variant_gen_prompt(knowledge_point, error_type, error_analysis,
                                    grade_level, curriculum, difficulty, count, include_original)
    for attempt in range(3):
        try:
            response = call_llm(SYSTEM_PROMPTS["variant_gen"], prompt)
            result = _parse_json(response)
            if not isinstance(result, list):
                raise TypeError("Expected JSON array")
            for item in result:
                if "problem" not in item or "correct_answer" not in item:
                    raise KeyError("Missing problem/correct_answer")
                if "difficulty" not in item:
                    item["difficulty"] = difficulty
            return result
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"变式题生成失败（重试3次后）: {e}")


def check_answer(problem: str, correct_answer: str, student_answer: str,
                 knowledge_point: str, error_analysis: str) -> dict:
    prompt = answer_check_prompt(problem, correct_answer, student_answer,
                                 knowledge_point, error_analysis)
    for attempt in range(3):
        try:
            response = call_llm(SYSTEM_PROMPTS["answer_check"], prompt)
            result = _parse_json(response)
            for key in ["is_correct", "feedback", "action_type"]:
                if key not in result:
                    raise KeyError(f"Missing key: {key}")
            result.setdefault("same_error_pattern", None)
            result.setdefault("hint", None)
            return result
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"批改失败（重试3次后）: {e}")

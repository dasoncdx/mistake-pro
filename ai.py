"""
错题Pro - AI引擎
适配 OpenAI 兼容 API（DeepSeek）
"""

import json
import os
import re
import base64
from openai import OpenAI

from prompts import (
    SYSTEM_PROMPTS,
    diagnosis_prompt,
    variant_gen_prompt,
    answer_check_prompt,
    ocr_diagnosis_prompt,
)


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
        temperature=0.3,  # 低温度保证JSON输出稳定
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def _parse_json(text: str) -> dict | list:
    """从LLM返回的文本中提取JSON，带容错"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if text.startswith("{"):
            match = re.search(r"\{.*\}", text, re.DOTALL)
        elif text.startswith("["):
            match = re.search(r"\[.*\]", text, re.DOTALL)
        else:
            raise
        if match:
            return json.loads(match.group(0))
        raise


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
                      include_original: bool = False) -> list[dict]:
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


def ocr_and_diagnose(image_path: str, grade_level: str,
                     curriculum: str = "人教版") -> dict:
    """OCR + 诊断（使用DeepSeek Vision，如不支持则退回纯文本）"""
    client = _get_client()

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "webp": "image/webp"}
    media_type = mime_map.get(ext, "image/png")

    prompt_text = ocr_diagnosis_prompt(grade_level, curriculum)

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=2048,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {
                            "url": f"data:{media_type};base64,{image_data}"
                        }},
                        {"type": "text", "text": prompt_text},
                    ],
                }],
            )
            result = _parse_json(response.choices[0].message.content)
            for key in ["ocr_problem", "ocr_student_answer", "knowledge_point",
                        "error_type", "error_analysis", "correct_answer"]:
                if key not in result:
                    raise KeyError(f"Missing key: {key}")
            return result
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"OCR诊断失败（重试3次后）: {e}")

"""
错题Pro - 知识点库引擎
负责知识点库的填充、匹配和例题检索
"""
import json
from ai import _get_client, _parse_json

GRADE_NAMES = {
    "grade_1": "一年级", "grade_2": "二年级", "grade_3": "三年级",
    "grade_4": "四年级", "grade_5": "五年级", "grade_6": "六年级",
    "grade_7": "七年级", "grade_8": "八年级", "grade_9": "九年级",
    "grade_10": "高一", "grade_11": "高二", "grade_12": "高三",
}
GRADE_LEVELS = list(GRADE_NAMES.keys())


def generate_knowledge_tree(grade_level: str, subject: str = "数学",
                            curriculum: str = "人教版") -> list[dict]:
    """Call DeepSeek to generate the full curriculum knowledge tree for one grade."""
    grade_name = GRADE_NAMES.get(grade_level, grade_level)
    prompt = f"""你是{curriculum}{grade_name}{subject}的教材编写专家。

请列出{curriculum}{grade_name}{subject}的所有教学单元，每个单元包含该单元所有知识点。

对于每个知识点：
1. 提供简短描述（1-2句话说明该知识点的核心内容）
2. 标注难度：basic(基础) / intermediate(中等) / advanced(较难)
3. 提供2-3道代表性例题，每道题包含：题目文本、正确答案、解题分析、难度

要求：
- 题目必须符合{grade_name}学生的认知水平和阅读能力
- 例题覆盖该知识点的不同考察角度
- 题目内容积极健康，符合社会主义核心价值观
- 严格遵循{curriculum}教学大纲

返回纯JSON数组（不要markdown代码块）：
[
  {{
    "unit": "第一单元 分数乘法",
    "knowledge_points": [
      {{
        "knowledge_point": "分数乘整数",
        "description": "理解分数乘整数的意义，掌握分数乘整数的计算方法",
        "difficulty_level": "basic",
        "example_questions": [
          {{"problem": "...", "correct_answer": "...", "analysis": "...", "difficulty": "basic"}},
          {{"problem": "...", "correct_answer": "...", "analysis": "...", "difficulty": "intermediate"}}
        ]
      }}
    ]
  }}
]"""
    client = _get_client()
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=8192, temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.choices[0].message.content.strip()
            result = _parse_json(raw)
            if not isinstance(result, list):
                raise TypeError("Expected JSON array")
            return result
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"知识树生成失败（重试3次后）: {e}")


def seed_knowledge_base(conn, grade_level: str, subject: str = "math",
                        curriculum: str = "人教版") -> dict:
    """Seed knowledge base for one grade. Returns {grade, units, kp_count}."""
    from db import upsert_knowledge_point

    tree = generate_knowledge_tree(grade_level, "数学", curriculum)
    total_kp = 0
    units = []

    for unit_data in tree:
        unit_name = unit_data.get("unit", "")
        for kp in unit_data.get("knowledge_points", []):
            upsert_knowledge_point(
                conn,
                subject=subject,
                grade_level=grade_level,
                curriculum_ver=curriculum,
                unit_name=unit_name,
                knowledge_point=kp.get("knowledge_point", ""),
                description=kp.get("description", ""),
                difficulty_level=kp.get("difficulty_level", "intermediate"),
                example_questions=kp.get("example_questions", [])
            )
            total_kp += 1
        units.append(unit_name)

    return {"grade": grade_level, "subject": subject, "units": len(units), "kp_count": total_kp}


def seed_all_grades(conn, subject: str = "math", curriculum: str = "人教版",
                    start_grade: str = "grade_1", end_grade: str = "grade_12") -> list[dict]:
    """Seed knowledge base for all grades. Returns list of per-grade results."""
    results = []
    start_idx = GRADE_LEVELS.index(start_grade)
    end_idx = GRADE_LEVELS.index(end_grade)
    for gl in GRADE_LEVELS[start_idx:end_idx + 1]:
        r = seed_knowledge_base(conn, gl, subject, curriculum)
        results.append(r)
        grade_name = GRADE_NAMES.get(gl, gl)
        print(f"  ✅ {grade_name}: {r['kp_count']}个知识点, {r['units']}个单元", flush=True)
    return results


def expand_knowledge_point(conn, knowledge_point: str, grade_level: str,
                           subject: str = "math", curriculum: str = "人教版") -> dict:
    """On-demand: generate example questions for a new knowledge point."""
    from db import upsert_knowledge_point
    grade_name = GRADE_NAMES.get(grade_level, grade_level)

    prompt = f"""为{curriculum}{grade_name}{subject}知识点「{knowledge_point}」设计3道代表性例题。

要求：
- 题目必须符合{grade_name}学生的认知水平
- 覆盖该知识点的不同考察角度（基础计算、应用题、变式）
- 每道题提供：题目文本、正确答案、解题分析、难度(basic/intermediate/advanced)
- 严格遵循{curriculum}教学大纲
- 题目内容积极健康

返回纯JSON数组（不要markdown代码块）：
[
  {{"problem": "...", "correct_answer": "...", "analysis": "...", "difficulty": "basic"}},
  ...
]"""
    client = _get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        max_tokens=2048, temperature=0.3,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    examples = _parse_json(raw)

    upsert_knowledge_point(
        conn,
        subject=subject,
        grade_level=grade_level,
        curriculum_ver=curriculum,
        unit_name="按需扩展",
        knowledge_point=knowledge_point,
        description="",
        difficulty_level="intermediate",
        example_questions=examples
    )
    return {"knowledge_point": knowledge_point, "example_questions": examples}


def match_knowledge_point(conn, knowledge_point: str, grade_level: str = None,
                          subject: str = "math") -> dict | None:
    """Match a diagnosed knowledge point to the knowledge base.
    Returns the KB entry with parsed example_questions, or None if not found."""
    from db import search_knowledge_point
    entry = search_knowledge_point(conn, knowledge_point, grade_level, subject)
    if not entry and grade_level:
        # Try fuzzy: search without grade level restriction
        entry = search_knowledge_point(conn, knowledge_point, None, subject)
    if entry and entry.get('example_questions'):
        try:
            entry['example_questions'] = json.loads(entry['example_questions'])
        except (json.JSONDecodeError, TypeError):
            entry['example_questions'] = []
    return entry


def get_few_shot_examples(conn, knowledge_point: str, grade_level: str = None,
                          subject: str = "math", max_examples: int = 3) -> list[dict]:
    """Get example questions for few-shot variant generation.
    If knowledge point not in KB, triggers on-demand expansion."""
    entry = match_knowledge_point(conn, knowledge_point, grade_level, subject)
    if not entry:
        if grade_level:
            entry = expand_knowledge_point(conn, knowledge_point, grade_level, subject)
        else:
            return []
    examples = entry.get('example_questions', []) if isinstance(entry, dict) else []
    if isinstance(examples, list):
        return examples[:max_examples]
    return []


def get_kb_stats(conn, subject: str = "math") -> dict:
    """Get stats about the knowledge base."""
    row = conn.execute(
        "SELECT COUNT(*) as total, COUNT(DISTINCT grade_level) as grades FROM knowledge_base WHERE subject=?",
        (subject,)).fetchone()
    return {"total_kp": row['total'], "grades_covered": row['grades']}

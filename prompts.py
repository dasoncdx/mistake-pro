"""
错题Pro - AI Prompt 模板
每个函数接收参数，返回格式化的prompt字符串。
"""

# ─── System Prompts ─────────────────────────────────────────

SYSTEM_PROMPTS = {
    "diagnosis": (
        "你是一位有20年经验的数学教师，擅长错误分析和知识点定位。"
        "你只输出合法的JSON对象，不输出其他任何文字。"
    ),
    "variant_gen": (
        "你是一位创意数学题设计师，善于针对特定知识盲区设计变式练习题。"
        "你只输出合法的JSON数组，不输出其他任何文字。"
    ),
    "answer_check": (
        "你是一位温暖、鼓励的数学导师。"
        "你给出具体、可操作的反馈（2-4句话），始终输出合法的JSON对象。"
    ),
    "ocr_diagnosis": (
        "你是一位教育经验丰富的数学教师。"
        "你先识别图片中的题目文字和学生答案，再对错误进行诊断分析。"
        "你只输出合法的JSON对象。"
    ),
}


# ─── Diagnosis Prompt ───────────────────────────────────────

def diagnosis_prompt(problem: str, wrong_answer: str, grade_level: str,
                     curriculum: str = "人教版") -> str:
    return f"""请分析以下学生的错误。

=== 学生信息 ===
年级：{grade_level}
教材版本：{curriculum}

=== 错题 ===
题目：{problem}
学生的错误答案：{wrong_answer}

=== 你的任务 ===
1. 确定这道题考察的精确知识点（如"分数的通分""两位数乘一位数的进位乘法"）。请具体到单元级别。
2. 判断错误类型，必须从以下三个中选择一个：
   - knowledge_gap：学生从根本上没理解这个概念
   - thinking_error：学生理解概念但思路或方法选错了
   - careless：思路正确但计算/读题过程中粗心出错
3. 写一段分析（给系统和家长看的，不会展示给学生）：学生具体的思维偏差是什么？
4. 给出正确答案。

=== 输出格式 ===
只返回JSON，不要markdown代码块：
{{"knowledge_point": "...", "error_type": "knowledge_gap|thinking_error|careless", "error_analysis": "...", "correct_answer": "..."}}"""


# ─── Variant Generation Prompt ──────────────────────────────

def variant_gen_prompt(knowledge_point: str, error_type: str, error_analysis: str,
                       grade_level: str, curriculum: str = "人教版",
                       difficulty: str = "same", count: int = 3,
                       include_original: bool = False) -> str:
    original_hint = ""
    if include_original:
        original_hint = "- 可以穿插1道与目标知识点直接相关的真题/经典题，帮助学生练熟真题。"

    return f"""请为一位{grade_level}学生（{curriculum}）设计{count}道变式练习题。

=== 背景 ===
目标知识点：{knowledge_point}
学生的错误类型：{error_type}
错误分析：{error_analysis}

=== 设计要求 ===
{original_hint}
- 难度：{difficulty}
- 改变题目场景、人物、具体数字、表述方式
- 保持同一个知识点的考察核心不变
- 题目彼此之间要有明显差异（不能只改数字）
- 适合{grade_level}学生的阅读和理解水平
- 题目内容积极健康，符合社会主义核心价值观

=== 输出格式 ===
只返回JSON数组，不要markdown代码块：
[{{"problem": "题目文本", "correct_answer": "正确答案", "difficulty": "{difficulty}"}}]"""


# ─── Answer Check Prompt ────────────────────────────────────

def answer_check_prompt(problem: str, correct_answer: str, student_answer: str,
                        knowledge_point: str, error_analysis: str) -> str:
    return f"""请评价学生的作答。

=== 题目 ===
{problem}
正确答案：{correct_answer}

=== 学生作答 ===
学生的答案：{student_answer}

=== 背景 ===
知识点：{knowledge_point}
该学生此前在这个知识点上犯过的错误模式：{error_analysis}

=== 你的任务 ===
1. 判断答案是否正确。要接受等价的表达形式（如0.5 = 1/2 = 50%）。
2. 如果答案是错误的：
   - 判断是否重复了之前描述的错误模式（same_error_pattern）
   - 写2-4句鼓励性的反馈，指出思考方向但不直接给出答案，以一个问题收尾引导学生
   - 提供一个具体的提示（hint），帮助学生找到正确路径
3. 如果答案是正确的：
   - same_error_pattern 设为 null
   - 写2-4句具体的表扬，指出学生对哪个概念或步骤理解得好
   - hint 设为 null
4. 反馈中不要出现任何暗示"你上次也错了""这是你之前错过的题"的表述
5. 根据作答质量给出 action_type：
   - "perfect"：完全正确且过程清晰
   - "correct"：答案正确
   - "wrong"：答案错误，和新错误有关
   - "same_error"：答案错误，且重复了之前的错误模式

=== 输出格式 ===
只返回JSON：
{{"is_correct": true/false, "same_error_pattern": true/false/null, "feedback": "...", "hint": "...或null", "action_type": "perfect|correct|wrong|same_error"}}"""


# ─── OCR + Diagnosis Prompt ─────────────────────────────────

def ocr_diagnosis_prompt(grade_level: str, curriculum: str = "人教版") -> str:
    return f"""请仔细观察这张图片，它是一道学生做错的数学题。

=== 第一步：OCR识别 ===
从图片中提取：
1. 题目的完整文字内容
2. 学生写在图片中的答案（可能是手写的，请尽可能准确识别）

=== 第二步：错因诊断 ===
基于识别出的题目和错误答案，进行诊断：
1. 确定这道题考察的精确知识点
2. 判断错误类型（knowledge_gap | thinking_error | careless）
3. 分析具体的思维偏差
4. 给出正确答案

=== 学生信息 ===
年级：{grade_level}
教材版本：{curriculum}

=== 输出格式 ===
只返回JSON：
{{
  "ocr_problem": "识别到的题目文字",
  "ocr_student_answer": "识别到的学生答案",
  "knowledge_point": "...",
  "error_type": "knowledge_gap|thinking_error|careless",
  "error_analysis": "...",
  "correct_answer": "..."
}}"""

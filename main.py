"""
错题Pro - 工作流编排
Phase 1 核心闭环：诊断 → 变式生成 → 批改 → 存储
"""

import os
import sys
import json
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from db import (
    init_db, get_conn,
    insert_mistake, get_mistake, list_mistakes, update_pool_status,
    insert_variant, get_variant, get_variants_for_mistake,
    insert_attempt, get_attempts_for_variant, get_recent_attempts,
    upsert_mastery, get_mastery, get_all_masteries, get_due_reviews,
    update_mastery_review,
)
from ai import diagnose_mistake, generate_variants, check_answer
from scheduler import determine_pool_transition, plan_review_session
from auth import load_profile

# 项目根
ROOT = os.path.dirname(os.path.abspath(__file__))

# 当前活跃学生名（登录后设置）
_current_student: str = None


def get_student() -> str:
    if not _current_student:
        raise RuntimeError("未登录")
    return _current_student


def set_student(name: str):
    global _current_student
    _current_student = name


# ─── 工作流 ─────────────────────────────────────────────────

def workflow_new_mistake(problem: str, wrong_answer: str,
                         subject: str = "math") -> dict:
    """
    录入新错题 → AI诊断 → 存储 → 生成变式题 → 存储
    返回完整的诊断结果 + 变式题列表
    """
    student = get_student()
    profile = load_profile()
    grade = profile.get("grade_level", "grade_4")
    curriculum = profile.get("curriculum_version", "人教版")

    # Step 1: AI诊断
    diagnosis = diagnose_mistake(problem, wrong_answer, grade, curriculum)

    # Step 2: 存入 mistakes
    conn = get_conn(student)
    mistake_id = insert_mistake(conn,
        subject=subject,
        original_problem=problem,
        wrong_answer=wrong_answer,
        correct_answer=diagnosis.get("correct_answer", ""),
        knowledge_point=diagnosis["knowledge_point"],
        error_type=diagnosis["error_type"],
        error_analysis=diagnosis["error_analysis"],
        pool_status="active",
        grade_level=grade,
        curriculum_ver=curriculum,
    )

    # Step 3: 生成变式题
    variants_raw = generate_variants(
        knowledge_point=diagnosis["knowledge_point"],
        error_type=diagnosis["error_type"],
        error_analysis=diagnosis["error_analysis"],
        grade_level=grade,
        curriculum=curriculum,
        difficulty="easy",  # 首题偏易
        count=3,
    )

    # Step 4: 存入 variants（前2道 easy, 第3道 same）
    difficulties = ["easy", "easy", "same"]
    variants_saved = []
    for i, v in enumerate(variants_raw):
        diff = difficulties[i] if i < len(difficulties) else "same"
        vid = insert_variant(conn,
            mistake_id=mistake_id,
            problem_text=v["problem"],
            correct_answer=v["correct_answer"],
            difficulty=diff,
        )
        variants_saved.append({"id": vid, **v, "difficulty": diff})

    conn.close()

    return {
        "mistake_id": mistake_id,
        "diagnosis": diagnosis,
        "variants": variants_saved,
    }


def workflow_solve_variant(variant_id: int, student_answer: str) -> dict:
    """
    学生作答一道变式题 → AI批改 → 存储 → 更新掌握度
    """
    student = get_student()
    conn = get_conn(student)

    # 获取变式题
    variant = get_variant(conn, variant_id)
    if not variant:
        conn.close()
        raise ValueError(f"变式题不存在: {variant_id}")

    # 获取关联的错题（用于error_analysis上下文）
    mistake = get_mistake(conn, variant["mistake_id"])
    if not mistake:
        conn.close()
        raise ValueError(f"错题不存在: {variant['mistake_id']}")

    # AI批改
    result = check_answer(
        problem=variant["problem_text"],
        correct_answer=variant["correct_answer"],
        student_answer=student_answer,
        knowledge_point=mistake["knowledge_point"],
        error_analysis=mistake["error_analysis"],
    )

    # 存储作答记录
    attempt_id = insert_attempt(conn,
        variant_id=variant_id,
        student_answer=student_answer,
        is_correct=1 if result["is_correct"] else 0,
        same_error=1 if result.get("same_error_pattern") else 0,
        feedback=result["feedback"],
        hint=result.get("hint"),
        action_type=result.get("action_type", "correct"),
    )

    # 更新掌握度
    mastery = upsert_mastery(conn,
        knowledge_point=mistake["knowledge_point"],
        subject=mistake.get("subject", "math"),
        is_correct=result["is_correct"],
    )

    # 判断池状态转换
    new_pool, next_review = determine_pool_transition(
        current_pool=mistake["pool_status"],
        is_correct=result["is_correct"],
        consecutive_correct=mastery["streak"],
        mastery_score=mastery["mastery_score"],
    )

    if new_pool != mistake["pool_status"]:
        update_pool_status(conn, mistake["id"], new_pool)
    if next_review:
        update_mastery_review(conn, mastery["knowledge_point"],
                             mistake.get("subject", "math"), next_review, new_pool)

    conn.close()

    return {
        "attempt_id": attempt_id,
        "result": result,
        "mastery": mastery,
        "pool_transition": f"{mistake['pool_status']} → {new_pool}",
    }


def workflow_daily_review(subject: str = "math") -> dict:
    """
    每日复习：获取到期知识点 → 计划出题 → 生成变式 → 返回题目列表
    """
    student = get_student()
    profile = load_profile()
    grade = profile.get("grade_level", "grade_4")
    curriculum = profile.get("curriculum_version", "人教版")
    conn = get_conn(student)

    due_kps = get_due_reviews(conn, subject)
    if not due_kps:
        conn.close()
        return {"due_count": 0, "questions": [], "message": "今日无可复习知识点"}

    plan = plan_review_session(due_kps, max_questions=5)

    all_questions = []
    for item in plan:
        kp = item["knowledge_point"]
        # 找一个该知识点的活跃错题
        mistakes = list_mistakes(conn, subject=subject, knowledge_point=kp,
                                 pool_status="active", limit=1)
        if not mistakes:
            mistakes = list_mistakes(conn, subject=subject, knowledge_point=kp, limit=1)
        if not mistakes:
            continue

        m = mistakes[0]
        difficulty = "easy" if item["pool_status"] == "active" else "same"

        variants_raw = generate_variants(
            knowledge_point=kp,
            error_type=m["error_type"],
            error_analysis=m["error_analysis"],
            grade_level=grade,
            curriculum=curriculum,
            difficulty=difficulty,
            count=item["count"],
            include_original=(item["pool_status"] == "dormant"),
        )

        for v in variants_raw:
            vid = insert_variant(conn,
                mistake_id=m["id"],
                problem_text=v["problem"],
                correct_answer=v["correct_answer"],
                difficulty=v.get("difficulty", difficulty),
            )
            all_questions.append({
                "variant_id": vid,
                "problem": v["problem"],
                "difficulty": v.get("difficulty", difficulty),
                "knowledge_point": kp,
                "pool_status": item["pool_status"],
            })

    conn.close()
    return {"due_count": len(due_kps), "questions": all_questions,
            "plan": plan, "message": None}


# ─── 报告 ───────────────────────────────────────────────────

def workflow_progress_report(subject: str = "math") -> dict:
    """生成学习进度报告"""
    student = get_student()
    conn = get_conn(student)

    masteries = get_all_masteries(conn, subject)
    active_count = len(list_mistakes(conn, subject=subject, pool_status="active"))
    observing_count = len(list_mistakes(conn, subject=subject, pool_status="observing"))
    dormant_count = len(list_mistakes(conn, subject=subject, pool_status="dormant"))

    # 整体掌握度
    if masteries:
        overall = sum(m["mastery_score"] for m in masteries) / len(masteries)
    else:
        overall = 0.0

    conn.close()
    return {
        "overall_mastery": round(overall, 2),
        "total_knowledge_points": len(masteries),
        "pool_breakdown": {"active": active_count, "observing": observing_count, "dormant": dormant_count},
        "masteries": masteries,
    }

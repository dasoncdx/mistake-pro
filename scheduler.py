"""
错题Pro - 调度模块
间隔重复 + 分层退出 + 复习出题计划
"""

from datetime import datetime, timedelta


# ─── 间隔表 ─────────────────────────────────────────────────

INTERVALS = {0: 1, 1: 3, 2: 7, 3: 14, 4: 21, 5: 30}
# streak 5+ → 30天


def calculate_next_review(streak: int, mastery_score: float) -> str:
    """
    计算下次复习日期（返回 ISO 日期字符串）
    """
    interval = INTERVALS.get(streak, 30)

    if mastery_score < 0.3:
        interval = max(1, interval // 2)
    elif mastery_score > 0.8:
        interval = int(interval * 1.5)

    next_date = datetime.now() + timedelta(days=interval)
    return next_date.strftime("%Y-%m-%d %H:%M:%S")


# ─── 分层退出判定 ───────────────────────────────────────────

def determine_pool_transition(
    current_pool: str,
    is_correct: bool,
    consecutive_correct: int,
    mastery_score: float
) -> tuple[str, str | None]:
    """
    判断池状态转换。
    返回: (新池, 下次复习日期)
    """
    if current_pool == "active":
        if is_correct and consecutive_correct >= 3:
            return "observing", calculate_next_review(consecutive_correct, mastery_score)
        elif is_correct:
            return "active", calculate_next_review(consecutive_correct, mastery_score)
        else:
            return "active", calculate_next_review(0, mastery_score)

    elif current_pool == "observing":
        if is_correct and consecutive_correct >= 2:
            return "dormant", calculate_next_review(5, mastery_score)  # 长间隔
        elif is_correct:
            return "observing", calculate_next_review(consecutive_correct + 1, mastery_score)
        else:
            # 下滑，回到活跃
            return "active", calculate_next_review(0, mastery_score)

    elif current_pool == "dormant":
        if is_correct:
            return "dormant", calculate_next_review(6, mastery_score)  # 更长的间隔
        else:
            # 假掌握，重新激活
            return "active", calculate_next_review(0, mastery_score)

    return current_pool, None


# ─── 复习出题计划 ───────────────────────────────────────────

def plan_review_session(due_kps: list[dict], max_questions: int = 5) -> list[dict]:
    """
    输入: 到期待复习的知识点列表
    输出: [{"knowledge_point": ..., "count": ..., "pool_status": ...}, ...]

    规则:
    - 每次会话3-5道题
    - active池优先，每个1-3道
    - observing池每个1道
    """
    plan = []
    remaining = max_questions

    active_kps = [kp for kp in due_kps if kp.get("pool_status") == "active"]
    observing_kps = [kp for kp in due_kps if kp.get("pool_status") == "observing"]

    # active 优先
    for kp in active_kps:
        if remaining <= 0:
            break
        count = min(3, remaining)
        plan.append({
            "knowledge_point": kp.get("knowledge_point", kp.get("kp")),
            "count": count,
            "pool_status": "active",
        })
        remaining -= count

    # observing 每个1道
    for kp in observing_kps:
        if remaining <= 0:
            break
        plan.append({
            "knowledge_point": kp.get("knowledge_point", kp.get("kp")),
            "count": 1,
            "pool_status": "observing",
        })
        remaining -= 1

    return plan


# ─── 掌握度计算 ─────────────────────────────────────────────

def compute_mastery(total_attempts: int, correct_attempts: int,
                    recent_results: list[bool]) -> float:
    """加权掌握度：近期权重0.7，历史权重0.3"""
    if total_attempts == 0:
        return 0.0

    recent_ratio = sum(recent_results) / len(recent_results) if recent_results else 0
    historical_ratio = correct_attempts / total_attempts

    return round(0.7 * recent_ratio + 0.3 * historical_ratio, 2)

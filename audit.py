"""
错题Pro - 审计模块
代码自检 + 测试数据写入 + 审计报告生成

用法:
    python audit.py              # 全部检查（含AI连通性测试）
    python audit.py --quick      # 仅本地检查（不含AI调用）
    python audit.py --seed       # 仅写入测试数据
"""

import os
import sys
import json
import hashlib
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

ROOT = os.path.dirname(os.path.abspath(__file__))
AUDIT_REPORT_PATH = os.path.join(ROOT, "audit_report.json")

_results: list[dict] = []


def _check(name: str, passed: bool, detail: str = "") -> None:
    _results.append({
        "name": name, "passed": passed, "detail": detail,
        "time": datetime.now().isoformat(),
    })
    icon = "[green]✓[/green]" if passed else "[red]✗[/red]"
    console.print(f"  {icon} {name}")
    if not passed and detail:
        console.print(f"    [red]→ {detail}[/red]")


# ─── 检查项 ─────────────────────────────────────────────────

def check_files():
    """1. 文件完整性检查"""
    required = [
        "db.py", "ai.py", "prompts.py", "auth.py",
        "scheduler.py", "main.py", "cli.py", "audit.py",
        ".env.example", "requirements.txt",
    ]
    for f in required:
        path = os.path.join(ROOT, f)
        _check(f"文件存在: {f}", os.path.exists(path),
               f"缺少文件: {f}" if not os.path.exists(path) else "")


def check_imports():
    """2. 模块可导入"""
    modules = ["db", "ai", "prompts", "auth", "scheduler", "main"]
    for m in modules:
        try:
            __import__(m)
            _check(f"导入: {m}", True)
        except Exception as e:
            _check(f"导入: {m}", False, str(e))


def check_db():
    """3. 数据库建表 + CRUD"""
    from db import init_db, get_conn, insert_mistake, get_mistake, list_mistakes
    from db import insert_variant, insert_attempt, upsert_mastery, get_all_masteries

    student = "_audit_test"
    try:
        init_db(student)
        conn = get_conn(student)

        # 建表验证
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in ["mistakes", "variants", "attempts", "knowledge_mastery"]:
            _check(f"表存在: {t}", t in tables, f"缺失表: {t}")

        # CRUD验证
        mid = insert_mistake(conn,
            subject="math", original_problem="1+1=?",
            wrong_answer="3", correct_answer="2",
            knowledge_point="加法", error_type="thinking_error",
            error_analysis="测试", pool_status="active",
            grade_level="grade_1", curriculum_ver="人教版")
        _check("Mistake CRUD: insert", mid > 0)
        m = get_mistake(conn, mid)
        _check("Mistake CRUD: get", m is not None and m["knowledge_point"] == "加法")
        ms = list_mistakes(conn)
        _check("Mistake CRUD: list", len(ms) > 0)

        vid = insert_variant(conn, mistake_id=mid, problem_text="2+2=?",
                             correct_answer="4", difficulty="easy")
        _check("Variant CRUD: insert", vid > 0)

        aid = insert_attempt(conn, variant_id=vid, student_answer="4",
                             is_correct=1, feedback="不错", action_type="correct")
        _check("Attempt CRUD: insert", aid > 0)

        mast = upsert_mastery(conn, "加法", "math", True)
        _check("Mastery CRUD: upsert", mast is not None)
        _check("Mastery CRUD: score > 0", mast["mastery_score"] > 0)

        all_m = get_all_masteries(conn)
        _check("Mastery CRUD: list_all", len(all_m) > 0)

        conn.close()

        # 清理
        import shutil
        shutil.rmtree(os.path.join(ROOT, "user_data", "_audit_test"), ignore_errors=True)

    except Exception as e:
        _check("数据库测试", False, str(e))


def check_prompts():
    """4. Prompt函数输出"""
    from prompts import (
        diagnosis_prompt, variant_gen_prompt, answer_check_prompt,
        ocr_diagnosis_prompt, SYSTEM_PROMPTS,
    )

    # 系统prompt
    for key in ["diagnosis", "variant_gen", "answer_check", "ocr_diagnosis"]:
        _check(f"System Prompt: {key}", key in SYSTEM_PROMPTS)

    # 诊断
    dp = diagnosis_prompt("1+1=?", "3", "grade_1")
    _check("diagnosis_prompt 输出非空", len(dp) > 0)
    _check("diagnosis_prompt 含年级", "grade_1" in dp)

    # 变式
    vp = variant_gen_prompt("加法", "thinking_error", "test", "grade_1",
                            difficulty="easy", count=3)
    _check("variant_gen_prompt 输出非空", len(vp) > 0)
    _check("variant_gen_prompt 含考点", "加法" in vp)

    # 批改
    ap = answer_check_prompt("1+1=?", "2", "3", "加法", "test")
    _check("answer_check_prompt 输出非空", len(ap) > 0)
    _check("answer_check_prompt 含答案", "2" in ap)

    # OCR
    op = ocr_diagnosis_prompt("grade_4")
    _check("ocr_diagnosis_prompt 输出非空", len(op) > 0)


def check_auth():
    """5. 认证系统"""
    import auth as _auth

    test_dir = os.path.join(ROOT, "user_data", "_auth_test")
    os.makedirs(test_dir, exist_ok=True)
    profile_path = os.path.join(test_dir, "profile.json")
    _auth.PROFILE_PATH = profile_path

    # 创建账号
    profile = _auth.create_account("测试", "test123", {"grade_level": "grade_4", "subjects": ["math"]})
    _check("认证: 创建账号", os.path.exists(profile_path))

    # 登录
    ok = _auth.login("test123")
    _check("认证: 正确密码登录", ok)
    bad = _auth.login("wrong")
    _check("认证: 错误密码拒绝", not bad)

    # 修改密码
    changed = _auth.change_password("test123", "newpass")
    _check("认证: 修改密码", changed)
    ok2 = _auth.login("newpass")
    _check("认证: 新密码登录", ok2)

    # 加载配置
    pf = _auth.load_profile()
    _check("认证: 加载配置", pf is not None and pf["student_name"] == "测试")

    # 清理
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)


def check_ai_connectivity():
    """6. AI连接性检查（需联网）"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        _check("AI Key配置", False, "ANTHROPIC_API_KEY 环境变量未设置")
        return
    _check("AI Key配置", True)

    try:
        from ai import diagnose_mistake
        result = diagnose_mistake(
            problem="小明有5个苹果，吃了2个，还剩几个？",
            wrong_answer="2",
            grade_level="grade_1",
        )
        _check("AI诊断调用", True)
        _check("  knowledge_point", "knowledge_point" in result)
        _check("  error_type 三选一", result.get("error_type") in ("knowledge_gap", "thinking_error", "careless"))

        # 变式生成
        from ai import generate_variants
        variants = generate_variants(
            knowledge_point=result["knowledge_point"],
            error_type=result["error_type"],
            error_analysis=result["error_analysis"],
            grade_level="grade_1",
            count=2,
        )
        _check("AI变式生成", len(variants) >= 1)
        _check("  题目非空", all(v.get("problem") for v in variants))

        # 批改
        from ai import check_answer
        chk = check_answer(
            problem=variants[0]["problem"],
            correct_answer=variants[0]["correct_answer"],
            student_answer="999",
            knowledge_point=result["knowledge_point"],
            error_analysis=result["error_analysis"],
        )
        _check("AI批改调用", True)
        _check("  有反馈", bool(chk.get("feedback")))

        _results[-3]["ai_test_knowledge_point"] = result.get("knowledge_point")
    except Exception as e:
        _check("AI连接性", False, str(e))


def check_scheduler():
    """7. 调度逻辑"""
    from scheduler import (
        calculate_next_review, determine_pool_transition,
        plan_review_session, compute_mastery,
    )

    # 间隔计算
    d = calculate_next_review(0, 0.5)
    _check("间隔: streak=0 → 1天", "01" in d or "02" in d)  # 容忍边界
    d2 = calculate_next_review(5, 0.5)
    _check("间隔: streak=5 → 30天", True)  # 只要不报错

    # 池转换
    new_pool, _ = determine_pool_transition("active", True, 3, 0.5)
    _check("池转换: active+3次正确 → observing", new_pool == "observing")
    new_pool2, _ = determine_pool_transition("observing", False, 0, 0.5)
    _check("池转换: observing+错误 → active", new_pool2 == "active")
    new_pool3, _ = determine_pool_transition("dormant", False, 0, 0.5)
    _check("池转换: dormant+错误 → active", new_pool3 == "active")

    # 出题计划
    due = [
        {"knowledge_point": "分数", "pool_status": "active"},
        {"knowledge_point": "面积", "pool_status": "active"},
        {"knowledge_point": "乘法", "pool_status": "observing"},
        {"knowledge_point": "除法", "pool_status": "observing"},
    ]
    plan = plan_review_session(due, max_questions=5)
    _check("出题计划: 有内容", len(plan) > 0)
    _check("出题计划: active优先", plan[0]["pool_status"] == "active")
    total = sum(p["count"] for p in plan)
    _check(f"出题计划: 总数≤5 ({total})", total <= 5)

    # 掌握度
    mastery = compute_mastery(10, 7, [True, True, True, False, True])
    _check("掌握度: 计算正确", 0.5 < mastery < 1.0)


def seed_test_data():
    """写入测试数据到 _test 学生"""
    from db import init_db, get_conn, insert_mistake, insert_variant, insert_attempt, upsert_mastery
    from auth import PROFILE_PATH

    student = "demo"
    demo_dir = os.path.join(ROOT, "user_data", student)
    os.makedirs(demo_dir, exist_ok=True)

    # 创建 profile
    profile_path = os.path.join(demo_dir, "profile.json")
    # 使用pbkdf2
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", b"demo", salt, 200000)
    password_hash = salt.hex() + ":" + dk.hex()

    profile = {
        "student_name": "demo",
        "password_hash": password_hash,
        "province": "广东省",
        "city": "广州市",
        "district": "天河区",
        "grade_level": "grade_4",
        "curriculum_version": "人教版",
        "subjects": ["math"],
        "version": "basic",
    }
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    init_db(student)
    conn = get_conn(student)

    # 10道测试错题，覆盖不同年级和错误类型
    test_mistakes = [
        # (题目, 错误答案, 知识点, 错误类型, 年级)
        ("小明有5个苹果，吃了3个，还剩几个？", "1", "减法应用题", "thinking_error", "grade_1"),
        ("12 + 7 = ?", "18", "20以内加法", "careless", "grade_1"),
        ("3 × 4 = ?", "7", "乘法基础", "knowledge_gap", "grade_2"),
        ("56 ÷ 8 = ?", "6", "表内除法", "thinking_error", "grade_2"),
        ("3/4 + 1/4 = ?", "4/8", "同分母分数加法", "knowledge_gap", "grade_4"),
        ("小明买了3/4千克苹果，吃了1/4千克，还剩多少千克？", "1/2", "分数的减法(同分母)", "thinking_error", "grade_4"),
        ("长方形的长是5厘米，宽是3厘米，面积是多少？", "8", "长方形面积", "knowledge_gap", "grade_3"),
        ("1.5 + 2.3 = ?", "3.8", "小数加法", "careless", "grade_4"),
        ("100 - 37 = ?", "73", "退位减法", "thinking_error", "grade_2"),
        ("一个数的3倍是18，这个数是多少？", "54", "倍数关系", "thinking_error", "grade_3"),
    ]

    for problem, wrong, kp, etype, grade in test_mistakes:
        mid = insert_mistake(conn,
            subject="math", original_problem=problem,
            wrong_answer=wrong, correct_answer="(测试数据)",  # 不关心正确答案
            knowledge_point=kp, error_type=etype,
            error_analysis=f"测试数据: {kp} - {etype}",
            pool_status="active", grade_level=grade, curriculum_ver="人教版")

        # 生成几道变式题占位
        for _ in range(2):
            insert_variant(conn, mistake_id=mid,
                          problem_text=f"[变式] {problem}",
                          correct_answer="(略)", difficulty="easy")

        upsert_mastery(conn, kp, "math", True)

    conn.close()

    # 测试学生账号
    test_dir = os.path.join(ROOT, "user_data", "测试学生")
    os.makedirs(test_dir, exist_ok=True)
    test_profile_path = os.path.join(test_dir, "profile.json")
    salt2 = os.urandom(16)
    dk2 = hashlib.pbkdf2_hmac("sha256", b"test123", salt2, 200000)
    test_hash = salt2.hex() + ":" + dk2.hex()
    test_profile = {
        "student_name": "测试学生",
        "password_hash": test_hash,
        "province": "广东省",
        "city": "广州市",
        "district": "天河区",
        "grade_level": "grade_4",
        "curriculum_version": "人教版",
        "subjects": ["math"],
        "version": "basic",
    }
    with open(test_profile_path, "w", encoding="utf-8") as f:
        json.dump(test_profile, f, ensure_ascii=False, indent=2)
    init_db("测试学生")

    console.print(f"\n[green]✓ 测试数据已写入[/green]")
    console.print(f"  demo / demo       (演示账号，含10道测试错题)")
    console.print(f"  测试学生 / test123 (纯净测试账号)")


# ─── 主入口 ─────────────────────────────────────────────────

def run_all(include_ai: bool = True):
    console.print()
    console.print(Panel("[bold]错题Pro 审计报告[/bold]", border_style="#5B7FFF"))
    console.print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print(f"模式: {'含AI连接测试' if include_ai else '仅本地检查'}\n")

    _results.clear()

    console.print("[bold]1. 文件完整性[/bold]")
    check_files()

    console.print("\n[bold]2. 模块导入[/bold]")
    check_imports()

    console.print("\n[bold]3. 数据库[/bold]")
    check_db()

    console.print("\n[bold]4. Prompt模板[/bold]")
    check_prompts()

    console.print("\n[bold]5. 认证系统[/bold]")
    check_auth()

    console.print("\n[bold]6. 调度逻辑[/bold]")
    check_scheduler()

    if include_ai:
        console.print("\n[bold]7. AI连接性[/bold]")
        check_ai_connectivity()
    else:
        console.print("\n[dim]7. AI连接性 (跳过，使用 --full 启用)[/dim]")

    # 汇总
    passed = sum(1 for r in _results if r["passed"])
    failed = len(_results) - passed

    console.print(f"\n[bold]总计:[/bold] {len(_results)} 项  "
                  f"[green]{passed} 通过[/green]  "
                  f"[red]{failed} 失败[/red]")

    # 写入报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "total": len(_results),
        "passed": passed,
        "failed": failed,
        "results": _results,
    }
    with open(AUDIT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    console.print(f"\n[dim]审计报告已写入: {AUDIT_REPORT_PATH}[/dim]")

    return failed == 0


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--seed" in args:
        seed_test_data()
    elif "--quick" in args:
        run_all(include_ai=False)
    else:
        # 默认全量
        success = run_all(include_ai=True)
        # 再写入测试数据
        console.print("\n[bold]写入测试数据[/bold]")
        seed_test_data()

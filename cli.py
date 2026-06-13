"""
错题Pro - CLI 终端交互界面
使用 Rich 库，参考 DESIGN.md 设计规范
"""

import os
import sys
import json
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich.layout import Layout
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# 配色常量
C_BLUE     = "#5B7FFF"
C_RED      = "#FF5B6B"
C_AMBER    = "#FF9F43"
C_GREEN    = "#34C759"
C_BG       = "#F5F6FA"
C_TEXT     = "#1A1C24"
C_TEXT_SUB = "#5E6372"

ROOT = os.path.dirname(os.path.abspath(__file__))

# ─── 全局状态 ───────────────────────────────────────────────

_current_student: str = None
_user_data_dir: str = None


def get_ud() -> str:
    return _user_data_dir


def get_name() -> str:
    return _current_student


# ─── 认证 ───────────────────────────────────────────────────

def _ensure_auth_imports():
    global auth, main
    import auth as _auth
    import main as _main
    return _auth, _main


def _login_screen():
    """登录/注册界面"""
    auth, main = _ensure_auth_imports()

    console.clear()
    console.print()
    console.print(Panel.fit(
        "[bold]错题[/bold][bold bright_blue]Pro[/bold bright_blue]",
        subtitle="让每一道错题，变成知识版图上被征服的领地",
        border_style=C_BLUE,
    ))

    # 检查是否已有账号
    user_dirs = []
    ud_dir = os.path.join(ROOT, "user_data")
    if os.path.isdir(ud_dir):
        user_dirs = [d for d in os.listdir(ud_dir)
                     if os.path.isdir(os.path.join(ud_dir, d)) and not d.startswith(".")]

    if user_dirs:
        console.print("\n[bold]选择账号或创建新账号：[/bold]\n")
        for i, d in enumerate(user_dirs, 1):
            pf_path = os.path.join(ud_dir, d, "profile.json")
            grade = ""
            if os.path.exists(pf_path):
                with open(pf_path) as f:
                    pf = json.load(f)
                grade = pf.get("grade_level", "")
            console.print(f"  [{C_BLUE}]{i}[/{C_BLUE}] {d}  [dim]{grade}[/dim]")

        console.print(f"\n  [{C_BLUE}]n[/{C_BLUE}] 创建新账号")
        console.print(f"  [{C_BLUE}]q[/{C_BLUE}] 退出")

        choice = Prompt.ask("\n选择", default="1")
        if choice.lower() == "q":
            sys.exit(0)
        elif choice.lower() == "n":
            _register_flow()
        else:
            try:
                idx = int(choice) - 1
                selected = user_dirs[idx]
            except (ValueError, IndexError):
                console.print("[red]无效选择[/red]")
                return _login_screen()

            global _user_data_dir
            _user_data_dir = os.path.join(ROOT, "user_data", selected)
            auth.PROFILE_PATH = os.path.join(_user_data_dir, "profile.json")
            main.set_student(selected)
            _current_student_name = selected

            password = Prompt.ask("输入密码", password=True)
            if auth.login(password):
                console.print(f"\n[green]✓ 欢迎回来，{selected}！[/green]")
                import time; time.sleep(0.8)
                _main_menu()
            else:
                console.print("\n[red]密码错误[/red]")
                import time; time.sleep(1)
                _login_screen()
    else:
        console.print("\n[dim]首次使用，请创建账号[/dim]\n")
        _register_flow()


def _register_flow():
    """注册流程"""
    auth, main = _ensure_auth_imports()
    from auth import create_account

    console.clear()
    console.print("[bold]创建账号[/bold]\n")

    name = Prompt.ask("昵称")
    if not name.strip():
        console.print("[red]昵称不能为空[/red]")
        return _register_flow()

    pw1 = Prompt.ask("设置密码", password=True)
    if len(pw1) < 3:
        console.print("[red]密码至少3位[/red]")
        return _register_flow()
    pw2 = Prompt.ask("确认密码", password=True)
    if pw1 != pw2:
        console.print("[red]两次密码不一致[/red]")
        return _register_flow()

    # 创建用户目录
    global _user_data_dir
    _user_data_dir = os.path.join(ROOT, "user_data", name)
    auth.PROFILE_PATH = os.path.join(_user_data_dir, "profile.json")
    os.makedirs(_user_data_dir, exist_ok=True)

    # 默认 profile
    profile = {
        "student_name": name,
        "province": "",
        "city": "",
        "district": "",
        "grade_level": "grade_4",
        "curriculum_version": "人教版",
        "subjects": ["math"],
        "version": "basic",
    }

    # 初始设置
    console.print("\n[bold]完善信息[/bold]\n")
    _setup_form(profile)

    create_account(name, pw1, profile)
    main.set_student(name)
    from db import init_db
    init_db(name)

    console.print(f"\n[green]✓ 账号创建成功！[/green]")
    import time; time.sleep(1)
    _main_menu()


def _setup_form(profile: dict):
    """初始设置表单"""
    # 地区
    console.print("[dim]所在地区[/dim]")
    province = Prompt.ask("  省", default="广东")
    city = Prompt.ask("  市", default="广州")
    district = Prompt.ask("  区", default="天河")
    profile["province"] = province
    profile["city"] = city
    profile["district"] = district

    # 年级
    console.print("\n[dim]在读年级[/dim]")
    grades = ["小一","小二","小三","小四","小五","小六",
              "初一","初二","初三","高一","高二","高三"]
    grade_keys = ["grade_1","grade_2","grade_3","grade_4","grade_5","grade_6",
                  "grade_7","grade_8","grade_9","grade_10","grade_11","grade_12"]
    for i in range(0, len(grades), 6):
        row = "  ".join(f"[{C_BLUE}]{j+1}[/{C_BLUE}] {g}" for j, g in enumerate(grades[i:i+6], i))
        console.print(f"  {row}")
    g_idx = IntPrompt.ask("选择年级", default=4, choices=[str(i) for i in range(1, 13)])
    profile["grade_level"] = grade_keys[g_idx - 1]

    # 教材版本
    console.print("\n[dim]教材版本[/dim]")
    versions = ["人教版","北师大版","苏教版","沪教版","其他"]
    for i, v in enumerate(versions, 1):
        console.print(f"  [{C_BLUE}]{i}[/{C_BLUE}] {v}")
    v_idx = IntPrompt.ask("选择版本", default=1, choices=[str(i) for i in range(1, 6)])
    profile["curriculum_version"] = versions[v_idx - 1]

    # 科目
    console.print("\n[dim]科目（多选，逗号分隔）[/dim]")
    console.print(f"  [{C_BLUE}]1[/{C_BLUE}] 数学  [{C_BLUE}]2[/{C_BLUE}] 英语  [{C_BLUE}]3[/{C_BLUE}] 语文")
    subj_sel = Prompt.ask("选择", default="1")
    subj_map = {"1":"math","2":"english","3":"chinese"}
    profile["subjects"] = [subj_map[s.strip()] for s in subj_sel.split(",") if s.strip() in subj_map]
    if not profile["subjects"]:
        profile["subjects"] = ["math"]


# ─── 主菜单 ─────────────────────────────────────────────────

def _main_menu():
    console.clear()
    name = get_name()
    import main as _main

    console.print()
    title = Text(f"你好，{name} 👋", style=f"bold {C_TEXT}")
    console.print(Panel(title, border_style=C_BLUE))

    # 到期复习检查
    try:
        conn = _main_get_conn()
        from db import get_due_reviews
        dues = get_due_reviews(conn)
        conn.close()
        if dues:
            console.print(f"\n  📌 今日有 [{C_RED}]{len(dues)}[/{C_RED}] 个知识点等待复习")
        else:
            console.print(f"\n  ✅ 今日没有需要复习的知识点")
    except Exception:
        pass

    console.print(f"\n  [[{C_BLUE}]1[/{C_BLUE}]] 📝 录入错题")
    console.print(f"  [[{C_BLUE}]2[/{C_BLUE}]] 📌 每日复习")
    console.print(f"  [[{C_BLUE}]3[/{C_BLUE}]] 🗺️  知识版图")
    console.print(f"  [[{C_BLUE}]4[/{C_BLUE}]] 📊 学习报告")
    console.print(f"  [[{C_BLUE}]5[/{C_BLUE}]] ⚙️  设置")
    console.print(f"  [[{C_BLUE}]q[/{C_BLUE}]] 退出")

    choice = Prompt.ask("\n选择", default="1")

    if choice == "1":
        _enter_mistake_flow()
    elif choice == "2":
        _daily_review_flow()
    elif choice == "3":
        _knowledge_map()
    elif choice == "4":
        _progress_report()
    elif choice == "5":
        _settings()
    elif choice.lower() == "q":
        console.print("[dim]再见！[/dim]")
        sys.exit(0)
    else:
        _main_menu()


def _main_get_conn():
    """获取数据库连接"""
    from db import get_conn
    return get_conn(get_name())


# ─── 录入错题流程 ───────────────────────────────────────────

def _enter_mistake_flow():
    console.clear()
    console.print("[bold]📝 录入错题[/bold]\n")

    # 选择科目
    profile = _main_load_profile()
    subjects = profile.get("subjects", ["math"])
    subject_map = {"math":"数学","english":"英语","chinese":"语文"}

    if len(subjects) == 1:
        subject = subjects[0]
        console.print(f"学科：[bold]{subject_map.get(subject, subject)}[/bold]")
    else:
        for i, s in enumerate(subjects, 1):
            console.print(f"  [{C_BLUE}]{i}[/{C_BLUE}] {subject_map.get(s, s)}")
        idx = IntPrompt.ask("选择学科", default=1) - 1
        subject = subjects[idx]

    console.print("\n输入错题内容：\n")

    problem = Prompt.ask("题目内容")
    if not problem.strip():
        console.print("[red]题目不能为空，已取消[/red]")
        import time; time.sleep(1)
        return _main_menu()

    wrong = Prompt.ask("你的错误答案")

    # AI诊断
    console.print("\n[dim]正在AI诊断...[/dim]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("[dim]分析中...预计5-10秒[/dim]", total=None)
        try:
            main_module = __import__('main')
            result = main_module.workflow_new_mistake(problem, wrong, subject)
            progress.remove_task(task)
        except Exception as e:
            progress.remove_task(task)
            console.print(f"\n[red]诊断失败: {e}[/red]")
            Prompt.ask("\n按回车返回")
            return _main_menu()

    # 展示诊断结果
    diag = result["diagnosis"]
    console.clear()
    console.print("[bold]🔍 AI诊断结果[/bold]\n")

    diag_panel = Panel(
        f"[bold]{diag['knowledge_point']}[/bold]\n\n"
        f"[{C_RED}]▎错误类型：[/{C_RED}] {diag['error_type']}\n"
        f"[dim]▎分析：{diag['error_analysis']}[/dim]\n"
        f"[{C_GREEN}]▎正确答案：[/{C_GREEN}] {diag.get('correct_answer', '')}",
        border_style=C_BLUE,
        title="诊断",
    )
    console.print(diag_panel)

    # 原题回顾
    console.print(f"[dim]📋 原题：[/dim]{problem}")
    console.print(f"[dim]你的答案：[/dim][red]{wrong}[/red]")
    console.print()

    console.print(f"\n已生成 [{C_BLUE}]{len(result['variants'])}[/{C_BLUE}] 道变式题")
    do_now = Confirm.ask("\n是否现在练习？", default=True)
    if do_now:
        _practice_variants(result["variants"], subject)
    else:
        console.print("[dim]变式题已保存，稍后可在复习中练习[/dim]")
        import time; time.sleep(1)
        _main_menu()


def _practice_variants(variants: list, subject: str = "math"):
    """练习一组变式题"""
    correct_count = 0
    total = len(variants)

    for i, v in enumerate(variants):
        console.clear()
        console.print(f"[bold]📝 练习 第{i+1}/{total}题[/bold]")
        difficulty_tag = {"easy":"🟢 热身","same":"🟡 标准","slightly_harder":"🔴 挑战"}.get(v.get("difficulty","same"), "")
        console.print(f"[dim]{difficulty_tag}[/dim]\n")

        console.print(Panel(v["problem"], border_style=C_BLUE, title="题目"))

        answer = Prompt.ask("\n你的答案")

        console.print("\n[dim]正在批改...[/dim]")
        try:
            main_module = __import__('main')
            result = main_module.workflow_solve_variant(v["id"], answer)
        except Exception as e:
            console.print(f"[red]批改失败: {e}[/red]")
            Prompt.ask("\n按回车继续")
            continue

        fb = result["result"]
        if fb["is_correct"]:
            console.print(f"\n[{C_GREEN}]✅ 回答正确！[/{C_GREEN}]")
            correct_count += 1
        else:
            console.print(f"\n[{C_RED}]💪 还差一点点[/{C_RED}]")

        console.print(f"[bold]{fb['feedback']}[/bold]")
        if fb.get("hint"):
            console.print(f"\n[{C_BLUE}]💡 提示：[/{C_BLUE}] {fb['hint']}")

        console.print(f"\n[dim]池状态: {result.get('pool_transition', '')}[/dim]")

        if i < total - 1:
            Prompt.ask("\n按回车进入下一题")

    console.clear()
    console.print(f"[bold]🎉 练习完成！[/bold]\n")
    console.print(f"  正确：[{C_GREEN}]{correct_count}/{total}[/{C_GREEN}]")
    Prompt.ask("\n按回车返回主菜单")
    _main_menu()


# ─── 每日复习流程 ───────────────────────────────────────────

def _daily_review_flow():
    console.clear()
    console.print("[bold]📌 每日复习[/bold]\n")

    profile = _main_load_profile()
    subjects = profile.get("subjects", ["math"])

    # 暂时选第一个科目做复习
    subject = subjects[0]

    console.print("[dim]正在检查待复习知识点...[/dim]")
    try:
        main_module = __import__('main')
        review = main_module.workflow_daily_review(subject)
    except Exception as e:
        console.print(f"[red]获取复习计划失败: {e}[/red]")
        Prompt.ask("\n按回车返回")
        return _main_menu()

    if review["due_count"] == 0:
        console.print(f"\n[{C_GREEN}]✅ {review['message']}[/{C_GREEN}]")
        Prompt.ask("\n按回车返回")
        return _main_menu()

    console.print(f"\n今日复习 [{C_BLUE}]{review['due_count']}[/{C_BLUE}] 个知识点，共 [{C_BLUE}]{len(review['questions'])}[/{C_BLUE}] 题\n")

    for item in review["plan"]:
        console.print(f"  · {item['knowledge_point']} [{item['pool_status']}] × {item['count']}题")

    start = Confirm.ask("\n开始复习？", default=True)
    if start:
        _practice_variants(review["questions"], subject)
    else:
        _main_menu()


# ─── 知识版图 ───────────────────────────────────────────────

def _knowledge_map():
    console.clear()
    console.print("[bold]🗺️ 知识版图[/bold]\n")

    try:
        main_module = __import__('main')
        report = main_module.workflow_progress_report()
    except Exception as e:
        console.print(f"[red]获取数据失败: {e}[/red]")
        Prompt.ask("\n按回车返回")
        return _main_menu()

    if report["total_knowledge_points"] == 0:
        console.print("[dim]暂无数据，先录入一些错题吧[/dim]")
        Prompt.ask("\n按回车返回")
        return _main_menu()

    console.print(f"知识点总数: [{C_BLUE}]{report['total_knowledge_points']}[/{C_BLUE}]")
    console.print(f"整体掌握度: [{C_GREEN}]{report['overall_mastery']*100:.0f}%[/{C_GREEN}]")
    console.print(f"活跃:{report['pool_breakdown']['active']} | 观察:{report['pool_breakdown']['observing']} | 休眠:{report['pool_breakdown']['dormant']}\n")

    # 表格
    table = Table(box=box.SIMPLE, border_style="dim")
    table.add_column("知识点", style=C_TEXT)
    table.add_column("掌握度", justify="right")
    table.add_column("Streak", justify="center")
    table.add_column("状态")

    for m in report["masteries"]:
        pct = m["mastery_score"]
        if pct >= 0.9:
            color = C_GREEN; tag = "熟练"
        elif pct >= 0.7:
            color = C_GREEN; tag = "基本"
        elif pct >= 0.4:
            color = C_AMBER; tag = "加强"
        else:
            color = C_RED; tag = "攻克"

        bar_len = int(pct * 10)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        table.add_row(
            m["knowledge_point"],
            f"[{color}]{bar}[/{color}] {pct*100:.0f}%",
            str(m["streak"]),
            f"[{color}]{tag}[/{color}]",
        )

    console.print(table)
    Prompt.ask("\n按回车返回")
    _main_menu()


# ─── 学习报告 ───────────────────────────────────────────────

def _progress_report():
    console.clear()
    console.print("[bold]📊 学习报告[/bold]\n")

    try:
        main_module = __import__('main')
        report = main_module.workflow_progress_report()
    except Exception as e:
        console.print(f"[red]获取报告失败: {e}[/red]")
        Prompt.ask("\n按回车返回")
        return _main_menu()

    if report["total_knowledge_points"] == 0:
        console.print("[dim]暂无数据[/dim]")
        Prompt.ask("\n按回车返回")
        return _main_menu()

    overall = report["overall_mastery"]
    overall_color = C_GREEN if overall >= 0.7 else (C_AMBER if overall >= 0.4 else C_RED)

    console.print(Panel(
        f"[{overall_color}]掌握度 {overall*100:.0f}%[/{overall_color}]\n"
        f"[dim]已覆盖 {report['total_knowledge_points']} 个知识点[/dim]",
        border_style=C_BLUE,
        title="整体掌握度",
    ))

    console.print(f"\n活跃池: [{C_RED}]{report['pool_breakdown']['active']}[/{C_RED}]")
    console.print(f"观察池: [{C_AMBER}]{report['pool_breakdown']['observing']}[/{C_AMBER}]")
    console.print(f"休眠池: [{C_GREEN}]{report['pool_breakdown']['dormant']}[/{C_GREEN}]")

    console.print("\n[dim]📅 下次报告：明日[/dim]")
    Prompt.ask("\n按回车返回")
    _main_menu()


# ─── 设置 ───────────────────────────────────────────────────

def _settings():
    console.clear()
    console.print("[bold]⚙️ 设置[/bold]\n")
    console.print(f"  [[{C_BLUE}]1[/{C_BLUE}]] 修改年级/教材")
    console.print(f"  [[{C_BLUE}]2[/{C_BLUE}]] 修改密码")
    console.print(f"  [[{C_BLUE}]r[/{C_BLUE}]] 返回主菜单")

    choice = Prompt.ask("\n选择", default="r")
    if choice == "1":
        profile = _main_load_profile()
        _setup_form(profile)
        from auth import save_profile
        save_profile(profile)
        console.print("[green]✓ 已更新[/green]")
        import time; time.sleep(0.8)
        _settings()
    elif choice == "2":
        old = Prompt.ask("旧密码", password=True)
        new = Prompt.ask("新密码", password=True)
        from auth import change_password
        if change_password(old, new):
            console.print("[green]✓ 密码已修改[/green]")
        else:
            console.print("[red]旧密码错误[/red]")
        import time; time.sleep(1)
        _settings()
    else:
        _main_menu()


def _main_load_profile():
    from auth import load_profile
    return load_profile()


# ─── 入口 ───────────────────────────────────────────────────

def run():
    """CLI 入口"""
    from auth import has_account

    # 扫描现有用户
    ud_dir = os.path.join(ROOT, "user_data")
    user_dirs = []
    if os.path.isdir(ud_dir):
        user_dirs = [d for d in os.listdir(ud_dir)
                     if os.path.isdir(os.path.join(ud_dir, d)) and not d.startswith(".")]

    if user_dirs:
        _login_screen()
    else:
        _register_flow()


if __name__ == "__main__":
    run()

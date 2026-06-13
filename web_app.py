"""
错题Pro - H5 Web应用
FastAPI 后端 + Jinja2 服务端渲染
移动端优先，未来可迁移到微信小程序
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from functools import wraps
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from db import (
    init_db, get_conn, get_db_path,
    insert_mistake, get_mistake, list_mistakes, update_pool_status,
    insert_variant, get_variant,
    insert_attempt,
    upsert_mastery, get_mastery, get_all_masteries, get_due_reviews,
    update_mastery_review,
)
from ai import diagnose_mistake, generate_variants, check_answer
from scheduler import determine_pool_transition, plan_review_session
from prompts import SYSTEM_PROMPTS

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "user_data")

app = FastAPI(title="错题Pro", version="1.0.0")
from jinja2 import Environment, FileSystemLoader
from fastapi.responses import HTMLResponse

_env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")), cache_size=0)

def render(name: str, context: dict) -> HTMLResponse:
    """兼容 starlette 的模板渲染，兼容 Python 3.14"""
    template = _env.get_template(name)
    context["request"] = context.get("request")
    return HTMLResponse(template.render(**{k: v for k, v in context.items()}))

# ─── 辅助 ───────────────────────────────────────────────────

SESSION_FILE = os.path.join(ROOT, ".session")

def get_session() -> str | None:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            return f.read().strip()
    return None

def set_session(name: str):
    os.makedirs(ROOT, exist_ok=True)
    with open(SESSION_FILE, "w") as f:
        f.write(name)

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

def get_profile(name: str) -> dict:
    path = os.path.join(DATA_DIR, name, "profile.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)

def save_profile(name: str, data: dict):
    path = os.path.join(DATA_DIR, name, "profile.json")
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def require_auth(request: Request):
    name = get_session()
    if not name:
        return RedirectResponse("/login", status_code=302)
    request.state.student = name
    request.state.profile = get_profile(name)
    request.state.conn = get_conn(name)
    return None

def _hash_pw(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200000)
    return salt.hex() + ":" + dk.hex()

def _verify_pw(password: str, stored: str) -> bool:
    salt_hex, dk_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(dk_hex)
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200000) == expected

# ─── 页面路由 ───────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    name = get_session()
    if not name:
        return RedirectResponse("/login", status_code=302)
    return RedirectResponse("/home", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页"""
    # 列出已有账号
    users = []
    if os.path.isdir(DATA_DIR):
        for d in os.listdir(DATA_DIR):
            pp = os.path.join(DATA_DIR, d, "profile.json")
            if os.path.isfile(pp):
                with open(pp) as f:
                    pf = json.load(f)
                users.append({"name": d, "grade": pf.get("grade_level", "")})

    return render("login.html", {
        "request": request,
        "users": users,
        "error": request.query_params.get("error", ""),
    })


@app.post("/login")
async def login_action(request: Request):
    form = await request.form()
    name = form.get("name", "").strip()
    password = form.get("password", "")

    pf_path = os.path.join(DATA_DIR, name, "profile.json")
    if not os.path.exists(pf_path):
        return RedirectResponse("/login?error=账号不存在", status_code=302)

    with open(pf_path) as f:
        pf = json.load(f)

    if not _verify_pw(password, pf.get("password_hash", "")):
        return RedirectResponse("/login?error=密码错误", status_code=302)

    set_session(name)
    init_db(name)
    return RedirectResponse("/home", status_code=302)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return render("register.html", {
        "request": request,
        "error": request.query_params.get("error", ""),
    })


@app.post("/register")
async def register_action(request: Request):
    form = await request.form()
    name = form.get("name", "").strip()
    pw1 = form.get("password", "")
    pw2 = form.get("password2", "")
    province = form.get("province", "")
    city = form.get("city", "")
    district = form.get("district", "")
    grade = form.get("grade", "grade_4")
    curriculum = form.get("curriculum", "人教版")
    subjects = form.getlist("subjects")

    if not name or len(pw1) < 3:
        return RedirectResponse("/register?error=昵称必填，密码至少3位", status_code=302)
    if pw1 != pw2:
        return RedirectResponse("/register?error=两次密码不一致", status_code=302)
    if not subjects:
        subjects = ["math"]

    user_dir = os.path.join(DATA_DIR, name)
    os.makedirs(user_dir, exist_ok=True)

    profile = {
        "student_name": name,
        "password_hash": _hash_pw(pw1),
        "province": province, "city": city, "district": district,
        "grade_level": grade, "curriculum_version": curriculum,
        "subjects": subjects, "version": "basic",
    }
    save_profile(name, profile)
    init_db(name)
    set_session(name)
    return RedirectResponse("/home", status_code=302)


@app.get("/logout")
async def logout():
    clear_session()
    return RedirectResponse("/login", status_code=302)


@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    auth = require_auth(request)
    if auth: return auth

    conn = request.state.conn
    due = get_due_reviews(conn, "math")
    masteries = get_all_masteries(conn, "math")
    total_kp = len(masteries)
    conquered = sum(1 for m in masteries if m["pool_status"] == "dormant")

    return render("home.html", {
        "request": request,
        "student": request.state.student,
        "due_count": len(due),
        "due_list": due[:5],
        "total_kp": total_kp,
        "conquered": conquered,
        "grade": request.state.profile.get("grade_level", ""),
    })


@app.get("/mistake/new", response_class=HTMLResponse)
async def mistake_new_page(request: Request):
    auth = require_auth(request)
    if auth: return auth
    return render("mistake_input.html", {
        "request": request,
        "subjects": request.state.profile.get("subjects", ["math"]),
    })


@app.post("/mistake/new")
async def mistake_new_action(request: Request):
    auth = require_auth(request)
    if auth: return auth

    form = await request.form()
    problem = form.get("problem", "").strip()
    wrong = form.get("wrong_answer", "").strip()
    subject = form.get("subject", "math")
    photo = form.get("photo")

    if not problem:
        return JSONResponse({"error": "题目不能为空"}, status_code=400)

    profile = request.state.profile
    grade = profile.get("grade_level", "grade_4")
    curriculum = profile.get("curriculum_version", "人教版")

    # 如果传了图片URL，走OCR
    if photo:
        import base64, requests
        resp = requests.get(photo)
        img_data = base64.b64encode(resp.content).decode()
        from ai import _get_client
        client = _get_client()
        from prompts import ocr_diagnosis_prompt
        prompt = ocr_diagnosis_prompt(grade, curriculum)
        ai_resp = client.chat.completions.create(
            model="deepseek-chat", max_tokens=2048, temperature=0.3,
            messages=[{"role":"user","content":[
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{img_data}"}},
                {"type":"text","text":prompt}
            ]}]
        )
        import re
        raw = ai_resp.choices[0].message.content.strip()
        if raw.startswith("```"): raw = re.sub(r"^```(?:json)?\s*","",raw); raw = re.sub(r"\s*```$","",raw)
        ocr_result = json.loads(raw)
        problem = ocr_result.get("ocr_problem", problem)
        wrong = ocr_result.get("ocr_student_answer", wrong)

    # AI诊断
    try:
        diag = diagnose_mistake(problem, wrong, grade, curriculum)
    except Exception as e:
        return JSONResponse({"error": f"诊断失败: {e}"}, status_code=500)

    conn = request.state.conn
    mid = insert_mistake(conn,
        subject=subject, original_problem=problem, wrong_answer=wrong,
        correct_answer=diag.get("correct_answer",""),
        knowledge_point=diag["knowledge_point"],
        error_type=diag["error_type"],
        error_analysis=diag["error_analysis"],
        pool_status="active", grade_level=grade, curriculum_ver=curriculum,
    )

    # 生成变式题
    try:
        variants = generate_variants(
            diag["knowledge_point"], diag["error_type"],
            diag["error_analysis"], grade, curriculum, "easy", 3,
        )
    except Exception as e:
        return JSONResponse({"error": f"变式生成失败: {e}"}, status_code=500)

    diffs = ["easy", "easy", "same"]
    saved = []
    for i, v in enumerate(variants):
        vid = insert_variant(conn, mistake_id=mid,
            problem_text=v["problem"], correct_answer=v["correct_answer"],
            difficulty=diffs[i] if i < len(diffs) else "same")
        saved.append({"id": vid, "problem": v["problem"], "difficulty": diffs[i] if i < len(diffs) else "same"})

    return JSONResponse({
        "mistake_id": mid,
        "diagnosis": diag,
        "variants": saved,
    })


@app.post("/mistake/{mistake_id}/review")
async def mistake_review_action(request: Request, mistake_id: int):
    """获取某错题的复习变式题"""
    auth = require_auth(request)
    if auth: return auth

    conn = request.state.conn
    m = get_mistake(conn, mistake_id)
    if not m:
        raise HTTPException(404)

    profile = request.state.profile
    variants = generate_variants(
        m["knowledge_point"], m["error_type"], m["error_analysis"],
        profile.get("grade_level","grade_4"), profile.get("curriculum_version","人教版"),
        "same", 3,
    )
    saved = []
    for v in variants:
        vid = insert_variant(conn, mistake_id=mistake_id,
            problem_text=v["problem"], correct_answer=v["correct_answer"],
            difficulty=v.get("difficulty","same"))
        saved.append({"id": vid, "problem": v["problem"], "difficulty": v.get("difficulty","same")})

    mis_conn = conn
    return JSONResponse({"mistake": {"id": mistake_id, "knowledge_point": m["knowledge_point"]}, "variants": saved})


@app.post("/answer/{variant_id}")
async def answer_action(request: Request, variant_id: int):
    """提交答案"""
    auth = require_auth(request)
    if auth: return auth

    form = await request.form()
    student_answer = form.get("answer", "").strip()

    conn = request.state.conn
    variant = get_variant(conn, variant_id)
    if not variant:
        raise HTTPException(404)

    mistake = get_mistake(conn, variant["mistake_id"])
    if not mistake:
        raise HTTPException(404)

    result = check_answer(
        variant["problem_text"], variant["correct_answer"], student_answer,
        mistake["knowledge_point"], mistake["error_analysis"],
    )

    insert_attempt(conn,
        variant_id=variant_id, student_answer=student_answer,
        is_correct=1 if result["is_correct"] else 0,
        same_error=1 if result.get("same_error_pattern") else 0,
        feedback=result["feedback"], hint=result.get("hint"),
        action_type=result.get("action_type","correct"),
    )

    mastery = upsert_mastery(conn, mistake["knowledge_point"],
                             mistake.get("subject","math"), result["is_correct"])

    new_pool, next_review = determine_pool_transition(
        mistake["pool_status"], result["is_correct"],
        mastery["streak"], mastery["mastery_score"],
    )

    if new_pool != mistake["pool_status"]:
        update_pool_status(conn, mistake["id"], new_pool)
    if next_review:
        update_mastery_review(conn, mastery["knowledge_point"],
                             mistake.get("subject","math"), next_review, new_pool)

    return JSONResponse({
        "is_correct": result["is_correct"],
        "feedback": result["feedback"],
        "hint": result.get("hint"),
        "action_type": result.get("action_type", "correct"),
        "correct_answer": variant["correct_answer"],
        "pool_transition": f"{mistake['pool_status']} → {new_pool}",
        "mastery": {"score": mastery["mastery_score"], "streak": mastery["streak"]},
    })


@app.get("/map", response_class=HTMLResponse)
async def knowledge_map_page(request: Request):
    auth = require_auth(request)
    if auth: return auth

    conn = request.state.conn
    masteries = get_all_masteries(conn, "math")
    active = len(list_mistakes(conn, pool_status="active"))
    observing = len(list_mistakes(conn, pool_status="observing"))
    dormant = len(list_mistakes(conn, pool_status="dormant"))
    overall = sum(m["mastery_score"] for m in masteries) / len(masteries) if masteries else 0

    return render("knowledge_map.html", {
        "request": request,
        "masteries": masteries,
        "overall": round(overall, 2),
        "active": active, "observing": observing, "dormant": dormant,
    })


@app.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    auth = require_auth(request)
    if auth: return auth

    conn = request.state.conn
    masteries = get_all_masteries(conn, "math")
    overall = sum(m["mastery_score"] for m in masteries) / len(masteries) if masteries else 0
    weak = [m for m in masteries if m["mastery_score"] < 0.7]
    strong = [m for m in masteries if m["mastery_score"] >= 0.9]

    return render("report.html", {
        "request": request,
        "student": request.state.student,
        "overall": round(overall, 2),
        "masteries": masteries,
        "weak_points": weak,
        "strong_points": strong,
    })


@app.get("/mistakes", response_class=HTMLResponse)
async def mistakes_list_page(request: Request):
    auth = require_auth(request)
    if auth: return auth

    conn = request.state.conn
    mistakes = list_mistakes(conn, limit=100)

    return render("mistakes_list.html", {
        "request": request,
        "mistakes": mistakes,
    })


# ─── 启动 ───────────────────────────────────────────────────

if __name__ == "__main__":
    import webbrowser
    port = 8765
    print(f"\n  🚀 错题Pro 已启动")
    print(f"  📱 打开浏览器访问: http://localhost:{port}\n")
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

"""错题Pro - FastAPI Web应用"""
import os, sys, json, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
# Zeabur容器: /tmp 有写权限
_DATA_ROOT = "/tmp/mistake_pro_data" if os.path.exists("/tmp") and not os.access(ROOT, os.W_OK) else ROOT

from dotenv import load_dotenv; load_dotenv()
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

# 强制db.py用/tmp写数据
import db
db.DB_DIR = os.path.join(_DATA_ROOT, "user_data")

app = FastAPI(title="错题Pro")

# ─── 全局错误处理 ──────────────────────────────
import traceback as _tb
from starlette.requests import Request as _SR
from starlette.responses import PlainTextResponse
@app.exception_handler(Exception)
async def _global_handler(request: _SR, exc: Exception):
    return PlainTextResponse(_tb.format_exc(), status_code=500)

# ─── 内存存储（Zeabur 文件系统不可靠）─────────────────
_users = {}
_sessions = {}
_ready = False

def _ensure():
    global _ready
    if _ready: return
    for name, pw in [("demo","demo"), ("test","test123")]:
        s=os.urandom(16); h=hashlib.pbkdf2_hmac("sha256",pw.encode(),s,200000)
        _users[name]={"student_name":name,"password_hash":s.hex()+":"+h.hex(),
            "province":"广东省","city":"广州市","district":"天河区",
            "grade_level":"grade_4","curriculum_version":"人教版",
            "subjects":["math"],"version":"basic"}
    # 尝试写文件持久化（使用/tmp路径）
    try:
        d=os.path.join(_DATA_ROOT,"user_data"); os.makedirs(d,exist_ok=True)
        for name in ["demo","test"]:
            ud=os.path.join(d,name); os.makedirs(ud,exist_ok=True)
            pf=os.path.join(ud,"profile.json")
            if not os.path.exists(pf):
                json.dump(_users[name],open(pf,"w"),ensure_ascii=False,indent=2)
            from db import init_db; init_db(name)
    except: pass
    _ready=True
    print("✅ 账号就绪: demo/demo, test/test123", flush=True)

_ensure()  # 启动时初始化

import random, string as _string
def _sid(): return ''.join(random.choices(_string.ascii_letters+_string.digits, k=32))

@app.get("/health")
def health(): return {"ok":True,"users":len(_users)}

@app.get("/")
def root(request: Request):
    ua = request.headers.get("user-agent","")
    if "Mozilla" in ua:
        return RedirectResponse("/login", 302)
    return {"ok": True, "app": "错题Pro"}

# ─── 认证 ──────────────────────────────────────

def _login_html(err=""):
    u="".join(f'<div class="crd2"><form method="post" action="/login"><input type="hidden" name="name" value="{n}"><div style="display:flex;align-items:center;justify-content:space-between;"><div><div style="font-size:15px;font-weight:600;color:var(--t);">{n}</div></div><input class="inp" name="password" type="password" placeholder="密码" style="width:120px;margin:0;" required></div></form></div>' for n in sorted(_users.keys()))
    return _pg(f"""<div class="hd"><div style="font-size:28px;font-weight:700;color:var(--t);">错题<span style="color:var(--b);">Pro</span></div><div style="font-size:13px;color:var(--ts);">让每一道错题，变成知识版图上被征服的领地</div></div>
    <div class="pg">{f'<div class="err-msg">{err}</div>' if err else ''}{u or '<div style="text-align:center;padding:40px;">还没有账号</div>'}<div style="text-align:center;padding:20px;"><a href="/register" style="color:var(--b);font-size:14px;">＋ 创建新账号</a></div></div>""","登录")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return HTMLResponse(_login_html(request.query_params.get("error","")))

@app.post("/login")
async def login_post(request: Request):
    form=await request.form(); n=form.get("name","").strip(); p=form.get("password","")
    pf=_users.get(n)
    if not pf: return RedirectResponse("/login?error=账号不存在",302)
    sh,eh=pf["password_hash"].split(":")
    if hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(sh),200000).hex()!=eh:
        return RedirectResponse("/login?error=密码错误",302)
    try: from db import init_db; init_db(n)
    except: pass
    sid=_sid(); _sessions[sid]=n; resp=RedirectResponse("/home",302); resp.set_cookie("sid",sid); return resp

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return HTMLResponse(_pg("""<div class="pg"><div class="nb"><a href="/login">← 返回</a><span class="tt">创建账号</span></div><form method="post" action="/register"><div class="label">昵称</div><input class="inp" name="name" placeholder="输入昵称" required><div class="label">密码</div><input class="inp" name="password" type="password" placeholder="至少3位" required minlength="3"><input class="inp" name="password2" type="password" placeholder="确认密码" required><div class="label">所在地区</div><input class="inp" name="province" placeholder="省" value="广东"><input class="inp" name="city" placeholder="市" value="广州"><input class="inp" name="district" placeholder="区" value="天河"><div class="label">在读年级</div><select class="inp" name="grade" style="appearance:auto"><option value="grade_1">小一</option><option value="grade_2">小二</option><option value="grade_3">小三</option><option value="grade_4" selected>小四</option><option value="grade_5">小五</option><option value="grade_6">小六</option><option value="grade_7">初一</option><option value="grade_8">初二</option><option value="grade_9">初三</option><option value="grade_10">高一</option><option value="grade_11">高二</option><option value="grade_12">高三</option></select><div class="label">教材版本</div><select class="inp" name="curriculum" style="appearance:auto"><option>人教版</option><option>北师大版</option><option>苏教版</option><option>沪教版</option></select><div class="label">科目</div><div class="chip-row"><label class="chip sel"><input type="checkbox" name="subjects" value="math" checked> 数学</label><label class="chip"><input type="checkbox" name="subjects" value="english"> 英语</label><label class="chip"><input type="checkbox" name="subjects" value="chinese"> 语文</label></div><button class="btn btn-p">确认，开始使用</button></form></div>""","注册"))

@app.post("/register")
async def register_post(request: Request):
    form=await request.form(); n=form.get("name","").strip(); p1=form.get("password",""); p2=form.get("password2","")
    if not n or len(p1)<3: return RedirectResponse("/register?error=昵称必填，密码至少3位",302)
    if p1!=p2: return RedirectResponse("/register?error=两次密码不一致",302)
    s=os.urandom(16); h=hashlib.pbkdf2_hmac("sha256",p1.encode(),s,200000)
    _users[n]={"student_name":n,"password_hash":s.hex()+":"+h.hex(),"province":form.get("province",""),"city":form.get("city",""),"district":form.get("district",""),"grade_level":form.get("grade","grade_4"),"curriculum_version":form.get("curriculum","人教版"),"subjects":form.getlist("subjects") or ["math"],"version":"basic"}
    try:
        d=os.path.join(_DATA_ROOT,"user_data",n); os.makedirs(d,exist_ok=True)
        json.dump(_users[n],open(os.path.join(d,"profile.json"),"w"),ensure_ascii=False,indent=2)
        from db import init_db; init_db(n)
    except: pass
    sid=_sid(); _sessions[sid]=n; resp=RedirectResponse("/home",302); resp.set_cookie("sid",sid); return resp

@app.get("/logout")
async def logout(request:Request):
    sid=request.cookies.get("sid",""); _sessions.pop(sid,None)
    resp=RedirectResponse("/login",302); resp.delete_cookie("sid"); return resp

def _auth(request):
    sid=request.cookies.get("sid",""); n=_sessions.get(sid)
    if not n: return RedirectResponse("/login",302), None
    conn=None
    try: from db import get_conn; conn=get_conn(n)
    except: pass
    return None, {"student":n, "profile":_users.get(n,{}), "conn":conn}

# ─── 首页 ──────────────────────────────────────

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    n = ctx["student"]
    body = f"""<div class="pg"><div style="display:flex;justify-content:flex-end;padding:12px 0;"><a href="/logout" style="font-size:12px;color:var(--tw);">退出</a></div>
    <div style="font-size:26px;font-weight:700;color:var(--t);">你好，{n} 👋</div>
    <div style="font-size:13px;color:var(--ts);margin-bottom:20px;">开始学习吧</div>
    <div class="gr"><a href="/mistake/new" class="gi" style="background:rgba(91,127,255,.04);"><div class="ic">📝</div><div class="lb">录入错题</div></a><a href="/map" class="gi" style="background:rgba(255,91,107,.04);"><div class="ic">🗺️</div><div class="lb">知识版图</div></a><a href="/report" class="gi" style="background:rgba(91,127,255,.02);"><div class="ic">📊</div><div class="lb">学习报告</div></a><a href="/mistakes" class="gi" style="background:rgba(255,91,107,.02);"><div class="ic">📋</div><div class="lb">错题回顾</div></a></div></div>"""
    return HTMLResponse(_pg(body, "首页", ("1","","")))

# ─── 录入 ──────────────────────────────────────

_JS_OCR = r"""
var vs=[],idx=0,cc=0;
async function ocrUpload(){
  var f=document.getElementById('photo').files[0];
  if(!f) return alert('请先选择图片');
  document.getElementById('f').style.display='none';
  document.getElementById('ld').style.display='block';
  var d=new FormData();d.append('photo',f);d.append('subject','math');
  try{
    var r=await fetch('/mistake/ocr',{method:'POST',body:d}),j=await r.json();
    if(j.error){alert(j.error);location.reload();return}
    document.getElementById('ld').style.display='none';
    document.getElementById('ocrResult').style.display='block';
    document.getElementById('ocrProblem').value=j.ocr_problem||'';
    document.getElementById('ocrWrong').value=j.ocr_student_answer||'';
    document.getElementById('ocrDiag').innerHTML='<div class="crd" style="background:rgba(91,127,255,.03);border:1px solid rgba(91,127,255,.06);margin-top:12px;"><div style="font-size:12px;color:var(--ts);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">AI 诊断</div><div style="font-size:16px;font-weight:700;color:var(--t);">'+esc(j.knowledge_point)+'</div><div style="display:flex;align-items:flex-start;gap:8px;margin:8px 0;"><span class="tag tag-w">'+esc(j.error_type)+'</span><span style="font-size:13px;color:var(--ts);">'+esc(j.error_analysis)+'</span></div><div style="display:flex;align-items:flex-start;gap:8px;"><span class="tag" style="background:var(--bb);color:#3D5FD9;">正确答案</span><span style="font-size:13px;font-weight:600;">'+esc(j.correct_answer)+'</span></div></div>';
    vs=j.variants;idx=0;cc=0;
  }catch(e){alert(e);location.reload()}
}
function ocrConfirm(){
  var p=document.getElementById('ocrProblem').value.trim();
  var w=document.getElementById('ocrWrong').value.trim();
  if(!p) return alert('题目不能为空');
  var d=new FormData();d.append('problem',p);d.append('wrong_answer',w);d.append('subject','math');
  document.getElementById('ocrResult').style.display='none';
  document.getElementById('ld').style.display='block';
  fetch('/mistake/new',{method:'POST',body:d}).then(r=>r.json()).then(j=>{
    if(j.error){alert(j.error);location.reload();return}
    document.getElementById('ld').style.display='none';
    document.getElementById('r').innerHTML='<p style="font-size:13px;color:var(--ts);margin:12px 0;">已生成 <b>'+j.variants.length+'</b> 道变式题</p>';
    vs=j.variants;idx=0;cc=0;nq();
  }).catch(e=>{alert(e);location.reload()});
}
async function goM(){
  var a=document.getElementById('prob').value.trim();
  var b=document.getElementById('wans').value.trim();
  if(!a) return alert('请输入题目');
  document.getElementById('f').style.display='none';
  document.getElementById('ld').style.display='block';
  var d=new FormData();d.append('problem',a);d.append('wrong_answer',b);d.append('subject','math');
  try{
    var r=await fetch('/mistake/new',{method:'POST',body:d}),j=await r.json();
    if(j.error){alert(j.error);location.reload();return}
    document.getElementById('ld').style.display='none';
    document.getElementById('r').innerHTML='<div class="crd" style="background:rgba(91,127,255,.03);border:1px solid rgba(91,127,255,.06);"><div style="font-size:12px;color:var(--ts);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">AI 诊断</div><div style="font-size:16px;font-weight:700;color:var(--t);margin-bottom:12px;">'+esc(j.diagnosis.knowledge_point)+'</div><div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;"><span class="tag tag-w">'+esc(j.diagnosis.error_type)+'</span><span style="font-size:13px;color:var(--ts);line-height:1.6;">'+esc(j.diagnosis.error_analysis)+'</span></div><div style="display:flex;align-items:flex-start;gap:8px;"><span class="tag" style="background:var(--bb);color:#3D5FD9;">正确答案</span><span style="font-size:13px;color:var(--t);font-weight:600;">'+esc(j.diagnosis.correct_answer)+'</span></div></div><p style="font-size:13px;color:var(--ts);margin:12px 0;">已生成 <b>'+j.variants.length+'</b> 道变式题</p>';
    vs=j.variants;idx=0;cc=0;nq();
  }catch(e){alert(e);location.reload()}
}
function nq(){
  if(idx>=vs.length){fp();return}
  var v=vs[idx];
  var dl={easy:'🟢 热���',same:'🟡 标准',slightly_harder:'🔴 挑战'}[v.difficulty]||'';
  document.getElementById('p').innerHTML='<div class="crd" style="margin-top:12px;"><div style="font-size:11px;color:var(--ts);margin-bottom:8px;">'+dl+' · 第'+(idx+1)+'/'+vs.length+'题</div><div style="font-size:16px;color:var(--t);line-height:1.8;margin-bottom:16px;">'+esc(v.problem)+'</div><input class="inp" id="pa" placeholder="输入你的答案"><div id="fb"></div><button class="btn btn-p" onclick="goAns('+v.id+')" id="sb">提交答案</button></div>';
  document.getElementById('p').style.display='block';
  setTimeout(function(){var el=document.getElementById('pa');if(el)el.focus()},100);
}
async function goAns(vid){
  var a=document.getElementById('pa').value.trim();
  if(!a) return;
  document.getElementById('sb').disabled=true;
  var d=new FormData();d.append('answer',a);
  try{
    var r=await fetch('/answer/'+vid,{method:'POST',body:d}),j=await r.json();
    var fb=document.getElementById('fb');
    if(j.is_correct){
      cc++;
      fb.innerHTML='<div class="fb-c"><div style="font-size:32px;">✅</div><div style="font-weight:700;color:var(--g);">回答正确！</div><div style="font-size:13px;color:var(--ts);">'+esc(j.feedback)+'</div></div>';
    }else{
      fb.innerHTML='<div class="fb-w"><div style="font-size:32px;">💪</div><div style="font-weight:700;color:var(--r);">还差一点点</div><div style="font-size:13px;color:var(--ts);">'+esc(j.feedback)+'</div>'+(j.hint?'<div style="background:var(--bb);padding:10px;border-radius:10px;margin-top:8px;text-align:left;font-size:12px;"><b>💡 提示：</b>'+esc(j.hint)+'</div>':'')+'<div style="font-size:12px;color:var(--tw);margin-top:8px;">正确答案：'+esc(j.correct_answer)+'</div></div>';
    }
    document.getElementById('sb').textContent='继续下一题 →';
    document.getElementById('sb').onclick=function(){idx++;nq()};
    document.getElementById('sb').disabled=false;
  }catch(e){alert(e)}
}
function fp(){
  document.getElementById('p').innerHTML='<div class="crd" style="text-align:center;"><div style="font-size:40px;">🎉</div><div style="font-size:20px;font-weight:700;color:var(--t);">练习完成！</div><div style="font-size:14px;color:var(--ts);">正确 '+cc+'/'+vs.length+'</div><a href="/home" class="btn btn-p" style="margin-top:16px;">返回首页</a></div>';
}
function esc(s){var d=document.createElement('div');d.textContent=s||'';return d.innerHTML}
"""

@app.get("/mistake/new", response_class=HTMLResponse)
async def mistake_page(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    html = r"""<div class="pg"><div class="nb"><a href="/home">← 返回</a><span class="tt">录入错题</span></div>
    <div id="f">
    <div class="label">方式一：拍照识别（推荐）</div>
    <div class="crd" style="text-align:center;padding:24px;border:2px dashed var(--br);background:var(--card);">
      <input type="file" id="photo" accept="image/*" capture="environment" style="margin-bottom:12px;font-size:14px;width:100%;">
      <button class="btn btn-p" onclick="ocrUpload()">📷 拍照识别 + AI诊断</button>
    </div>
    <div class="label" style="margin-top:20px;">方式二：手动输入</div>
    <textarea class="txa" id="prob" placeholder="输入题目..."></textarea>
    <div class="label">你的错误答案</div><input class="inp" id="wans" placeholder="考试/作业中写的答案">
    <button class="btn btn-p" onclick="goM()">提交，开始AI诊断</button></div>
    <div id="ld" style="display:none;text-align:center;padding:40px;"><div class="spinner"></div><div style="color:var(--ts);">AI正在分析中...</div></div>
    <div id="ocrResult" style="display:none;margin-top:16px;">
      <div class="label">识别结果（可修改）</div><textarea class="txa" id="ocrProblem"></textarea>
      <div class="label">错误答案（可修改）</div><input class="inp" id="ocrWrong">
      <div id="ocrDiag"></div>
      <button class="btn btn-p" onclick="ocrConfirm()">确认提交，生成变式题</button>
    </div>
    <div id="r" style="display:none;"></div><div id="p" style="display:none;"></div></div>
    <script>""" + _JS_OCR + "</script>"
    return HTMLResponse(_pg(html, "录入错题"))

@app.post("/mistake/ocr")
async def mistake_ocr(request: Request):
    """拍照OCR + AI诊断 + 变式生成 一键完成"""
    redir, ctx = _auth(request)
    if redir: return redir
    form = await request.form()
    photo = form.get("photo")
    if not photo or not hasattr(photo, 'filename') or not photo.filename:
        return JSONResponse({"error":"请上传图片"}, 400)
    import base64
    img_bytes = await photo.read()
    img_b64 = base64.b64encode(img_bytes).decode()

    pf = ctx["profile"]
    grade = pf.get("grade_level", "grade_4")
    curriculum = pf.get("curriculum_version", "人教版")

    from ai import _get_client
    client = _get_client()
    from prompts import ocr_diagnosis_prompt
    prompt = ocr_diagnosis_prompt(grade, curriculum)

    response = client.chat.completions.create(
        model="deepseek-chat",
        max_tokens=2048, temperature=0.3,
        messages=[{"role":"user","content": [
            {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{img_b64}"}},
            {"type":"text","text":prompt},
        ]}]
    )
    raw = response.choices[0].message.content.strip()
    import re
    if raw.startswith("```"): raw = re.sub(r"^```(?:json)?\s*","",raw); raw = re.sub(r"\s*```$","",raw)
    ocr_data = json.loads(raw)

    problem = ocr_data.get("ocr_problem","")
    wrong = ocr_data.get("ocr_student_answer","")
    diag = {"knowledge_point": ocr_data["knowledge_point"],
            "error_type": ocr_data["error_type"],
            "error_analysis": ocr_data["error_analysis"],
            "correct_answer": ocr_data["correct_answer"]}

    from ai import generate_variants
    variants = generate_variants(diag["knowledge_point"], diag["error_type"],
        diag["error_analysis"], grade, curriculum, "easy", 3)
    diffs = ["easy","easy","same"]; saved = []
    for i, v in enumerate(variants):
        saved.append({"id": -1, "problem": v["problem"],
                      "difficulty": diffs[i] if i < len(diffs) else "same"})

    return JSONResponse({"ocr_problem": problem, "ocr_student_answer": wrong,
        "knowledge_point": diag["knowledge_point"], "error_type": diag["error_type"],
        "error_analysis": diag["error_analysis"], "correct_answer": diag["correct_answer"],
        "variants": saved})


@app.post("/mistake/new")
async def mistake_post(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    form=await request.form(); problem=form.get("problem","").strip(); wrong=form.get("wrong_answer","").strip()
    if not problem: return JSONResponse({"error":"题目不能为空"},400)
    pf=ctx["profile"]; grade=pf.get("grade_level","grade_4"); curriculum=pf.get("curriculum_version","人教版")
    from ai import diagnose_mistake, generate_variants
    diag=diagnose_mistake(problem,wrong,grade,curriculum)
    conn=ctx["conn"]
    from db import insert_mistake, insert_variant
    mid=insert_mistake(conn,subject="math",original_problem=problem,wrong_answer=wrong,correct_answer=diag.get("correct_answer",""),knowledge_point=diag["knowledge_point"],error_type=diag["error_type"],error_analysis=diag["error_analysis"],pool_status="active",grade_level=grade,curriculum_ver=curriculum)
    variants=generate_variants(diag["knowledge_point"],diag["error_type"],diag["error_analysis"],grade,curriculum,"easy",3)
    diffs=["easy","easy","same"]; saved=[]
    for i,v in enumerate(variants):
        vid=insert_variant(conn,mistake_id=mid,problem_text=v["problem"],correct_answer=v["correct_answer"],difficulty=diffs[i] if i<len(diffs) else"same")
        saved.append({"id":vid,"problem":v["problem"],"difficulty":diffs[i] if i<len(diffs) else"same"})
    return JSONResponse({"mistake_id":mid,"diagnosis":diag,"variants":saved})

@app.post("/answer/{variant_id}")
async def answer(request: Request, variant_id:int):
    redir, ctx = _auth(request)
    if redir: return redir
    form=await request.form(); ans=form.get("answer","").strip()
    conn=ctx["conn"]
    from db import get_variant, get_mistake, insert_attempt, upsert_mastery, update_pool_status, update_mastery_review
    v=get_variant(conn,variant_id)
    if not v: return JSONResponse({"error":"不存在"},404)
    m=get_mistake(conn,v["mistake_id"])
    from ai import check_answer
    r=check_answer(v["problem_text"],v["correct_answer"],ans,m["knowledge_point"],m["error_analysis"])
    insert_attempt(conn,variant_id=variant_id,student_answer=ans,is_correct=1 if r["is_correct"] else 0,same_error=1 if r.get("same_error_pattern") else 0,feedback=r["feedback"],hint=r.get("hint"),action_type=r.get("action_type","correct"))
    mast=upsert_mastery(conn,m["knowledge_point"],m.get("subject","math"),r["is_correct"])
    from scheduler import determine_pool_transition
    np,nr=determine_pool_transition(m["pool_status"],r["is_correct"],mast["streak"],mast["mastery_score"])
    if np!=m["pool_status"]: update_pool_status(conn,m["id"],np)
    if nr: update_mastery_review(conn,mast["knowledge_point"],m.get("subject","math"),nr,np)
    return JSONResponse({"is_correct":r["is_correct"],"feedback":r["feedback"],"hint":r.get("hint"),"correct_answer":v["correct_answer"]})

# ─── 版图/报告 ──────────────────────────────────

@app.get("/map", response_class=HTMLResponse)
async def map_page(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    conn=ctx.get("conn"); mh=""
    if conn:
        from db import get_all_masteries
        ms=get_all_masteries(conn,"math")
        for m in ms:
            sc=m["mastery_score"];c="#3D5FD9" if sc>=0.7 else("#D9821A" if sc>=0.4 else"#E04050");tc="tag-m" if m["pool_status"]=="dormant" else("tag-w" if m["pool_status"]=="active" else"tag-i");st="熟练" if m["pool_status"]=="dormant" else("攻克" if m["pool_status"]=="active" else"加强")
            mh+=f'<div class="crd2"><div class="kpr"><span class="nm">{m["knowledge_point"]}</span><span class="pct" style="color:{c};">{int(sc*100)}%</span><span class="tag {tc}">{st}</span></div><div class="prog"><div class="pf" style="width:{int(sc*100)}%;background:{c};"></div></div></div>'
    body=f'<div class="pg"><div class="nb"><a href="/home">← 返回</a><span class="tt">知识版图</span></div>{mh or "<div>暂无数据</div>"}</div>'
    return HTMLResponse(_pg(body,"版图",("","1","")))

@app.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    n=ctx["student"]; conn=ctx.get("conn"); mh=""; overall=0
    if conn:
        from db import get_all_masteries
        ms=get_all_masteries(conn,"math"); overall=sum(m["mastery_score"] for m in ms)/len(ms) if ms else 0
        for m in ms:
            sc=m["mastery_score"];c="var(--b)" if sc>=0.7 else("var(--a)" if sc>=0.4 else"var(--r)")
            tc="tag-w" if m["pool_status"]=="active" else("tag-i" if m["pool_status"]=="observing" else"tag-m");lb="熟练" if m["pool_status"]=="dormant" else("攻克" if m["pool_status"]=="active" else"加强")
            mh+=f'<div class="crd"><div style="display:flex;align-items:center;gap:8px;"><span style="font-size:14px;font-weight:600;">{m["knowledge_point"]}</span><span style="font-size:22px;font-weight:800;color:{c};">{int(sc*100)}%</span><span class="tag {tc}">{lb}</span></div></div>'
    body=f'<div class="pg"><div class="nb"><a href="/home">← 返回</a><span class="tt">学习报告</span></div><div class="hero"><div class="big">{int(overall*100)}%</div></div>{mh}</div>'
    return HTMLResponse(_pg(body,"报告",("","","1")))

@app.get("/mistakes", response_class=HTMLResponse)
async def mistakes_list(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    conn=ctx.get("conn"); mh=""
    if conn:
        from db import list_mistakes
        ms=list_mistakes(conn,limit=100); em={"knowledge_gap":"知识盲区","thinking_error":"思路错误","careless":"粗心"}
        for m in ms:
            ec="tag-kg" if m['error_type']=='knowledge_gap' else("tag-te" if m['error_type']=='thinking_error' else"tag-cl")
            mh+=f'<div class="crd2"><span class="tag {ec}">{em.get(m["error_type"],"")}</span><span style="font-size:13px;color:var(--t);"> {m["original_problem"][:60]}</span></div>'
    body=f'<div class="pg"><div class="nb"><a href="/home">← 返回</a><span class="tt">错题回顾</span></div>{mh or "<div>暂无数据</div>"}</div>'
    return HTMLResponse(_pg(body,"回顾"))

# ─── CSS ──────────────────────────────────────

CSS = """<style>
:root{--b:#5B7FFF;--bb:rgba(91,127,255,.06);--r:#FF5B6B;--rb:rgba(255,91,107,.07);--a:#FF9F43;--g:#34C759;--gb:rgba(52,199,89,.08);--t:#1A1C24;--ts:#5E6372;--tw:#949AAD;--bg:#F5F6FA;--w:#FFF;--c:#EEF0F5;--br:#E4E6EC}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;background:var(--bg);min-height:100vh}
.pg{max-width:420px;margin:0 auto;padding:20px}
.nb{display:flex;align-items:center;gap:12px;margin-bottom:20px}
.nb a{font-size:14px;color:var(--b);text-decoration:none}
.nb .tt{font-size:16px;font-weight:600;color:var(--t);flex:1;text-align:center;margin-right:20px}
.crd{background:var(--w);border-radius:18px;padding:18px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.03)}
.crd2{background:var(--w);border-radius:16px;padding:14px 16px;margin-bottom:8px;box-shadow:0 1px 2px rgba(0,0,0,.02)}
.btn{display:block;width:100%;height:50px;border:none;border-radius:13px;font-size:15px;font-weight:600;cursor:pointer;text-align:center;text-decoration:none;font-family:inherit}
.btn-p{background:var(--b);color:#FFF;line-height:50px}
.inp{width:100%;height:46px;background:var(--c);border:none;border-radius:11px;padding:0 14px;font-size:14px;color:var(--t);outline:none;margin-bottom:8px;font-family:inherit}
.inp:focus{background:var(--w);box-shadow:0 0 0 3px rgba(91,127,255,.12)}
.txa{width:100%;min-height:90px;background:var(--w);border:1px solid var(--br);border-radius:12px;padding:12px 14px;font-size:14px;color:var(--t);outline:none;font-family:inherit;resize:vertical;margin-bottom:8px}
.txa:focus{border-color:var(--b);box-shadow:0 0 0 3px rgba(91,127,255,.08)}
.prog{height:5px;background:var(--br);border-radius:99px;overflow:hidden}
.pf{height:100%;border-radius:99px}
.tag{display:inline-block;padding:2px 8px;border-radius:5px;font-size:10px;font-weight:600}
.tag-m{background:var(--gb);color:#28A745}.tag-i{background:rgba(255,159,67,.08);color:#D9821A}.tag-w{background:var(--rb);color:#E04050}
.tag-kg{background:rgba(255,91,107,.08);color:#E04050}.tag-te{background:rgba(91,127,255,.08);color:#3D5FD9}.tag-cl{background:rgba(255,159,67,.08);color:#D9821A}
.bn{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:420px;display:flex;justify-content:space-around;background:var(--w);border-top:1px solid var(--br);height:64px;align-items:center;z-index:100}
.bn a{display:flex;flex-direction:column;align-items:center;font-size:10px;color:var(--tw);text-decoration:none;gap:2px}.bn a .ic{font-size:20px}.bn a.on{color:var(--b)}
.hd{text-align:center;padding:48px 24px 32px}
.gr{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}
.gi{background:var(--w);border-radius:16px;padding:20px 16px;text-align:center;text-decoration:none;display:block;box-shadow:0 1px 2px rgba(0,0,0,.03)}.gi .ic{font-size:28px;margin-bottom:6px}.gi .lb{font-size:13px;font-weight:600;color:var(--t)}
.kpr{display:flex;align-items:center;gap:8px;padding:5px 0}.kpr .nm{flex:2;font-size:13px;color:var(--t)}.kpr .pct{font-size:13px;font-weight:600}
.hero{background:linear-gradient(180deg,var(--bb),rgba(255,91,107,.02));border-radius:20px;padding:28px 20px;text-align:center;margin-bottom:16px}.hero .big{font-size:52px;font-weight:800;color:var(--b)}
.err-msg{background:var(--rb);color:var(--r);padding:12px 16px;border-radius:12px;font-size:13px;margin-bottom:12px}
.fb-c{background:var(--gb);padding:16px;border-radius:12px;text-align:center}.fb-w{background:var(--rb);padding:16px;border-radius:12px;text-align:center}
.label{font-size:11px;font-weight:700;color:var(--ts);text-transform:uppercase;letter-spacing:1.5px;margin:16px 0 6px}
.spinner{width:40px;height:40px;border:3px solid var(--br);border-top-color:var(--b);border-radius:50%;animation:s .8s linear infinite;margin:0 auto 12px}@keyframes s{to{transform:rotate(360deg)}}
.chip-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}
.chip{padding:8px 14px;background:var(--c);border-radius:8px;font-size:13px;color:var(--t);cursor:pointer;border:2px solid transparent}.chip.sel{background:var(--bb);border-color:var(--b);color:var(--b);font-weight:600}</style>"""

def _pg(body, title="错题Pro", nav=None):
    n=nav if nav else("","","")
    nh=f'<nav class="bn"><a href="/home" class="{"on" if n[0]=="1" else ""}"><span class="ic">🏠</span>首页</a><a href="/mistake/new"><span class="ic">📝</span>录入</a><a href="/map" class="{"on" if n[1]=="1" else ""}"><span class="ic">🗺️</span>版图</a><a href="/report" class="{"on" if n[2]=="1" else ""}"><span class="ic">📊</span>报告</a></nav>'
    return f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no"><title>{title} - 错题Pro</title>{CSS}</head><body>{body}{nh}</body></html>'

# ─── 启动 ──────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 错题Pro port={port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

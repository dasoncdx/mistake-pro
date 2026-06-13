"""
错题Pro - Zeabur 入口
"""

import os, sys, json, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# ─── 初始化测试账号 ────────────────────────────────

DATA_DIR = os.path.join(ROOT, "user_data")
os.makedirs(DATA_DIR, exist_ok=True)

def init_account(name, password):
    d = os.path.join(DATA_DIR, name)
    os.makedirs(d, exist_ok=True)
    pf_path = os.path.join(d, "profile.json")
    if not os.path.exists(pf_path):
        s = os.urandom(16)
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), s, 200000)
        pf = {"student_name":name, "password_hash": s.hex()+":"+h.hex(),
              "province":"广东省","city":"广州市","district":"天河区",
              "grade_level":"grade_4","curriculum_version":"人教版",
              "subjects":["math"],"version":"basic"}
        json.dump(pf, open(pf_path,"w"), ensure_ascii=False, indent=2)
        try:
            from db import init_db
            init_db(name)
        except: pass

# ─── FastAPI App ──────────────────────────────────

from dotenv import load_dotenv; load_dotenv()

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

app = FastAPI(title="错题Pro")

@app.on_event("startup")
def startup():
    try:
        init_account("demo", "demo")
        init_account("test", "test123")
        print("✅ 测试账号就绪")
    except Exception as e:
        print(f"⚠️ 初始化跳过: {e}")

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/")
def root():
    return RedirectResponse("/login")

# ─── Session ───────────────────────────────────────

SF = os.path.join(ROOT, ".session")
def gs():
    return open(SF).read().strip() if os.path.exists(SF) else None
def ss(n):
    open(SF,"w").write(n)
def cs():
    os.path.exists(SF) and os.remove(SF)

def gp(n):
    p=os.path.join(DATA_DIR,n,"profile.json")
    return json.load(open(p)) if os.path.exists(p) else {}

def hpw(pw):
    s=os.urandom(16)
    return s.hex()+":"+hashlib.pbkdf2_hmac("sha256",pw.encode(),s,200000).hex()
def vpw(pw,st):
    sh,eh=st.split(":")
    return hashlib.pbkdf2_hmac("sha256",pw.encode(),bytes.fromhex(sh),200000).hex()==eh

def require_auth(request):
    n=gs()
    if not n: return RedirectResponse("/login",302)
    request.state.student=n
    request.state.profile=gp(n)
    from db import get_conn
    request.state.conn=get_conn(n)
    return None

# ─── CSS ───────────────────────────────────────────

CSS = """<style>
:root{--b:#5B7FFF;--bb:rgba(91,127,255,.06);--r:#FF5B6B;--rb:rgba(255,91,107,.07);--a:#FF9F43;--g:#34C759;--gb:rgba(52,199,89,.08);--t:#1A1C24;--ts:#5E6372;--tw:#949AAD;--bg:#F5F6FA;--w:#FFF;--c:#EEF0F5;--br:#E4E6EC}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;background:var(--bg);min-height:100vh}
.pg{max-width:420px;margin:0 auto;padding:20px 20px 100px}
.nb{display:flex;align-items:center;gap:12px;margin-bottom:20px}
.nb a{font-size:14px;color:var(--b);text-decoration:none}
.nb .tt{font-size:16px;font-weight:600;color:var(--t);flex:1;text-align:center;margin-right:20px}
.crd{background:var(--w);border-radius:18px;padding:18px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.03)}
.crd2{background:var(--w);border-radius:16px;padding:14px 16px;margin-bottom:8px;box-shadow:0 1px 2px rgba(0,0,0,.02)}
.btn{display:block;width:100%;height:50px;border:none;border-radius:13px;font-size:15px;font-weight:600;cursor:pointer;text-align:center;text-decoration:none;font-family:inherit}
.btn-p{background:var(--b);color:#FFF;line-height:50px}
.btn-s{background:var(--c);color:var(--t);margin-top:8px;line-height:50px}
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
.hd{text-align:center;padding:48px 24px 32px}.hd span{color:var(--b)}
.gr{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}
.gi{background:var(--w);border-radius:16px;padding:20px 16px;text-align:center;text-decoration:none;display:block;box-shadow:0 1px 2px rgba(0,0,0,.03)}.gi .ic{font-size:28px;margin-bottom:6px}.gi .lb{font-size:13px;font-weight:600;color:var(--t)}.gi .hi{font-size:11px;color:var(--tw);margin-top:2px}
.kpr{display:flex;align-items:center;gap:8px;padding:5px 0}.kpr .nm{flex:2;font-size:13px;color:var(--t)}.kpr .pct{font-size:13px;font-weight:600}
.hero{background:linear-gradient(180deg,var(--bb),rgba(255,91,107,.02));border-radius:20px;padding:28px 20px;text-align:center;margin-bottom:16px}
.hero .big{font-size:52px;font-weight:800;color:var(--b)}.hero .sub{font-size:12px;color:var(--ts)}
.err-msg{background:var(--rb);color:var(--r);padding:12px 16px;border-radius:12px;font-size:13px;margin-bottom:12px}
.fb-c{background:var(--gb);padding:16px;border-radius:12px;text-align:center}.fb-w{background:var(--rb);padding:16px;border-radius:12px;text-align:center}
.label{font-size:11px;font-weight:700;color:var(--ts);text-transform:uppercase;letter-spacing:1.5px;margin:16px 0 6px}
.card-w{border-left:3px solid rgba(255,91,107,.4)}.card-i{border-left:3px solid rgba(255,159,67,.4)}
.spinner{width:40px;height:40px;border:3px solid var(--br);border-top-color:var(--b);border-radius:50%;animation:s .8s linear infinite;margin:0 auto 12px}@keyframes s{to{transform:rotate(360deg)}}
.chip-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}
.chip{padding:8px 14px;background:var(--c);border-radius:8px;font-size:13px;color:var(--t);cursor:pointer;border:2px solid transparent}
.chip.sel{background:var(--bb);border-color:var(--b);color:var(--b);font-weight:600}
.chip input{display:none}
</style>"""

def _esc(s):
    if not s: return ""
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def _page(title,body,nav=None):
    n=nav if nav else ("","","")
    nav_html=f"""<nav class="bn"><a href="/home" class="{'on' if n[0]=='1' else ''}"><span class="ic">🏠</span>首页</a><a href="/mistake/new"><span class="ic">📝</span>录入</a><a href="/map" class="{'on' if n[1]=='1' else ''}"><span class="ic">🗺️</span>版图</a><a href="/report" class="{'on' if n[2]=='1' else ''}"><span class="ic">📊</span>报告</a></nav>"""
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no"><title>{title} - 错题Pro</title>{CSS}</head><body>{body}{nav_html}</body></html>"""

# ─── 登录页 ─────────────────────────────────────────

@app.get("/login",response_class=HTMLResponse)
async def login(request:Request):
    users=[]
    if os.path.isdir(DATA_DIR):
        for d in sorted(os.listdir(DATA_DIR)):
            pp=os.path.join(DATA_DIR,d,"profile.json")
            if os.path.isfile(pp):
                pf=json.load(open(pp))
                users.append({"n":d,"g":pf.get("grade_level","")})
    err=request.query_params.get("error","")
    uhtml=""
    for u in users:
        uhtml+=f"""<div class="crd2" style="position:relative;">
        <form method="post" action="/login"><input type="hidden" name="name" value="{_esc(u['n'])}">
        <div style="display:flex;align-items:center;justify-content:space-between;">
        <div><div style="font-size:15px;font-weight:600;color:var(--t);">{_esc(u['n'])}</div><div style="font-size:12px;color:var(--ts);">{_esc(u['g'])}</div></div>
        <input class="inp" name="password" type="password" placeholder="密码" style="width:120px;margin:0;" required>
        </div></form></div>"""
    if not users:
        uhtml='<div style="text-align:center;color:var(--ts);font-size:14px;padding:40px 0;">还没有账号</div>'
    body=f"""<div class="hd"><div style="font-size:28px;font-weight:700;color:var(--t);">错题<span style="color:var(--b);">Pro</span></div><div style="font-size:13px;color:var(--ts);">让每一道错题，变成知识版图上被征服的领地</div></div>
    <div class="pg" style="padding:0 24px;">
    {f'<div class="err-msg">{_esc(err)}</div>' if err else ''}
    {uhtml}
    <div style="text-align:center;padding:20px;"><a href="/register" style="color:var(--b);font-size:14px;text-decoration:none;">＋ 创建新账号</a></div></div>"""
    return HTMLResponse(_page("登录",body))

@app.post("/login")
async def login_post(request:Request):
    form=await request.form()
    n=form.get("name","").strip(); p=form.get("password","")
    pf=os.path.join(DATA_DIR,n,"profile.json")
    if not os.path.exists(pf): return RedirectResponse("/login?error=账号不存在",302)
    pf_data=json.load(open(pf))
    if not vpw(p, pf_data.get("password_hash","")): return RedirectResponse("/login?error=密码错误",302)
    ss(n)
    from db import init_db; init_db(n)
    return RedirectResponse("/home",302)

# ─── 注册页 ─────────────────────────────────────────

@app.get("/register",response_class=HTMLResponse)
async def register_page(request:Request):
    err=request.query_params.get("error","")
    body=f"""<div class="pg">
    <div class="nb"><a href="/login">← 返回</a><span class="tt">创建账号</span></div>
    {f'<div class="err-msg">{_esc(err)}</div>' if err else ''}
    <form method="post" action="/register">
    <div class="label">昵称</div><input class="inp" name="name" placeholder="输入昵称" required>
    <div class="label">密码</div><input class="inp" name="password" type="password" placeholder="至少3位" required minlength="3">
    <input class="inp" name="password2" type="password" placeholder="确认密码" required>
    <div class="label">所在地区</div>
    <input class="inp" name="province" placeholder="省" value="广东">
    <input class="inp" name="city" placeholder="市" value="广州">
    <input class="inp" name="district" placeholder="区" value="天河">
    <div class="label">在读年级</div>
    <select class="inp" name="grade" style="appearance:auto"><option value="grade_1">小一</option><option value="grade_2">小二</option><option value="grade_3">小三</option><option value="grade_4" selected>小四</option><option value="grade_5">小五</option><option value="grade_6">小六</option><option value="grade_7">初一</option><option value="grade_8">初二</option><option value="grade_9">初三</option><option value="grade_10">高一</option><option value="grade_11">高二</option><option value="grade_12">高三</option></select>
    <div class="label">教材版本</div>
    <select class="inp" name="curriculum" style="appearance:auto"><option>人教版</option><option>北师大版</option><option>苏教版</option><option>沪教版</option></select>
    <div class="label">科目</div>
    <div class="chip-row">
    <label class="chip sel"><input type="checkbox" name="subjects" value="math" checked> 数学</label>
    <label class="chip"><input type="checkbox" name="subjects" value="english"> 英语</label>
    <label class="chip"><input type="checkbox" name="subjects" value="chinese"> 语文</label></div>
    <button class="btn btn-p">确认，开始使用</button></form></div>"""
    return HTMLResponse(_page("注册",body))

@app.post("/register")
async def register_post(request:Request):
    form=await request.form(); n=form.get("name","").strip(); p1=form.get("password",""); p2=form.get("password2","")
    if not n or len(p1)<3: return RedirectResponse("/register?error=昵称必填，密码至少3位",302)
    if p1!=p2: return RedirectResponse("/register?error=两次密码不一致",302)
    d=os.path.join(DATA_DIR,n)
    if os.path.exists(os.path.join(d,"profile.json")): return RedirectResponse("/register?error=昵称已存在",302)
    subjects=form.getlist("subjects") or ["math"]
    pf={"student_name":n,"password_hash":hpw(p1),"province":form.get("province",""),"city":form.get("city",""),"district":form.get("district",""),"grade_level":form.get("grade","grade_4"),"curriculum_version":form.get("curriculum","人教版"),"subjects":subjects,"version":"basic"}
    os.makedirs(d,exist_ok=True); json.dump(pf,open(os.path.join(d,"profile.json"),"w"),ensure_ascii=False,indent=2)
    from db import init_db; init_db(n); ss(n)
    return RedirectResponse("/home",302)

@app.get("/logout")
async def logout(): cs(); return RedirectResponse("/login",302)

# ─── 首页 ──────────────────────────────────────────

@app.get("/home",response_class=HTMLResponse)
async def home(request:Request):
    a=require_auth(request)
    if a: return a
    conn=request.state.conn; n=request.state.student
    from db import get_due_reviews,get_all_masteries
    due=get_due_reviews(conn,"math"); ms=get_all_masteries(conn,"math")
    due_html=""
    if due:
        for k in due[:5]:
            sc=k["mastery_score"]; color="#FF5B6B" if sc<0.4 else ("#FF9F43" if sc<0.7 else "#34C759")
            due_html+=f"""<div style="margin-bottom:10px;"><div class="kpr"><span class="nm">{_esc(k['knowledge_point'])}</span><span class="pct" style="color:{color};">{int(sc*100)}%</span></div><div class="prog"><div class="pf" style="width:{int(sc*100)}%;background:{color};"></div></div></div>"""
        due_html=f"""<div class="crd" style="border:1px solid rgba(91,127,255,.08);"><div style="font-size:15px;font-weight:600;color:var(--t);margin-bottom:12px;">📌 今日待复习</div>{due_html}<a href="/mistake/new" class="btn btn-p">开始复习</a></div>"""
    conquered=sum(1 for m in ms if m["pool_status"]=="dormant")
    body=f"""<div class="pg">
    <div style="display:flex;justify-content:flex-end;padding:12px 0;"><a href="/logout" style="font-size:12px;color:var(--tw);text-decoration:none;">退出</a></div>
    <div style="font-size:26px;font-weight:700;color:var(--t);">你好，{_esc(n)} 👋</div>
    <div style="font-size:13px;color:var(--ts);margin-bottom:20px;">{"今日有 <b>"+str(len(due))+"</b> 个知识点等待复习" if due else "今日无需复习 ✅"}</div>
    {due_html}
    <div class="gr">
    <a href="/mistake/new" class="gi" style="background:rgba(91,127,255,.04);"><div class="ic">📝</div><div class="lb">录入错题</div><div class="hi">拍照/文字输入</div></a>
    <a href="/map" class="gi" style="background:rgba(255,91,107,.04);"><div class="ic">🗺️</div><div class="lb">知识版图</div><div class="hi">已征服 {conquered}/{len(ms)}</div></a>
    <a href="/report" class="gi" style="background:rgba(91,127,255,.02);"><div class="ic">📊</div><div class="lb">学习报告</div><div class="hi">掌握度分析</div></a>
    <a href="/mistakes" class="gi" style="background:rgba(255,91,107,.02);"><div class="ic">📋</div><div class="lb">错题回顾</div><div class="hi">全部记录</div></a></div></div>"""
    return HTMLResponse(_page("首页",body,("1","","")))

# ─── 录入错题 ──────────────────────────────────────

@app.get("/mistake/new",response_class=HTMLResponse)
async def mistake_page(request:Request):
    a=require_auth(request)
    if a: return a
    body="""<div class="pg">
    <div class="nb"><a href="/home">← 返回</a><span class="tt">录入错题</span></div>
    <div id="f"><div class="label">题目内容</div><textarea class="txa" id="prob" placeholder="输入题目..."></textarea>
    <div class="label">你的错误答案</div><input class="inp" id="wans" placeholder="考试/作业中写的答案">
    <button class="btn btn-p" onclick="go()">提交，开始AI诊断</button></div>
    <div id="ld" style="display:none;text-align:center;padding:40px;"><div class="spinner"></div><div style="color:var(--ts);">AI正在分析中...</div></div>
    <div id="r" style="display:none;"></div><div id="p" style="display:none;"></div></div>
<script>let vs=[],idx=0,cc=0;
async function go(){let a=document.getElementById('prob').value.trim(),b=document.getElementById('wans').value.trim();if(!a)return alert('请输入题目');document.getElementById('f').style.display='none';document.getElementById('ld').style.display='block';let d=new FormData();d.append('problem',a);d.append('wrong_answer',b);d.append('subject','math');try{let r=await fetch('/mistake/new',{method:'POST',body:d}),j=await r.json();if(j.error){alert(j.error);location.reload()}sr(j)}catch(e){alert(e);location.reload()}}
function sr(d){document.getElementById('ld').style.display='none';let di=d.diagnosis;document.getElementById('r').innerHTML='<div class="crd" style="background:rgba(91,127,255,.03);border:1px solid rgba(91,127,255,.06);"><div style="font-size:12px;color:var(--ts);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">AI 诊断</div><div style="font-size:16px;font-weight:700;color:var(--t);margin-bottom:12px;">'+e(di.knowledge_point)+'</div><div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;"><span class="tag tag-w">'+e(di.error_type)+'</span><span style="font-size:13px;color:var(--ts);line-height:1.6;">'+e(di.error_analysis)+'</span></div><div style="display:flex;align-items:flex-start;gap:8px;"><span class="tag" style="background:var(--bb);color:#3D5FD9;">正确答案</span><span style="font-size:13px;color:var(--t);font-weight:600;">'+e(di.correct_answer)+'</span></div></div><p style="font-size:13px;color:var(--ts);margin:12px 0;">已生成 <b>'+d.variants.length+'</b> 道变式题</p>';document.getElementById('r').style.display='block';vs=d.variants;idx=0;cc=0;nq()}
function nq(){if(idx>=vs.length){fp();return}let v=vs[idx],dl={easy:'🟢 热身',same:'🟡 标准',slightly_harder:'🔴 挑战'}[v.difficulty]||'';document.getElementById('p').innerHTML='<div class="crd" style="margin-top:12px;"><div style="font-size:11px;color:var(--ts);margin-bottom:8px;">'+dl+' · 第'+(idx+1)+'/'+vs.length+'题</div><div style="font-size:16px;color:var(--t);line-height:1.8;margin-bottom:16px;">'+e(v.problem)+'</div><input class="inp" id="pa" placeholder="输入你的答案"><div id="fb"></div><button class="btn btn-p" onclick="sa('+v.id+')" id="sb">提交答案</button></div>';document.getElementById('p').style.display='block';setTimeout(()=>{let el=document.getElementById('pa');if(el)el.focus()},100)}
async function sa(vid){let a=document.getElementById('pa').value.trim();if(!a)return;document.getElementById('sb').disabled=true;document.getElementById('sb').textContent='批改中...';let d=new FormData();d.append('answer',a);try{let r=await fetch('/answer/'+vid,{method:'POST',body:d}),j=await r.json();let fb=document.getElementById('fb');if(j.is_correct){cc++;fb.innerHTML='<div class="fb-c"><div style="font-size:32px;">✅</div><div style="font-weight:700;color:var(--g);">回答正确！</div><div style="font-size:13px;color:var(--ts);">'+e(j.feedback)+'</div></div>'}else{fb.innerHTML='<div class="fb-w"><div style="font-size:32px;">💪</div><div style="font-weight:700;color:var(--r);">还差一点点</div><div style="font-size:13px;color:var(--ts);">'+e(j.feedback)+'</div>'+(j.hint?'<div style="background:var(--bb);padding:10px;border-radius:10px;margin-top:8px;text-align:left;font-size:12px;"><b>💡 提示：</b>'+e(j.hint)+'</div>':'')+'<div style="font-size:12px;color:var(--tw);margin-top:8px;">正确答案：'+e(j.correct_answer)+'</div></div>'}document.getElementById('sb').textContent='继续下一题 →';document.getElementById('sb').onclick=()=>{idx++;nq()};document.getElementById('sb').disabled=false}catch(e){alert(e);document.getElementById('sb').disabled=false}}
function fp(){document.getElementById('p').innerHTML='<div class="crd" style="text-align:center;"><div style="font-size:40px;">🎉</div><div style="font-size:20px;font-weight:700;color:var(--t);">练习完成！</div><div style="font-size:14px;color:var(--ts);">正确 '+cc+'/'+vs.length+'</div><a href="/home" class="btn btn-p" style="margin-top:16px;">返回首页</a></div>'}
function e(s){let d=document.createElement('div');d.textContent=s||'';return d.innerHTML}
</script>"""
    return HTMLResponse(_page("录入错题",body))

@app.post("/mistake/new")
async def mistake_post(request:Request):
    a=require_auth(request)
    if a: return a
    form=await request.form()
    problem=form.get("problem","").strip(); wrong=form.get("wrong_answer","").strip()
    if not problem: return JSONResponse({"error":"题目不能为空"},400)
    pf=request.state.profile; grade=pf.get("grade_level","grade_4"); curriculum=pf.get("curriculum_version","人教版")
    from ai import diagnose_mistake,generate_variants
    try: diag=diagnose_mistake(problem,wrong,grade,curriculum)
    except Exception as e: return JSONResponse({"error":f"诊断失败: {e}"},500)
    conn=request.state.conn
    from db import insert_mistake,insert_variant
    mid=insert_mistake(conn,subject="math",original_problem=problem,wrong_answer=wrong,correct_answer=diag.get("correct_answer",""),knowledge_point=diag["knowledge_point"],error_type=diag["error_type"],error_analysis=diag["error_analysis"],pool_status="active",grade_level=grade,curriculum_ver=curriculum)
    try: variants=generate_variants(diag["knowledge_point"],diag["error_type"],diag["error_analysis"],grade,curriculum,"easy",3)
    except Exception as e: return JSONResponse({"error":f"变式生成失败: {e}"},500)
    diffs=["easy","easy","same"]; saved=[]
    for i,v in enumerate(variants):
        vid=insert_variant(conn,mistake_id=mid,problem_text=v["problem"],correct_answer=v["correct_answer"],difficulty=diffs[i] if i<len(diffs) else "same")
        saved.append({"id":vid,"problem":v["problem"],"difficulty":diffs[i] if i<len(diffs) else "same"})
    return JSONResponse({"mistake_id":mid,"diagnosis":diag,"variants":saved})

# ─── 答题 ───────────────────────────────────────────

@app.post("/answer/{variant_id}")
async def answer_post(request:Request, variant_id:int):
    a=require_auth(request)
    if a: return a
    form=await request.form(); student_answer=form.get("answer","").strip()
    conn=request.state.conn
    from db import get_variant,get_mistake,insert_attempt,upsert_mastery,update_pool_status,update_mastery_review
    variant=get_variant(conn,variant_id)
    if not variant: return JSONResponse({"error":"变式题不存在"},404)
    mistake=get_mistake(conn,variant["mistake_id"])
    if not mistake: return JSONResponse({"error":"错题不存在"},404)
    from ai import check_answer
    result=check_answer(variant["problem_text"],variant["correct_answer"],student_answer,mistake["knowledge_point"],mistake["error_analysis"])
    insert_attempt(conn,variant_id=variant_id,student_answer=student_answer,is_correct=1 if result["is_correct"] else 0,same_error=1 if result.get("same_error_pattern") else 0,feedback=result["feedback"],hint=result.get("hint"),action_type=result.get("action_type","correct"))
    mastery=upsert_mastery(conn,mistake["knowledge_point"],mistake.get("subject","math"),result["is_correct"])
    from scheduler import determine_pool_transition
    new_pool,next_review=determine_pool_transition(mistake["pool_status"],result["is_correct"],mastery["streak"],mastery["mastery_score"])
    if new_pool!=mistake["pool_status"]: update_pool_status(conn,mistake["id"],new_pool)
    if next_review: update_mastery_review(conn,mastery["knowledge_point"],mistake.get("subject","math"),next_review,new_pool)
    return JSONResponse({"is_correct":result["is_correct"],"feedback":result["feedback"],"hint":result.get("hint"),"action_type":result.get("action_type","correct"),"correct_answer":variant["correct_answer"],"mastery":{"score":mastery["mastery_score"],"streak":mastery["streak"]}})

# ─── 知识版图 ──────────────────────────────────────

@app.get("/map",response_class=HTMLResponse)
async def map_page(request:Request):
    a=require_auth(request)
    if a: return a
    conn=request.state.conn
    from db import get_all_masteries
    ms=get_all_masteries(conn,"math"); dorm=sum(1 for m in ms if m["pool_status"]=="dormant"); overall=sum(m["mastery_score"] for m in ms)/len(ms) if ms else 0
    mh=""
    for m in ms:
        sc=m["mastery_score"]; color="#3D5FD9" if sc>=0.7 else ("#D9821A" if sc>=0.4 else "#E04050")
        bg="var(--rb)" if sc<0.4 else "var(--w)"; pf_cl="#28A745" if sc>=0.9 else ("#3D5FD9" if sc>=0.7 else ("#D9821A" if sc>=0.4 else "#E04050"))
        st="熟练" if m["pool_status"]=="dormant" else ("攻克" if m["pool_status"]=="active" else "加强")
        tc="tag-m" if m["pool_status"]=="dormant" else ("tag-w" if m["pool_status"]=="active" else "tag-i")
        mh+=f"""<div class="crd2" style="background:{bg};"><div class="kpr"><span class="nm">{_esc(m['knowledge_point'])}</span><span class="pct" style="color:{color};">{int(sc*100)}%</span><span class="tag {tc}">{st}</span></div><div class="prog"><div class="pf" style="width:{int(sc*100)}%;background:{pf_cl};"></div></div></div>"""
    body=f"""<div class="pg"><div class="nb"><a href="/home">← 返回</a><span class="tt">知识版图</span></div>
    <div style="text-align:center;font-size:13px;color:var(--ts);margin-bottom:16px;">已征服 <b>{dorm}</b> 个 · 整体 <b style="color:var(--b);">{int(overall*100)}%</b></div>
    {mh or '<div style="text-align:center;padding:60px;color:var(--ts);"><div style="font-size:40px;">🗺️</div><div>暂无数据</div></div>'}
    <div style="display:flex;gap:16px;justify-content:center;margin-top:16px;font-size:11px;color:var(--tw);"><span>🟢 熟练</span><span>🟡 加强</span><span>🔴 攻克</span></div></div>"""
    return HTMLResponse(_page("知识版图",body,("","1","")))

# ─── 学习报告 ──────────────────────────────────────

@app.get("/report",response_class=HTMLResponse)
async def report_page(request:Request):
    a=require_auth(request)
    if a: return a
    n=request.state.student; conn=request.state.conn
    from db import get_all_masteries
    ms=get_all_masteries(conn,"math"); overall=sum(m["mastery_score"] for m in ms)/len(ms) if ms else 0
    mh=""
    for m in ms:
        sc=m["mastery_score"]; color="var(--b)" if sc>=0.7 else ("var(--a)" if sc>=0.4 else "var(--r)")
        cl="card-w" if sc<0.4 else ("card-i" if sc<0.7 else "")
        tc="tag-w" if m["pool_status"]=="active" else ("tag-i" if m["pool_status"]=="observing" else "tag-m")
        lb="熟练" if m["pool_status"]=="dormant" else ("攻克" if m["pool_status"]=="active" else "加强")
        mh+=f"""<div class="crd {cl}"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;"><span style="font-size:14px;font-weight:600;color:var(--t);">{_esc(m['knowledge_point'])}</span><span style="font-size:22px;font-weight:800;color:{color};">{int(sc*100)}%</span><span class="tag {tc}">{lb}</span></div><div class="prog"><div class="pf" style="width:{int(sc*100)}%;background:{color};"></div></div><div style="font-size:11px;color:var(--tw);margin-top:4px;">连续正确 {m['streak']} 次 · {m['total_attempts']} 次练习</div></div>"""
    body=f"""<div class="pg"><div class="nb"><a href="/home">← 返回</a><span class="tt">学习报告</span></div>
    <div style="text-align:center;font-size:12px;color:var(--ts);margin-bottom:12px;">{_esc(n)}的数学 · 知识版图</div>
    <div class="hero"><div style="font-size:11px;font-weight:700;color:var(--ts);text-transform:uppercase;letter-spacing:1.5px;">当前掌握度</div><div class="big">{int(overall*100)}%</div><div style="font-size:15px;font-weight:700;color:var(--b);margin:4px 0;">{"基本掌握" if overall>=0.7 else ("仍需加强" if overall>=0.4 else "仍未掌握")}</div><div class="sub">{len(ms)} 个知识点</div></div>
    {mh or '<div style="text-align:center;padding:60px;color:var(--ts);"><div style="font-size:40px;">📊</div><div>暂无数据</div></div>'}</div>"""
    return HTMLResponse(_page("学习报告",body,("","","1")))

# ─── 错题回顾 ──────────────────────────────────────

@app.get("/mistakes",response_class=HTMLResponse)
async def mistakes_list(request:Request):
    a=require_auth(request)
    if a: return a
    conn=request.state.conn
    from db import list_mistakes
    ms=list_mistakes(conn,limit=100)
    em={"knowledge_gap":"知识盲区","thinking_error":"思路错误","careless":"粗心"}
    ps={"active":"攻克中","observing":"观察中","dormant":"已掌握"}
    pc={"active":"tag-w","observing":"tag-i","dormant":"tag-m"}
    mh=""
    for m in ms:
        ec=("tag-kg" if m['error_type']=='knowledge_gap' else ("tag-te" if m['error_type']=='thinking_error' else "tag-cl"))
        mh+=f"""<div class="crd2"><div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;"><span class="tag {ec}">{em.get(m['error_type'],m['error_type'])}</span><span class="tag {pc.get(m['pool_status'],'tag-m')}">{ps.get(m['pool_status'],m['pool_status'])}</span><span style="flex:1;"></span><span style="font-size:11px;color:var(--tw);">{m['created_at'][:10]}</span></div><div style="font-size:13px;color:var(--t);line-height:1.6;">{_esc(m['original_problem'][:80])}</div><div style="font-size:11px;color:var(--ts);margin-top:4px;">{_esc(m['knowledge_point'])} · 你答：<span style="color:var(--r);">{_esc(m['wrong_answer'][:20])}</span></div></div>"""
    body=f"""<div class="pg"><div class="nb"><a href="/home">← 返回</a><span class="tt">错题回顾</span></div>
    {mh or '<div style="text-align:center;padding:60px;color:var(--ts);"><div style="font-size:40px;">📋</div><div>还没有错题记录</div></div>'}</div>"""
    return HTMLResponse(_page("错题回顾",body,("1","","")))

# ─── 启动 ───────────────────────────────────────────

if __name__=="__main__":
    import uvicorn, traceback
    port=int(os.environ.get("PORT",8080))
    try:
        print(f"🚀 错题Pro 启动于端口 {port}", flush=True)
        uvicorn.run("app:app",host="0.0.0.0",port=port,log_level="info",reload=False)
    except Exception as e:
        print(f"❌ 启动失败: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)

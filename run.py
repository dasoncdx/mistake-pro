"""错题Pro - FastAPI Web应用"""
import os, sys, json, hashlib
from urllib.parse import quote, unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
# Zeabur容器: /tmp 有写权限
_DATA_ROOT = "/tmp/mistake_pro_data" if os.path.exists("/tmp") and not os.access(ROOT, os.W_OK) else ROOT

from dotenv import load_dotenv; load_dotenv()
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# 强制db.py用/tmp写数据
import db
db.DB_DIR = os.path.join(_DATA_ROOT, "user_data")

app = FastAPI(title="错题Pro")

# 静态文件服务
static_dir = os.path.join(ROOT, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

saved_dir = os.path.join(ROOT, "saved")
os.makedirs(saved_dir, exist_ok=True)
app.mount("/saved", StaticFiles(directory=saved_dir), name="saved")

# ─── 全局错误处理 ────────────────────────────────
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

GRADE_OPTIONS = [
    ("grade_1", "小一"), ("grade_2", "小二"), ("grade_3", "小三"),
    ("grade_4", "小四"), ("grade_5", "小五"), ("grade_6", "小六"),
    ("grade_7", "初一"), ("grade_8", "初二"), ("grade_9", "初三"),
    ("grade_10", "高一"), ("grade_11", "高二"), ("grade_12", "高三"),
]
GRADE_LABELS = dict(GRADE_OPTIONS)
SUBJECT_NAMES = {"math": "数学", "english": "英语", "chinese": "语文"}

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

_LOGIN_PAGE = r"""<div class="login-page">
  <!-- Logo 区 -->
  <div class="login-logo">
    <div class="login-icon">
      <svg width="72" height="72" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="72" height="72" rx="20" fill="#3B82F6"/>
        <path d="M22 22 L50 50" stroke="#FFF" stroke-width="4.5" stroke-linecap="round"/>
        <path d="M50 22 L22 50" stroke="#FFF" stroke-width="4.5" stroke-linecap="round"/>
        <path d="M44 14 L56 14 L56 26" stroke="#FFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      </svg>
    </div>
    <div class="login-brand">错题<span class="login-brand-accent">Pro</span></div>
    <div class="login-subtitle">让每一道错题，变成知识版图上被征服的领地</div>
  </div>

  <!-- 登录表单 -->
  <div class="login-form">
    <div class="login-error" id="loginError" style="display:none;"></div>
    <input class="login-input" id="loginName" type="text" placeholder="手机号 / 昵称" autocomplete="username">
    <input class="login-input" id="loginPass" type="password" placeholder="输入密码" autocomplete="current-password">
    <button class="login-btn" onclick="doLogin()">登 录</button>
  </div>

  <!-- 底部引导 -->
  <div class="login-footer">
    还没有账号？<a href="/register" class="login-link">立即注册</a>
  </div>
</div>

<style>
.login-page{max-width:420px;margin:0 auto;padding:0 28px;display:flex;flex-direction:column;min-height:100vh;justify-content:center}
.login-logo{text-align:center;margin-bottom:36px}
.login-icon{margin:0 auto 20px;width:72px;height:72px}
.login-brand{font-size:32px;font-weight:800;color:var(--t);letter-spacing:-1px}
.login-brand-accent{color:var(--b)}
.login-subtitle{font-size:13px;color:var(--ts);margin-top:10px;line-height:1.5}
.login-form{display:flex;flex-direction:column;gap:14px}
.login-input{width:100%;height:52px;background:var(--bg);border:1.5px solid var(--br);border-radius:14px;padding:0 18px;font-size:16px;color:var(--t);outline:none;font-family:inherit;transition:border-color .2s}
.login-input:focus{border-color:var(--b);background:var(--w)}
.login-input::placeholder{color:var(--tw)}
.login-btn{width:100%;height:52px;background:var(--b);color:#FFF;border:none;border-radius:14px;font-size:17px;font-weight:600;cursor:pointer;font-family:inherit;margin-top:8px;transition:opacity .2s}
.login-btn:active{opacity:.85}
.login-error{background:var(--rb);color:var(--r);padding:12px 16px;border-radius:12px;font-size:14px;text-align:center}
.login-footer{text-align:center;margin-top:32px;font-size:14px;color:var(--ts)}
.login-link{color:var(--b);font-weight:600;text-decoration:none}
</style>
<script>
async function doLogin(){
  var n=document.getElementById('loginName').value.trim();
  var p=document.getElementById('loginPass').value;
  if(!n) return showErr('请输入手机号或昵称');
  if(!p) return showErr('请输入密码');
  var d=new FormData();d.append('name',n);d.append('password',p);
  try{
    var r=await fetch('/login',{method:'POST',body:d});
    if(r.redirected){window.location.href=r.url;return}
    if(r.url.indexOf('error=')>-1){
      var err=new URL(r.url).searchParams.get('error')||'登录失败';
      showErr(err);
    }else{window.location.href=r.url}
  }catch(e){showErr('网络错误，请重试')}
}
function showErr(msg){var el=document.getElementById('loginError');el.textContent=msg;el.style.display='block'}
</script>"""

_NAV_ICONS = {
    "notebook": {
        'on': r'<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M4 19.5A2.5 2.5 0 016.5 17H20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 7h8M8 11h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
        'off': r'<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M4 19.5A2.5 2.5 0 016.5 17H20" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 7h8M8 11h8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
    },
    "exam_points": {
        'on': r'<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="1.5" stroke="currentColor" stroke-width="1.8"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
        'off': r'<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="1.5" stroke="currentColor" stroke-width="1.6"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
    },
    "profile": {
        'on': r'<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="1.8"/><path d="M4 22c0-4.418 3.582-8 8-8s8 3.582 8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
        'off': r'<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="1.6"/><path d="M4 22c0-4.418 3.582-8 8-8s8 3.582 8 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
    },
}

def _nav_bar(active=""):
    def icon(key, active_cond):
        return _NAV_ICONS[key]['on'] if active_cond else _NAV_ICONS[key]['off']
    return f"""<nav class="bn"><a href="/home" class="{'on' if active=='notebook' else ''}">{icon('notebook', active=='notebook')}<span>错题本</span></a><a href="/exam-points" class="{'on' if active=='exam_points' else ''}">{icon('exam_points', active=='exam_points')}<span>考点通</span></a><a href="/profile" class="{'on' if active=='profile' else ''}">{icon('profile', active=='profile')}<span>我的</span></a></nav>"""

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return HTMLResponse(_pg(_LOGIN_PAGE, "登录"))

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

_REG_PAGE = """<div class="pg"><div class="nb"><a href="/login">← 返回</a></div><div style="text-align:center;font-size:19px;font-weight:700;color:var(--t);margin-bottom:24px;">创建账号</div><form method="post" action="/register">
<div class="label">昵称</div><input class="inp" name="name" placeholder="输入昵称" required>
<div class="label">密码</div><input class="inp" name="password" type="password" placeholder="至少3位" required minlength="3">
<input class="inp" name="password2" type="password" placeholder="确认密码" required>
<button class="btn btn-p" style="margin-top:12px;">确认，开始使用</button></form></div>"""

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return HTMLResponse(_pg(_REG_PAGE, "注册"))

@app.post("/register")
async def register_post(request: Request):
    form=await request.form(); n=form.get("name","").strip(); p1=form.get("password",""); p2=form.get("password2","")
    if not n or len(p1)<3: return RedirectResponse("/register?error=昵称必填，密码至少3位",302)
    if p1!=p2: return RedirectResponse("/register?error=两次密码不一致",302)
    s=os.urandom(16); h=hashlib.pbkdf2_hmac("sha256",p1.encode(),s,200000)
    _users[n]={"student_name":n,"password_hash":s.hex()+":"+h.hex(),"province":"","city":"","district":"","grade_level":"grade_4","curriculum_version":"人教版","subjects":["math"],"version":"basic"}
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
    pf = ctx.get("profile", {})
    subjects = pf.get("subjects", ["math"])
    grade = pf.get("grade_level", "grade_4")
    grade_label = GRADE_LABELS.get(grade, "小四")

    conn = ctx.get("conn")
    subject_cards = ""
    all_subjects = list(SUBJECT_NAMES.keys())
    for subj in subjects:
        count = 0
        if conn:
            from db import list_mistakes
            ms = list_mistakes(conn, subject=subj, limit=1000)
            count = len(ms)
        can_remove = len(subjects) > 1
        subject_cards += f'''<div class="subject-card-row">
          <a href="/mistakes?subject={subj}" class="subject-card">
            <span class="subject-name">{SUBJECT_NAMES.get(subj, subj)}</span>
            <span class="subject-count">{count} 道错题</span>
          </a>
          {f'<button class="subject-remove" onclick="removeSubject(\'{subj}\')" title="移除">×</button>' if can_remove else ''}
        </div>'''

    # Subjects not yet added
    available = [s for s in all_subjects if s not in subjects]
    add_html = ""
    if available:
        add_html = '<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">' + ''.join(
            f'<button class="subject-add-btn" onclick="addSubject(\'{s}\')">+ {SUBJECT_NAMES.get(s, s)}</button>' for s in available
        ) + '</div>'

    grade_options = ''.join(f'<option value="{k}" {"selected" if k==grade else ""}>{v}</option>' for k,v in GRADE_OPTIONS)

    body = f"""<div class="pg">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:20px;">
      <select class="grade-select" onchange="updateGrade(this.value)">{grade_options}</select>
      <span style="font-size:14px;color:var(--ts);margin-left:auto;">{n}</span>
    </div>
    <a href="/mistake/new" class="record-card">
      <div class="record-icon">📝</div>
      <div class="record-label">录错题</div>
      <div class="record-desc">拍照或手动录入错题，AI 智能诊断</div>
    </a>
    <div class="section-title">我的错题本</div>
    <div class="subject-grid">{subject_cards or "<div style='color:var(--ts);font-size:13px;padding:12px 0;'>暂无科目，先录入错题吧</div>"}</div>
    {add_html}
    </div>
    <script>
    async function updateGrade(v){{
      var d=new FormData();d.append('grade',v);
      await fetch('/update-grade',{{method:'POST',body:d}});
    }}
    async function addSubject(s){{
      var d=new FormData();d.append('subject',s);
      await fetch('/add-subject',{{method:'POST',body:d}});
      location.reload();
    }}
    async function removeSubject(s){{
      if(!confirm('确定移除 '+s+' ？')) return;
      var d=new FormData();d.append('subject',s);
      await fetch('/remove-subject',{{method:'POST',body:d}});
      location.reload();
    }}
    </script>"""
    return HTMLResponse(_pg(body, "错题本", "notebook"))

# ─── 录入 ──────────────────────────────────────

_JS_OCR = r"""
var _processedImg='';
var _selections=[];  // [{id, x1,y1,x2,y2}], coords 0~1 relative to img natural size
var _nextId=0;
var _drawing=null;   // {startX,startY,x1,y1,x2,y2} in px relative to imgWrap

async function processImage(inputEl){
  var f=inputEl.files[0];
  if(!f) return;
  document.getElementById('f').style.display='none';
  document.getElementById('ld').style.display='block';
  document.getElementById('ldMsg').textContent='压缩图片...';
  var d=new FormData();d.append('photo',f);d.append('subject',document.getElementById('curSubject').value);
  try{
    var r=await fetch('/mistake/process-image',{method:'POST',body:d});
    var j=await r.json();
    if(j.error){alert(j.error);location.reload();return}
    document.getElementById('ld').style.display='none';
    _processedImg=j.processed_image_url;
    _selections=[];_nextId=0;
    renderDrawUI();
  }catch(e){alert('处理失败：'+e.message);location.reload()}
}

function renderDrawUI(){
  var sel=document.getElementById('sel');
  sel.className='sel-overlay';
  var html='<div class="sel-topbar"><span class="sel-topbar-title">框选题目区域</span><button class="sel-close" onclick="location.reload()">✕</button></div>';
  html+='<div class="sel-hint" style="text-align:center;font-size:12px;color:var(--ts);padding:4px 12px;">手指拖动画框 · 拖拽四角微调 · 拖拽框体移动 · ✕ 删除</div>';
  html+='<div class="sel-scroll" id="selScroll">';
  html+='<div class="draw-wrap" id="drawWrap">';
  html+='<img src="'+_processedImg+'" class="draw-img" id="drawImg" onload="onImgLoad()">';
  html+='<div class="draw-layer" id="drawLayer"></div>';
  html+='</div>';
  html+='</div>';
  html+='<div class="sel-bottombar">';
  html+='<span class="sel-count" id="selCount">已选 0 题</span>';
  html+='<button class="btn btn-p" id="selConfirmBtn" onclick="saveSelections()">保存选题</button>';
  html+='</div>';
  sel.innerHTML=html;sel.style.display='flex';
  setTimeout(bindDrawEvents,50);
}

function onImgLoad(){
  syncSelectionDivs();
  bindDrawEvents();
}

// ---- coordinate helpers ----
function imgToNorm(px,py){
  var img=document.getElementById('drawImg');
  return {x:px/img.clientWidth, y:py/img.clientHeight};
}
function normToImg(nx,ny){
  var img=document.getElementById('drawImg');
  return {x:nx*img.clientWidth, y:ny*img.clientHeight};
}
function clampNorm(v){return Math.max(0,Math.min(1,v));}

function getLayerOffset(e){
  var layer=document.getElementById('drawLayer');
  var rect=layer.getBoundingClientRect();
  return {x:e.clientX-rect.left, y:e.clientY-rect.top};
}

// ---- render selection box with resize handles ----
function renderSelectionBox(s){
  var layer=document.getElementById('drawLayer');
  var id='selbox_'+s.id;
  var el=document.getElementById(id);
  if(!el){
    el=document.createElement('div');el.id=id;el.className='selbox';
    el.innerHTML='<div class="shandle sh-tl" data-corner="tl"></div><div class="shandle sh-tr" data-corner="tr"></div><div class="shandle sh-bl" data-corner="bl"></div><div class="shandle sh-br" data-corner="br"></div><div class="selbox-del">✕</div>';
    el.querySelector('.selbox-del').addEventListener('pointerdown',function(e){
      e.stopPropagation();e.preventDefault();
      _selections=_selections.filter(function(x){return x.id!==s.id});
      el.remove();updateCount();
    });
    el.addEventListener('pointerdown',function(e){
      e.stopPropagation();
      var corner=e.target.getAttribute('data-corner');
      if(corner){
        e.preventDefault();
        _dragMode='resize';_dragTarget={sel:s,corner:corner};
      }else if(e.target===el||e.target.classList.contains('selbox')){
        e.preventDefault();
        _dragMode='move';
        var off=getLayerOffset(e);
        _dragTarget={sel:s,startX:off.x,startY:off.y,origX1:s.x1,origY1:s.y1,origX2:s.x2,origY2:s.y2};
      }
    });
    layer.appendChild(el);
  }
  var p=normToImg(s.x1,s.y1);
  var p2=normToImg(s.x2,s.y2);
  el.style.left=p.x+'px';
  el.style.top=p.y+'px';
  el.style.width=Math.max(20,p2.x-p.x)+'px';
  el.style.height=Math.max(20,p2.y-p.y)+'px';
  el.style.display='block';
}

function syncSelectionDivs(){
  var layer=document.getElementById('drawLayer');
  var ids=new Set(_selections.map(function(s){return 'selbox_'+s.id}));
  Array.from(layer.children).forEach(function(c){
    if(!ids.has(c.id)&&(c.classList.contains('selbox')||c.id==='drawTmp')) c.remove();
  });
  _selections.forEach(function(s){renderSelectionBox(s);});
}

function updateCount(){
  var n=_selections.length;
  document.getElementById('selCount').textContent='已选 '+n+' 题';
  document.getElementById('selConfirmBtn').textContent=n>0?'保存选题（'+n+'题）':'保存选题';
}

var _dragMode=null;
var _dragTarget=null;

function bindDrawEvents(){
  var layer=document.getElementById('drawLayer');
  if(!layer||layer._bound) return;
  layer._bound=true;

  layer.addEventListener('pointerdown',function(e){
    if(_dragMode) return;
    if(e.target!==layer) return;
    e.preventDefault();
    var off=getLayerOffset(e);
    _drawing={x1:off.x,y1:off.y,x2:off.x,y2:off.y};
    _dragMode='draw';
  });

  layer.addEventListener('pointermove',function(e){
    if(!_dragMode) return;
    e.preventDefault();
    var off=getLayerOffset(e);
    if(_dragMode==='draw'){
      if(!_drawing) return;
      _drawing.x2=off.x;_drawing.y2=off.y;
      var x=Math.min(_drawing.x1,_drawing.x2), y=Math.min(_drawing.y1,_drawing.y2);
      var w=Math.abs(_drawing.x2-_drawing.x1), h=Math.abs(_drawing.y2-_drawing.y1);
      var tmp=document.getElementById('drawTmp');
      if(!tmp){tmp=document.createElement('div');tmp.id='drawTmp';tmp.className='selbox selbox-tmp';layer.appendChild(tmp);}
      tmp.style.left=x+'px';tmp.style.top=y+'px';
      tmp.style.width=w+'px';tmp.style.height=h+'px';
    }else if(_dragMode==='resize'){
      var t=_dragTarget;
      var n=imgToNorm(off.x,off.y);
      if(t.corner==='tl'){t.sel.x1=clampNorm(n.x);t.sel.y1=clampNorm(n.y);}
      else if(t.corner==='tr'){t.sel.x2=clampNorm(n.x);t.sel.y1=clampNorm(n.y);}
      else if(t.corner==='bl'){t.sel.x1=clampNorm(n.x);t.sel.y2=clampNorm(n.y);}
      else if(t.corner==='br'){t.sel.x2=clampNorm(n.x);t.sel.y2=clampNorm(n.y);}
      if(t.sel.x1>t.sel.x2){var tx=t.sel.x1;t.sel.x1=t.sel.x2;t.sel.x2=tx;}
      if(t.sel.y1>t.sel.y2){var ty=t.sel.y1;t.sel.y1=t.sel.y2;t.sel.y2=ty;}
      renderSelectionBox(t.sel);
    }else if(_dragMode==='move'){
      var tm=_dragTarget;
      var nm=imgToNorm(off.x,off.y);
      var startNorm=imgToNorm(tm.startX,tm.startY);
      var dw=nm.x-startNorm.x, dh=nm.y-startNorm.y;
      var nw=tm.origX2-tm.origX1, nh=tm.origY2-tm.origY1;
      tm.sel.x1=clampNorm(tm.origX1+dw);tm.sel.y1=clampNorm(tm.origY1+dh);
      tm.sel.x2=clampNorm(tm.origX2+dw);tm.sel.y2=clampNorm(tm.origY2+dh);
      if(tm.sel.x2-tm.sel.x1<0.01){tm.sel.x2=tm.sel.x1+nw;}
      if(tm.sel.y2-tm.sel.y1<0.01){tm.sel.y2=tm.sel.y1+nh;}
      renderSelectionBox(tm.sel);
    }
  });

  function endDrag(e){
    if(_dragMode==='draw'&&_drawing){
      var dx=Math.abs(_drawing.x2-_drawing.x1), dy=Math.abs(_drawing.y2-_drawing.y1);
      var tmp=document.getElementById('drawTmp');if(tmp)tmp.remove();
      if(dx>20&&dy>20){
        var n1=imgToNorm(Math.min(_drawing.x1,_drawing.x2),Math.min(_drawing.y1,_drawing.y2));
        var n2=imgToNorm(Math.max(_drawing.x1,_drawing.x2),Math.max(_drawing.y1,_drawing.y2));
        var s={id:_nextId++,x1:clampNorm(n1.x),y1:clampNorm(n1.y),x2:clampNorm(n2.x),y2:clampNorm(n2.y)};
        _selections.push(s);renderSelectionBox(s);updateCount();
      }
      _drawing=null;
    }
    _dragMode=null;_dragTarget=null;
  }

  layer.addEventListener('pointerup',endDrag);
  layer.addEventListener('pointerleave',function(e){
    if(_dragMode==='draw'){var tmp=document.getElementById('drawTmp');if(tmp)tmp.remove();_drawing=null;}
    _dragMode=null;_dragTarget=null;
  });
}

// ---- save ----
async function saveSelections(){
  if(_selections.length===0) return alert('请至少框选一个题目区域');
  document.getElementById('sel').style.display='none';
  document.getElementById('ld').style.display='block';
  document.getElementById('ldMsg').textContent='正在保存...';
  var d=new FormData();
  d.append('image_path',_processedImg);
  var regions=_selections.map(function(s){return{x1:s.x1,y1:s.y1,x2:s.x2,y2:s.y2};});
  d.append('regions',JSON.stringify(regions));
  d.append('subject',document.getElementById('curSubject').value);
  try{
    var r=await fetch('/mistake/save-regions',{method:'POST',body:d}),j=await r.json();
    if(j.error){alert(j.error);location.reload();return}
    document.getElementById('ld').style.display='none';
    var subj=document.getElementById('curSubject').value;
    var html='<div style="text-align:center;padding:20px;"><div style="font-size:48px;margin-bottom:12px;">&#x2705;</div><div style="font-size:16px;font-weight:700;color:var(--t);margin-bottom:4px;">保存成功</div><div style="font-size:13px;color:var(--ts);">已保存 '+j.count+' 道题目</div><div style="margin-top:16px;display:flex;gap:10px;justify-content:center;"><button class="btn btn-p" onclick="location.reload()">继续录入</button><a href="/mistakes?subject='+subj+'" class="btn" style="background:var(--c);border:1.5px solid var(--b);color:var(--b);padding:12px 20px;border-radius:12px;font-size:14px;font-weight:600;text-decoration:none;display:inline-block;">查看错题本</a></div></div>';
    document.getElementById('r').innerHTML=html;document.getElementById('r').style.display='block';
  }catch(e){alert(e);location.reload()}
}

window.addEventListener('resize',function(){if(_selections.length>0)syncSelectionDivs();});

async function goM(){
  var a=document.getElementById('prob').value.trim();
  if(!a) return alert('请输入题目');
  document.getElementById('f').style.display='none';
  document.getElementById('ld').style.display='block';
  document.getElementById('ldMsg').textContent='AI正在诊断...';
  var d=new FormData();d.append('problem',a);d.append('wrong_answer','');d.append('subject',document.getElementById('curSubject').value);
  try{
    var r=await fetch('/mistake/new',{method:'POST',body:d}),j=await r.json();
    if(j.error){alert(j.error);location.reload();return}
    document.getElementById('ld').style.display='none';
    var et={knowledge_gap:'知识盲区',thinking_error:'思路错误',careless:'粗心'};
    document.getElementById('r').innerHTML='<div class="crd" style="background:rgba(91,127,255,.03);border:1px solid rgba(91,127,255,.06);"><div style="font-size:12px;color:var(--ts);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">AI 诊断</div><div style="font-size:16px;font-weight:700;color:var(--t);margin-bottom:12px;">'+esc(j.diagnosis.knowledge_point)+'</div><div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;"><span class="tag tag-w">'+et[j.diagnosis.error_type]+'</span><span style="font-size:13px;color:var(--ts);line-height:1.6;">'+esc(j.diagnosis.error_analysis)+'</span></div><div style="display:flex;align-items:flex-start;gap:8px;"><span class="tag" style="background:var(--bb);color:#3D5FD9;">正确答案</span><span style="font-size:13px;color:var(--t);font-weight:600;">'+esc(j.diagnosis.correct_answer)+'</span></div></div><p style="font-size:13px;color:var(--ts);margin:12px 0;">已生成 <b>'+j.variants.length+'</b> 道变式题</p>';
    document.getElementById('r').style.display='block';
    vs=j.variants;idx=0;cc=0;nq();
  }catch(e){alert(e);location.reload()}
}
function nq(){
  if(idx>=vs.length){fp();return}
  var v=vs[idx];
  var dl={easy:'🟢 热身',same:'🟡 标准',slightly_harder:'🔴 挑战'}[v.difficulty]||'';
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
function esc(s){var d=document.createElement('div');d.textContent=s||'';return d.innerHTML}"""

_JS_MISTAKES = r"""<script>
var _origTexts={};
var _selAll=false;
function onTxtChange(id){
  var ta=document.getElementById('txt-'+id), acts=document.getElementById('acts-'+id);
  if(!ta||!acts)return;
  var cur=ta.value, orig=_origTexts[id];
  if(orig===undefined) _origTexts[id]=ta.defaultValue;
  if(cur!==(_origTexts[id]!==undefined?_origTexts[id]:ta.defaultValue)){
    acts.style.display='flex';
  }else{
    acts.style.display='none';
  }
}
async function saveTxt(id){
  var ta=document.getElementById('txt-'+id), hint=document.getElementById('hint-'+id), acts=document.getElementById('acts-'+id);
  if(!ta)return;
  var r=await fetch('/mistake/edit/'+id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ocr_text:ta.value})});
  if(r.ok){_origTexts[id]=ta.value;ta.defaultValue=ta.value;acts.style.display='none';hint.style.display='inline';setTimeout(function(){hint.style.display='none'},1500)}
  else alert('保存失败')
}
function onChk(){
  _selAll=false;document.getElementById('selectAll').checked=false;
  var bar=document.getElementById('batchBar'), cnt=document.getElementById('batchCount'), ids=getSelIds();
  bar.style.display=ids.length>0?'flex':'none';
  cnt.textContent='已选 '+ids.length+' 道';
}
function toggleAll(el){
  _selAll=el.checked;
  document.querySelectorAll('.mcrd-check').forEach(function(c){c.checked=el.checked});
  onChk();
}
function getSelIds(){
  if(_selAll){
    var span=document.getElementById('allFilteredIds');
    if(span){
      try{var ids=JSON.parse(span.getAttribute('data-ids'));return ids;}catch(e){}
    }
  }
  var ids=[];
  document.querySelectorAll('.mcrd-check:checked').forEach(function(c){ids.push(parseInt(c.getAttribute('data-id')))});
  return ids;
}
function applyDateFilter(){
  var from=document.getElementById('dateFrom').value, to=document.getElementById('dateTo').value;
  var url=new URL(location);
  if(from) url.searchParams.set('date_from',from); else url.searchParams.delete('date_from');
  if(to) url.searchParams.set('date_to',to); else url.searchParams.delete('date_to');
  url.searchParams.delete('page');
  location.href=url;
}
function clearDateFilter(){
  var url=new URL(location);
  url.searchParams.delete('date_from');url.searchParams.delete('date_to');url.searchParams.delete('page');
  location.href=url;
}
function goPage(n){
  var url=new URL(location);
  url.searchParams.set('page',n);
  location.href=url;
}
async function delMis(id){
  if(!confirm('确定删除这道错题吗？'))return;
  var r=await fetch('/mistake/delete/'+id,{method:'POST'});
  if(r.ok){var card=document.getElementById('card-'+id);if(card)card.remove();onChk()}
  else alert('删除失败')
}
async function delSel(){
  var ids=getSelIds();
  if(ids.length===0)return;
  if(!confirm('确定删除已选的 '+ids.length+' 道错题吗？'))return;
  for(var i=0;i<ids.length;i++){
    await fetch('/mistake/delete/'+ids[i],{method:'POST'});
    var card=document.getElementById('card-'+ids[i]);if(card)card.remove();
  }
  onChk();
}
function exportSel(){
  var ids=getSelIds();
  if(ids.length===0){alert('请先选择错题');return}
  window.open('/mistake/export?ids='+ids.join(',')+'&download=1','_blank');
}
async function delFig(figId,btn){
  if(!confirm('删除此图案？'))return;
  var r=await fetch('/mistake/delete-figure/'+figId,{method:'POST'});
  if(r.ok){var item=btn.closest('.fig-item');if(item)item.remove()}
  else alert('删除失败')
}

// ---- figure cropping overlay ----
var _figCropImg='', _figCropMid=0, _figDrawRect=null, _figDrawing=null, _figDragMode=null;

function openFigCrop(mid){
  _figCropMid=mid;
  var card=document.getElementById('card-'+mid);
  if(!card)return;
  var cropPath=card.getAttribute('data-crop');
  if(!cropPath)return;
  _figCropImg='/'+cropPath;
  _figDrawRect=null;_figDrawing=null;_figDragMode=null;
  var ov=document.createElement('div');ov.id='figOverlay';ov.className='fig-overlay';
  ov.innerHTML='<div class="fig-topbar"><span class="fig-topbar-title">截取图案</span><button class="fig-close" onclick="closeFigCrop()">✕</button></div>'
    +'<div class="fig-hint">手指拖动画框，框选需保留的示意图/几何图</div>'
    +'<div class="fig-scroll"><div class="fig-draw-wrap" id="figDrawWrap">'
    +'<img src="'+_figCropImg+'" class="fig-draw-img" id="figDrawImg">'
    +'<div class="fig-draw-layer" id="figDrawLayer"></div>'
    +'</div></div>'
    +'<div class="fig-bottombar"><button class="btn" style="background:var(--c);border:1.5px solid var(--br);color:var(--ts);padding:10px 20px;border-radius:20px;font-size:14px;font-family:inherit;cursor:pointer" onclick="closeFigCrop()">取消</button><button class="btn btn-p" onclick="saveFigCrop()">保存图案</button></div>';
  document.body.appendChild(ov);
  setTimeout(bindFigDraw,100);
}

function closeFigCrop(){
  var ov=document.getElementById('figOverlay');if(ov)ov.remove();
}

function bindFigDraw(){
  var layer=document.getElementById('figDrawLayer');
  if(!layer||layer._bound)return;
  layer._bound=true;

  function figImgToNorm(px,py){
    var img=document.getElementById('figDrawImg');
    return {x:px/img.clientWidth, y:py/img.clientHeight};
  }
  function figNormToImg(nx,ny){
    var img=document.getElementById('figDrawImg');
    return {x:nx*img.clientWidth, y:ny*img.clientHeight};
  }
  function clamp(v){return Math.max(0,Math.min(1,v));}

  function getLayerOff(e){
    var r=layer.getBoundingClientRect();
    return {x:e.clientX-r.left, y:e.clientY-r.top};
  }

  function renderFigSel(){
    if(!_figDrawRect)return;
    var sel=document.getElementById('figDrawSel');
    var p1=figNormToImg(_figDrawRect.x1,_figDrawRect.y1);
    var p2=figNormToImg(_figDrawRect.x2,_figDrawRect.y2);
    if(!sel){
      sel=document.createElement('div');sel.id='figDrawSel';sel.className='selbox';
      sel.innerHTML='<div class="shandle sh-tl" data-corner="tl"></div><div class="shandle sh-tr" data-corner="tr"></div><div class="shandle sh-bl" data-corner="bl"></div><div class="shandle sh-br" data-corner="br"></div>';
      sel.addEventListener('pointerdown',function(e){
        e.stopPropagation();e.preventDefault();
        var corner=e.target.getAttribute('data-corner');
        if(corner){_figDragMode='resize';_figDragTarget={sel:_figDrawRect,corner:corner};}
        else if(e.target===sel||sel.contains(e.target)){
          _figDragMode='move';
          var off=getLayerOff(e);
          _figDragTarget={sel:_figDrawRect,startX:off.x,startY:off.y,origX1:_figDrawRect.x1,origY1:_figDrawRect.y1,origX2:_figDrawRect.x2,origY2:_figDrawRect.y2};
        }
      });
      layer.appendChild(sel);
    }
    sel.style.left=Math.min(p1.x,p2.x)+'px';
    sel.style.top=Math.min(p1.y,p2.y)+'px';
    sel.style.width=Math.max(20,Math.abs(p2.x-p1.x))+'px';
    sel.style.height=Math.max(20,Math.abs(p2.y-p1.y))+'px';
    sel.style.display='block';
  }

  layer.addEventListener('pointerdown',function(e){
    if(_figDragMode)return;
    if(e.target!==layer)return;
    e.preventDefault();
    var off=getLayerOff(e);
    _figDrawing={x1:off.x,y1:off.y};
    _figDragMode='draw';
  });

  layer.addEventListener('pointermove',function(e){
    if(!_figDragMode)return;
    e.preventDefault();
    var off=getLayerOff(e);
    if(_figDragMode==='draw'){
      if(!_figDrawing)return;
      var rx=Math.min(_figDrawing.x1,off.x), ry=Math.min(_figDrawing.y1,off.y);
      var rw=Math.abs(off.x-_figDrawing.x1), rh=Math.abs(off.y-_figDrawing.y1);
      var tmp=document.getElementById('figDrawTmp');
      if(!tmp){tmp=document.createElement('div');tmp.id='figDrawTmp';tmp.className='selbox selbox-tmp';layer.appendChild(tmp);}
      tmp.style.left=rx+'px';tmp.style.top=ry+'px';
      tmp.style.width=rw+'px';tmp.style.height=rh+'px';
    }else if(_figDragMode==='resize'){
      var t=_figDragTarget, n=figImgToNorm(off.x,off.y);
      if(t.corner==='tl'){t.sel.x1=clamp(n.x);t.sel.y1=clamp(n.y);}
      else if(t.corner==='tr'){t.sel.x2=clamp(n.x);t.sel.y1=clamp(n.y);}
      else if(t.corner==='bl'){t.sel.x1=clamp(n.x);t.sel.y2=clamp(n.y);}
      else if(t.corner==='br'){t.sel.x2=clamp(n.x);t.sel.y2=clamp(n.y);}
      if(t.sel.x1>t.sel.x2){var tx=t.sel.x1;t.sel.x1=t.sel.x2;t.sel.x2=tx;}
      if(t.sel.y1>t.sel.y2){var ty=t.sel.y1;t.sel.y1=t.sel.y2;t.sel.y2=ty;}
      renderFigSel();
    }else if(_figDragMode==='move'){
      var tm=_figDragTarget, nm=figImgToNorm(off.x,off.y);
      var sn=figImgToNorm(tm.startX,tm.startY);
      var dw=nm.x-sn.x, dh=nm.y-sn.y;
      var nw=tm.origX2-tm.origX1, nh=tm.origY2-tm.origY1;
      tm.sel.x1=clamp(tm.origX1+dw);tm.sel.y1=clamp(tm.origY1+dh);
      tm.sel.x2=clamp(tm.origX2+dw);tm.sel.y2=clamp(tm.origY2+dh);
      if(tm.sel.x2-tm.sel.x1<0.01){tm.sel.x2=tm.sel.x1+nw;}
      if(tm.sel.y2-tm.sel.y1<0.01){tm.sel.y2=tm.sel.y1+nh;}
      renderFigSel();
    }
  });

  layer.addEventListener('pointerup',function(e){
    if(_figDragMode==='draw'&&_figDrawing){
      var off=getLayerOff(e);
      var dx=Math.abs(off.x-_figDrawing.x1), dy=Math.abs(off.y-_figDrawing.y1);
      var tmp=document.getElementById('figDrawTmp');if(tmp)tmp.remove();
      if(dx>20&&dy>20){
        var img=document.getElementById('figDrawImg');
        var n1=figImgToNorm(Math.min(_figDrawing.x1,off.x),Math.min(_figDrawing.y1,off.y));
        var n2=figImgToNorm(Math.max(_figDrawing.x1,off.x),Math.max(_figDrawing.y1,off.y));
        _figDrawRect={x1:n1.x,y1:n1.y,x2:n2.x,y2:n2.y};
        renderFigSel();
      }
      _figDrawing=null;
    }
    _figDragMode=null;_figDragTarget=null;
  });
}

async function saveFigCrop(){
  if(!_figDrawRect){alert('请先框选图案区域');return}
  var d=new FormData();
  d.append('x1',_figDrawRect.x1);d.append('y1',_figDrawRect.y1);
  d.append('x2',_figDrawRect.x2);d.append('y2',_figDrawRect.y2);
  var r=await fetch('/mistake/crop-figure/'+_figCropMid,{method:'POST',body:d});
  if(r.ok){
    var j=await r.json();
    closeFigCrop();
    var figs=document.getElementById('figs-'+_figCropMid);
    if(figs){
      var item=document.createElement('div');item.className='fig-item';
      item.innerHTML='<img src="/'+j.image_path+'" class="fig-thumb"><span class="fig-label">'+(j.label||'图')+'</span><button class="fig-del" onclick="delFig('+j.figure_id+',this)">✕</button>';
      figs.appendChild(item);
    }
  }else{alert('截取失败')}
}
</script>"""

@app.get("/mistake/new", response_class=HTMLResponse)
async def mistake_page(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    html = r"""<div class="pg"><div class="nb"><a href="/home">← 返回</a></div>
    <div class="mistake-title">录入错题</div>
    <div id="f">
    <div class="section-label">一、选择学科</div>
    <div class="chip-row" style="margin-bottom:16px;">
      <label class="chip sel" onclick="setSubj('math',this)"><span class="dot"></span> 数学</label>
      <label class="chip" onclick="setSubj('english',this)"><span class="dot"></span> 英语</label>
      <label class="chip" onclick="setSubj('chinese',this)"><span class="dot"></span> 语文</label>
    </div>
    <input type="hidden" id="curSubject" value="math">
    <div class="section-label" style="margin-top:8px;">二、录入方式</div>
    <div class="sub-label">方式一：拍照识别（推荐）</div>
    <input type="file" id="photoCamera" accept="image/*" capture="environment" style="display:none;" onchange="processImage(this)">
    <input type="file" id="photoGallery" accept="image/*" style="display:none;" onchange="processImage(this)">
    <div class="photo-btns">
      <button type="button" class="photo-btn photo-btn-camera" onclick="document.getElementById('photoCamera').click()">
        <span class="photo-btn-icon">📷</span>拍照识别
      </button>
      <button type="button" class="photo-btn photo-btn-gallery" onclick="document.getElementById('photoGallery').click()">
        <span class="photo-btn-icon">🖼️</span>选择文件
      </button>
    </div>
    <div class="sub-label" style="margin-top:20px;">方式二：手动输入</div>
    <textarea class="txa" id="prob" placeholder="输入题目..."></textarea>
    <button class="btn btn-p" onclick="goM()">提交，开始AI诊断</button></div>
    <div id="ld" style="display:none;text-align:center;padding:40px;"><div class="spinner"></div><div id="ldMsg" style="color:var(--ts);">AI正在识别题目...</div></div>
    <div id="sel" style="display:none;"></div>
    <div id="r" style="display:none;"></div><div id="p" style="display:none;"></div></div>
    <script>function setSubj(s,el){document.querySelectorAll('.chip-row .chip').forEach(function(c){c.classList.remove('sel')});el.classList.add('sel');document.getElementById('curSubject').value=s};</script>
    <script>""" + _JS_OCR + "</script>"
    return HTMLResponse(_pg(html, "录入错题"))

@app.post("/mistake/process-image")
async def mistake_process_image(request: Request):
    """压缩上传图片（长边≤2048px, ≤2MB），保证文字清晰可读"""
    redir, ctx = _auth(request)
    if redir: return redir
    form = await request.form()
    photo = form.get("photo")
    if not photo or not hasattr(photo, 'filename') or not photo.filename:
        return JSONResponse({"error":"请上传图片"}, 400)
    img_bytes = await photo.read()
    if len(img_bytes) < 100:
        return JSONResponse({"error":"图片文件太小或损坏"}, 400)
    import time, hashlib, io
    ts = str(int(time.time() * 1000))
    h = hashlib.md5(img_bytes[:1024]).hexdigest()[:8]
    fname = f"{ts}_{h}.jpg"
    processed_dir = os.path.join(ROOT, "static", "processed")
    os.makedirs(processed_dir, exist_ok=True)
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        # 根据 EXIF 方向标签自动旋转（手机竖拍照片靠这个标签指示方向）
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
        # 如果原图太大则等比缩小，长边限 2048px
        w, h_orig = img.size
        max_dim = 2048
        if max(w, h_orig) > max_dim:
            scale = max_dim / max(w, h_orig)
            img = img.resize((int(w * scale), int(h_orig * scale)), Image.LANCZOS)
        # 转为 RGB（处理 RGBA / P 模式）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        # 压缩保存，目标 ≤ 2MB
        out_path = os.path.join(processed_dir, fname)
        quality = 30
        while quality >= 10:
            buf = io.BytesIO()
            img.save(buf, 'JPEG', quality=quality)
            if buf.tell() <= 2 * 1024 * 1024:
                break
            quality -= 10
        with open(out_path, "wb") as f:
            f.write(buf.getvalue())
        return JSONResponse({
            "processed_image_url": f"/static/processed/{fname}"
        })
    except Exception as e:
        return JSONResponse({"error":f"图片处理失败：{e}"}, 500)


@app.post("/mistake/save")
async def mistake_save(request: Request):
    """Save selected questions as clean text files + save to DB for 错题本"""
    redir, ctx = _auth(request)
    if redir: return redir
    form = await request.form()
    questions_json = form.get("questions", "[]")
    questions = json.loads(questions_json)
    subject = form.get("subject", "math")
    if not questions:
        return JSONResponse({"error": "请选择至少一道题"}, 400)

    pf = ctx["profile"]
    grade = pf.get("grade_level", "grade_4")
    curriculum = pf.get("curriculum_version", "人教版")
    conn = ctx.get("conn")

    # Auto-add subject to profile if needed
    n = ctx["student"]
    subs = _users[n].get("subjects", ["math"])
    if subject in SUBJECT_NAMES and subject not in subs:
        subs.append(subject)
        _users[n]["subjects"] = subs
        try:
            d = os.path.join(_DATA_ROOT, "user_data", n)
            json.dump(_users[n], open(os.path.join(d, "profile.json"), "w"), ensure_ascii=False, indent=2)
        except: pass

    # Save to text files
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved", subject)
    os.makedirs(base_dir, exist_ok=True)
    timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.txt"
    filepath = os.path.join(base_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        for i, q in enumerate(questions):
            idx = q.get("question_index", i + 1)
            text = q.get("question_text", "").strip()
            f.write(f"{idx}. {text}\n\n")

    # Also save to DB for 错题本
    saved_count = 0
    if conn:
        from db import insert_mistake
        for q in questions:
            text = q.get("question_text", "").strip()
            if text:
                insert_mistake(conn,
                    subject=subject, original_problem=text,
                    wrong_answer="", correct_answer="",
                    knowledge_point="OCR录入", error_type="thinking_error",
                    error_analysis="OCR拍照录入，待诊断",
                    pool_status="active", grade_level=grade, curriculum_ver=curriculum)
                saved_count += 1

    return JSONResponse({"count": len(questions), "saved_to_db": saved_count, "folder": f"saved/{subject}/", "file": filename})


@app.post("/mistake/save-regions")
async def mistake_save_regions(request: Request):
    """Save cropped question regions from processed image"""
    redir, ctx = _auth(request)
    if redir: return redir
    form = await request.form()
    image_path = form.get("image_path", "")
    regions_json = form.get("regions", "[]")
    regions = json.loads(regions_json)
    subject = form.get("subject", "math")
    if not regions:
        return JSONResponse({"error":"请选择至少一个区域"}, 400)

    pf = ctx["profile"]
    grade = pf.get("grade_level", "grade_4")
    curriculum = pf.get("curriculum_version", "人教版")
    conn = ctx.get("conn")

    # Auto-add subject
    n = ctx["student"]
    subs = _users[n].get("subjects", ["math"])
    if subject in SUBJECT_NAMES and subject not in subs:
        subs.append(subject)
        _users[n]["subjects"] = subs
        try:
            d = os.path.join(_DATA_ROOT, "user_data", n)
            json.dump(_users[n], open(os.path.join(d, "profile.json"), "w"), ensure_ascii=False, indent=2)
        except: pass

    # Read processed image
    full_path = os.path.join(ROOT, image_path.lstrip("/"))
    if not os.path.exists(full_path):
        return JSONResponse({"error":"处理图片已过期，请重新拍照"}, 400)

    try:
        from PIL import Image
        img = Image.open(full_path)
        w, h = img.size
    except Exception:
        return JSONResponse({"error":"无法打开处理图片"}, 400)

    # Crop, analyze (handwriting + OCR), erase, save each region
    import time as _tm, hashlib as _hl
    from image_utils import erase_handwriting, enhance_image
    from ai import analyze_crop
    crop_dir = os.path.join(ROOT, "saved", subject)
    os.makedirs(crop_dir, exist_ok=True)

    grade_label = {"grade_1":"一年级","grade_2":"二年级","grade_3":"三年级","grade_4":"四年级",
                   "grade_5":"五年级","grade_6":"六年级","grade_7":"初一","grade_8":"初二","grade_9":"初三"}

    saved = 0
    for r in regions:
        x1 = max(0, int(r["x1"] * w))
        y1 = max(0, int(r["y1"] * h))
        x2 = min(w, int(r["x2"] * w))
        y2 = min(h, int(r["y2"] * h))
        if x2 <= x1 or y2 <= y1:
            continue
        cropped = img.crop((x1, y1, x2, y2))
        import io
        buf = io.BytesIO()
        cropped.save(buf, "JPEG", quality=30)
        orig_bytes = buf.getvalue()

        ts = str(int(_tm.time() * 1000))
        crop_name = f"crop_{ts}_{saved}.jpg"
        crop_path = os.path.join(crop_dir, crop_name)
        with open(crop_path, "wb") as f:
            f.write(orig_bytes)

        # 一次 Vision API 调用：手写识别 + OCR + 内容类型 + 学科识别
        analysis = {"handwriting_regions": [], "ocr_text": "", "content_type": "pure_text", "detected_subject": ""}
        try:
            gl = grade_label.get(grade, "")
            analysis = analyze_crop(orig_bytes, subject, gl)
        except Exception as e:
            import traceback
            print(f"[save-regions] Vision API 失败: {e}")
            traceback.print_exc()

        # 学科自动识别：Vision API 优先，启发式规则降级
        detected = analysis.get("detected_subject", "")
        valid_subjects = {"math", "english", "chinese"}
        if detected not in valid_subjects:
            from ai import _guess_subject
            detected = _guess_subject(analysis.get("ocr_text", ""))
        if detected in valid_subjects and detected != subject:
            print(f"[save-regions] 学科自动纠正: {subject} -> {detected}")
            # 迁移已保存的 crop 文件到新学科目录
            new_crop_dir = os.path.join(ROOT, "saved", detected)
            os.makedirs(new_crop_dir, exist_ok=True)
            new_crop_path = os.path.join(new_crop_dir, crop_name)
            os.rename(crop_path, new_crop_path)
            crop_path = new_crop_path
            crop_dir = new_crop_dir
            subject = detected
            # 自动创建对应学科错题本
            subs = _users[n].get("subjects", ["math"])
            if subject not in subs:
                subs.append(subject)
                _users[n]["subjects"] = subs
                try:
                    d = os.path.join(_DATA_ROOT, "user_data", n)
                    json.dump(_users[n], open(os.path.join(d, "profile.json"), "w"), ensure_ascii=False, indent=2)
                    db.init_db(n)
                except Exception:
                    pass

        # 擦除手写 + 增强 → 清洁版
        hw_regions = analysis.get("handwriting_regions", [])
        try:
            if hw_regions:
                clean_bytes = erase_handwriting(orig_bytes, hw_regions)
            else:
                clean_bytes = orig_bytes
        except Exception:
            clean_bytes = orig_bytes
        clean_bytes = enhance_image(clean_bytes)

        clean_name = f"clean_{ts}_{saved}.jpg"
        clean_path = os.path.join(crop_dir, clean_name)
        with open(clean_path, "wb") as f:
            f.write(clean_bytes)

        ocr_text = analysis.get("ocr_text", "")
        content_type = analysis.get("content_type", "pure_text")
        crop_rel = f"saved/{subject}/{crop_name}"

        # 根据内容类型决定 original_problem 存什么
        if content_type == "pure_text" and ocr_text:
            op = ocr_text
        else:
            op = f"IMAGE:saved/{subject}/{clean_name}"

        qn = r.get("question_number", "")
        label = r.get("label", "")
        label_str = f" ({label})" if label else ""
        if conn:
            from db import insert_mistake
            insert_mistake(conn,
                subject=subject,
                original_problem=op,
                wrong_answer="", correct_answer="",
                knowledge_point="图片录入", error_type="thinking_error",
                error_analysis=f"题号{qn}{label_str}，图片拍照录入，待诊断",
                pool_status="active", grade_level=grade, curriculum_ver=curriculum,
                ocr_text=ocr_text or None,
                crop_image_path=crop_rel)
        saved += 1

    return JSONResponse({"count": saved})


@app.post("/mistake/edit/{mistake_id}")
async def mistake_edit(request: Request, mistake_id: int):
    """编辑错题文字"""
    redir, ctx = _auth(request)
    if redir: return redir
    conn = ctx.get("conn")
    if not conn: return JSONResponse({"error":"数据库未连接"}, 500)
    try:
        body = await request.json()
    except Exception:
        body = {}
    updates = {}
    for field in ["ocr_text", "knowledge_point", "error_type", "error_analysis", "correct_answer"]:
        val = body.get(field)
        if val is not None and isinstance(val, str):
            updates[field] = val.strip()
    if not updates:
        return JSONResponse({"error":"没有要更新的字段"}, 400)
    from db import update_mistake
    update_mistake(conn, mistake_id, **updates)
    return JSONResponse({"ok": True})


@app.post("/mistake/delete/{mistake_id}")
async def mistake_delete(request: Request, mistake_id: int):
    """删除错题 + 清理关联图片"""
    redir, ctx = _auth(request)
    if redir: return redir
    conn = ctx.get("conn")
    if not conn: return JSONResponse({"error":"数据库未连接"}, 500)
    from db import delete_mistake, get_figures_for_mistake
    # 先收集图片路径
    figures = get_figures_for_mistake(conn, mistake_id) if conn else []
    m = delete_mistake(conn, mistake_id)
    if m:
        for fpath in [m.get("crop_image_path"), m.get("original_problem")]:
            if fpath and fpath.startswith("IMAGE:"):
                path = os.path.join(ROOT, fpath[6:])
                if os.path.exists(path): os.remove(path)
        for fig in figures:
            fpath = fig.get("image_path", "")
            if fpath:
                path = os.path.join(ROOT, fpath)
                if os.path.exists(path): os.remove(path)
    return JSONResponse({"ok": True})


@app.post("/mistake/crop-figure/{mistake_id}")
async def mistake_crop_figure(request: Request, mistake_id: int):
    """从原图裁切保留图案（示意图/几何图等）"""
    redir, ctx = _auth(request)
    if redir: return redir
    conn = ctx.get("conn")
    if not conn: return JSONResponse({"error":"数据库未连接"}, 500)
    from db import get_mistake, insert_figure
    m = get_mistake(conn, mistake_id)
    if not m: return JSONResponse({"error":"错题不存在"}, 404)
    crop_path = m.get("crop_image_path")
    if not crop_path:
        return JSONResponse({"error":"该错题没有原图"}, 400)
    full = os.path.join(ROOT, crop_path)
    if not os.path.exists(full):
        return JSONResponse({"error":"原图文件已过期"}, 400)
    form = await request.form()
    x1 = float(form.get("x1", 0))
    y1 = float(form.get("y1", 0))
    x2 = float(form.get("x2", 0))
    y2 = float(form.get("y2", 0))
    if x2 <= x1 or y2 <= y1:
        return JSONResponse({"error":"无效的框选区域"}, 400)
    try:
        from PIL import Image
        img = Image.open(full)
        w, h = img.size
        cropped = img.crop((int(x1*w), int(y1*h), int(x2*w), int(y2*h)))
        import time, io
        ts = str(int(time.time() * 1000))
        fig_dir = os.path.join(ROOT, "saved", m["subject"])
        os.makedirs(fig_dir, exist_ok=True)
        fig_name = f"fig_{mistake_id}_{ts}.jpg"
        fig_path = os.path.join(fig_dir, fig_name)
        cropped.save(fig_path, "JPEG", quality=30)
    except Exception as e:
        return JSONResponse({"error":f"图片裁切失败：{e}"}, 500)
    label = form.get("label", "").strip() or f"图{ts[-4:]}"
    fig_id = insert_figure(conn, mistake_id=mistake_id,
                           image_path=f"saved/{m['subject']}/{fig_name}", label=label)
    return JSONResponse({"ok": True, "figure_id": fig_id, "label": label,
                         "image_path": f"saved/{m['subject']}/{fig_name}", "image_url": f"/saved/{m['subject']}/{fig_name}"})


@app.post("/mistake/delete-figure/{figure_id}")
async def mistake_delete_figure(request: Request, figure_id: int):
    """删除单个子图"""
    redir, ctx = _auth(request)
    if redir: return redir
    conn = ctx.get("conn")
    from db import delete_figure
    fig = delete_figure(conn, figure_id)
    if fig:
        fpath = fig.get("image_path", "")
        if fpath:
            path = os.path.join(ROOT, fpath)
            if os.path.exists(path): os.remove(path)
    return JSONResponse({"ok": True})


@app.get("/mistake/export")
def mistake_export(request: Request):
    """导出选中错题：?ids=1,2,3&download=1 返回PDF文件，否则返回HTML预览"""
    redir, ctx = _auth(request)
    if redir: return redir
    conn = ctx.get("conn")
    if not conn: return HTMLResponse("数据库未连接", 500)
    ids_param = request.query_params.get("ids", "")
    if not ids_param:
        return HTMLResponse("未选择错题", 400)
    ids = [int(x) for x in ids_param.split(",") if x.strip().isdigit()]
    if not ids:
        return HTMLResponse("无效的ID", 400)
    want_download = request.query_params.get("download") == "1"

    from db import get_mistake, get_figures_for_mistake
    import base64 as _b64
    cards = ""
    for mid in ids:
        m = get_mistake(conn, mid)
        if not m: continue
        text = (m.get("ocr_text") or m.get("original_problem") or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        if text.startswith("IMAGE:"):
            img_path = os.path.join(ROOT, text[6:])
            if os.path.exists(img_path):
                with open(img_path, "rb") as f:
                    img_b64 = _b64.b64encode(f.read()).decode()
                ext = os.path.splitext(img_path)[1].lower().lstrip(".")
                mime = "image/jpeg" if ext in ("jpg","jpeg") else "image/png"
                text = f'<img src="data:{mime};base64,{img_b64}" style="max-width:100%;border-radius:8px;margin:8px 0">'
        kp = m.get("knowledge_point","")
        dt = (m.get("created_at") or "")[:10]
        figs = get_figures_for_mistake(conn, mid)
        figs_html = ""
        for i, f in enumerate(figs):
            fpath = os.path.join(ROOT, f["image_path"])
            if os.path.exists(fpath):
                with open(fpath, "rb") as ff:
                    f_b64 = _b64.b64encode(ff.read()).decode()
                figs_html += f'<div style="text-align:center;margin:12px 0;"><img src="data:image/jpeg;base64,{f_b64}" style="max-width:100%;border-radius:8px"><div style="font-size:11px;color:#999;margin-top:4px;">{f.get("label","") or f"图{i+1}"}</div></div>'
        cards += f'''<div class="exp-card">
  <div class="exp-meta">{kp} · {dt}</div>
  <div class="exp-text">{text}</div>
  {figs_html}
</div>'''

    if want_download:
        try:
            download_html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>错题导出</title>
<style>
@page{{size:A4;margin:15mm}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:"WenQuanYi Micro Hei","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;font-size:14px;line-height:1.8;color:#222;background:#fff;max-width:800px;margin:0 auto;padding:20px}}
.exp-card{{margin-bottom:20px;padding-bottom:18px;border-bottom:1px dashed #ddd;page-break-inside:avoid}}
.exp-meta{{font-size:12px;color:#888;margin-bottom:8px}}
.exp-text{{white-space:pre-wrap;word-break:break-word}}
h1{{text-align:center;font-size:20px;margin-bottom:24px;color:#333}}
@media print{{
  body{{padding:15px;font-size:14px}}
  .exp-card{{page-break-inside:avoid;margin-bottom:18px}}
  h1{{font-size:18px}}
}}
</style></head><body><h1>错题导出</h1>{cards}</body></html>'''
            from weasyprint import HTML as WHTML
            pdf_bytes = WHTML(string=download_html).write_pdf()
            from fastapi.responses import Response
            return Response(content=pdf_bytes, media_type="application/pdf",
                          headers={"Content-Disposition": "attachment; filename*=UTF-8''%E9%94%99%E9%A2%98%E5%AF%BC%E5%87%BA.pdf"})
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return HTMLResponse(f"<pre>PDF生成失败: {e}\n\n{tb}</pre>", 500)

    # HTML 预览模式
    preview_html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>错题导出打印</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:"PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;font-size:15px;line-height:1.8;color:#222;background:#fff;padding:20px;max-width:800px;margin:0 auto}}
.exp-card{{margin-bottom:24px;padding-bottom:20px;border-bottom:1px dashed #ddd}}
.exp-meta{{font-size:12px;color:#888;margin-bottom:8px}}
.exp-text{{white-space:pre-wrap;word-break:break-word}}
h1{{text-align:center;font-size:20px;margin-bottom:12px;color:#333}}
.exp-actions{{display:flex;justify-content:center;gap:10px;margin-bottom:24px;flex-wrap:wrap}}
.exp-btn{{padding:8px 18px;border-radius:20px;font-size:13px;cursor:pointer;font-family:inherit;border:none;font-weight:600}}
.exp-btn-print{{background:#5B7FFF;color:#fff}}
.exp-btn-share{{background:#f0f0f0;color:#333}}
.exp-btn-dl{{background:#f0f0f0;color:#333}}
@media print{{body{{padding:15px;font-size:14px}}.exp-card{{page-break-inside:avoid;margin-bottom:18px}}h1{{font-size:18px}}.exp-actions{{display:none!important}}}}
</style></head><body>
<h1>错题导出</h1>
<div class="exp-actions">
  <button class="exp-btn exp-btn-print" onclick="window.print()">打印 / 另存PDF</button>
  <button class="exp-btn exp-btn-share" onclick="downloadPDF()">下载PDF</button>
</div>
{cards}
<script>
function downloadPDF(){{window.location.search=window.location.search+'&download=1'}}
</script></body></html>'''
    return HTMLResponse(preview_html)


@app.post("/mistake/diagnose")
async def mistake_diagnose(request: Request):
    """Stage 4: Diagnose selected questions one by one, save to DB, generate variants"""
    redir, ctx = _auth(request)
    if redir: return redir
    form = await request.form()
    questions_json = form.get("questions", "[]")
    questions = json.loads(questions_json)
    if not questions:
        return JSONResponse({"error":"请选择题目"}, 400)
    pf = ctx["profile"]
    grade = pf.get("grade_level", "grade_4")
    curriculum = pf.get("curriculum_version", "人教版")
    subject = form.get("subject", "math")
    conn = ctx["conn"]
    from ai import diagnose_mistake, generate_variants
    from db import insert_mistake, insert_variant
    results = []
    for q in questions:
        problem = q.get("question_text", "").strip()
        wrong = q.get("student_answer", "") or ""
        if not problem:
            continue
        diag = diagnose_mistake(problem, wrong, grade, curriculum)
        mid = insert_mistake(conn, subject=subject, original_problem=problem,
            wrong_answer=wrong, correct_answer=diag.get("correct_answer",""),
            knowledge_point=diag["knowledge_point"], error_type=diag["error_type"],
            error_analysis=diag["error_analysis"], pool_status="active",
            grade_level=grade, curriculum_ver=curriculum)
        from knowledge_base import get_few_shot_examples
        examples = get_few_shot_examples(conn, diag["knowledge_point"], grade, subject)
        variants = generate_variants(diag["knowledge_point"], diag["error_type"],
            diag["error_analysis"], grade, curriculum, "same", 3, False, examples)
        diffs = ["easy","same","slightly_harder"]
        saved = []
        for i, v in enumerate(variants):
            vid = insert_variant(conn, mistake_id=mid, problem_text=v["problem"],
                correct_answer=v["correct_answer"],
                difficulty=diffs[i] if i < len(diffs) else "same")
            saved.append({"id":vid, "problem":v["problem"], "difficulty":diffs[i] if i<len(diffs) else"same"})
        results.append({"knowledge_point":diag["knowledge_point"],
            "error_type":diag["error_type"], "error_analysis":diag["error_analysis"],
            "correct_answer":diag["correct_answer"], "variants":saved})
    return JSONResponse({"results": results})

@app.post("/mistake/new")
async def mistake_post(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    form=await request.form(); problem=form.get("problem","").strip(); wrong=form.get("wrong_answer","").strip()
    if not problem: return JSONResponse({"error":"题目不能为空"},400)
    pf=ctx["profile"]; grade=pf.get("grade_level","grade_4"); curriculum=pf.get("curriculum_version","人教版")
    subject=form.get("subject","math")
    from ai import diagnose_mistake, generate_variants
    diag=diagnose_mistake(problem,wrong,grade,curriculum)
    conn=ctx["conn"]
    from db import insert_mistake, insert_variant
    mid=insert_mistake(conn,subject=subject,original_problem=problem,wrong_answer=wrong,correct_answer=diag.get("correct_answer",""),knowledge_point=diag["knowledge_point"],error_type=diag["error_type"],error_analysis=diag["error_analysis"],pool_status="active",grade_level=grade,curriculum_ver=curriculum)
    from knowledge_base import get_few_shot_examples
    kp_examples=get_few_shot_examples(conn,diag["knowledge_point"],grade,subject)
    variants=generate_variants(diag["knowledge_point"],diag["error_type"],diag["error_analysis"],grade,curriculum,"easy",3,False,kp_examples)
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
    return HTMLResponse(_pg(body,"版图","map"))

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
    return HTMLResponse(_pg(body,"报告","report"))

@app.get("/mistakes", response_class=HTMLResponse)
async def mistakes_list(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    subject = request.query_params.get("subject", "")
    subject_label = SUBJECT_NAMES.get(subject, subject)
    date_from = request.query_params.get("date_from", "")
    date_to = request.query_params.get("date_to", "")
    page = int(request.query_params.get("page", "1"))
    per_page = 5
    conn=ctx.get("conn"); cards=""; has_any=False
    total = 0; total_pages = 0; all_filtered_ids = []
    if conn:
        from db import list_mistakes, count_mistakes, get_filtered_ids, get_figures_for_mistake
        total = count_mistakes(conn, subject=subject if subject else None, date_from=date_from or None, date_to=date_to or None)
        total_pages = max(1, (total + per_page - 1) // per_page)
        offset = (page - 1) * per_page
        all_filtered_ids = get_filtered_ids(conn, subject=subject if subject else None, date_from=date_from or None, date_to=date_to or None)
        ms=list_mistakes(conn, subject=subject if subject else None, date_from=date_from or None, date_to=date_to or None, limit=per_page, offset=offset)
        for m in ms:
            has_any=True
            mid=m["id"]
            crop_img=m.get("crop_image_path") or ""
            dt=m["created_at"][:10] if m.get("created_at") else ""

            figs=get_figures_for_mistake(conn, mid)
            figs_html=""
            for fi in figs:
                figs_html+=f'<div class="fig-item"><img src="/{fi["image_path"]}" class="fig-thumb"><span class="fig-label">{fi.get("label","") or "图"}</span><button class="fig-del" onclick="delFig({fi["id"]},this)">✕</button></div>'
            text_value = m.get("ocr_text") or ""

            cards+=f'''<div class="mcrd" id="card-{mid}" data-crop="{crop_img}">
  <div class="mcrd-top">
    <input type="checkbox" class="mcrd-check" data-id="{mid}" onchange="onChk()">
    {f'<a class="fig-link" onclick="event.preventDefault();openFigCrop({mid})">截图案</a>' if crop_img else ''}
    <span class="mcrd-date">{dt}</span>
  </div>
  <textarea class="mcrd-txa" id="txt-{mid}" oninput="onTxtChange({mid})">{text_value}</textarea>
  <div class="mcrd-acts" id="acts-{mid}" style="display:none;">
    <button class="mbtn mbtn-save" onclick="saveTxt({mid})">保存</button>
    <span class="mbtn-hint" id="hint-{mid}">已修改</span>
  </div>
  {f'<div class="mcrd-figs" id="figs-{mid}">{figs_html}</div>' if figs_html else f'<div class="mcrd-figs" id="figs-{mid}"></div>'}
  <div class="mcrd-footer">
    <button class="mbtn mbtn-del" onclick="delMis({mid})">删除</button>
  </div>
</div>'''

    # 日期筛选栏
    date_filter = f'''<div class="date-filter">
  <input type="date" id="dateFrom" value="{date_from}" onchange="applyDateFilter()">
  <span class="date-sep">至</span>
  <input type="date" id="dateTo" value="{date_to}" onchange="applyDateFilter()">
  {f'<button class="date-clear" onclick="clearDateFilter()">清除</button>' if date_from or date_to else ''}
</div>'''

    # 翻页导航
    pager = ""
    if total_pages > 1:
        pager = f'''<div class="pager">
  <button class="pager-btn" onclick="goPage({page-1})" {'disabled' if page<=1 else ''}>上一页</button>
  <span class="pager-info">{page}/{total_pages}（共{total}道）</span>
  <button class="pager-btn" onclick="goPage({page+1})" {'disabled' if page>=total_pages else ''}>下一页</button>
</div>'''

    all_ids_json = json.dumps(all_filtered_ids)

    batch_bar=f'''<div class="batch-bar" id="batchBar" style="display:none">
  <div class="batch-left">
    <label class="batch-selall"><input type="checkbox" id="selectAll" onchange="toggleAll(this)"> 全选</label>
    <span class="batch-count" id="batchCount">已选 0 道</span>
  </div>
  <div class="batch-right">
    <button class="mbtn mbtn-exp" onclick="exportSel()">导出PDF</button>
    <button class="mbtn mbtn-del" onclick="delSel()">批量删除</button>
  </div>
</div>'''

    title=f"{subject_label}错题本" if subject else "错题回顾"
    js=_JS_MISTAKES
    body=f'<div class="pg"><div class="nb"><a href="/home">← 返回</a><span class="tt">{title}</span></div>{date_filter}{pager}{cards or "<div style=\"color:var(--ts);font-size:13px;padding:20px;text-align:center;\">暂无错题</div>"}{pager}{batch_bar}<span id="allFilteredIds" data-ids="{all_ids_json}" style="display:none"></span></div>{js}'
    return HTMLResponse(_pg(body,"回顾"))

# ─── 考点通 ────────────────────────────────────

@app.get("/exam-points", response_class=HTMLResponse)
async def exam_points_page(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    conn = ctx.get("conn")
    items = ""
    if conn:
        from db import get_all_masteries
        subjects = ctx.get("profile", {}).get("subjects", ["math"])
        for subj in subjects:
            ms = get_all_masteries(conn, subj)
            if ms:
                items += f'<div class="section-title" style="margin-top:8px;">{SUBJECT_NAMES.get(subj, subj)}</div>'
                for m in ms:
                    sc = m["mastery_score"]
                    c = "#3D5FD9" if sc >= 0.7 else ("#D9821A" if sc >= 0.4 else "#E04050")
                    tc = "tag-m" if m["pool_status"] == "dormant" else ("tag-w" if m["pool_status"] == "active" else "tag-i")
                    st = "熟练" if m["pool_status"] == "dormant" else ("攻克中" if m["pool_status"] == "active" else "需加强")
                    kp_encoded = quote(m["knowledge_point"])
                    items += f'''<a href="/exam-point/{kp_encoded}" class="kp-card">
                      <span class="kp-name">{m["knowledge_point"]}</span>
                      <span class="kp-score" style="color:{c};">{int(sc*100)}%</span>
                      <span class="tag {tc}">{st}</span>
                    </a>'''
    body = f'<div class="pg"><div class="section-title" style="font-size:20px;font-weight:700;color:var(--t);margin-bottom:16px;">考点通</div>{items or "<div style=\'color:var(--ts);font-size:13px;\'>暂无考点数据，先录入错题吧</div>"}</div>'
    return HTMLResponse(_pg(body, "考点通", "exam_points"))

@app.get("/exam-point/{kp}", response_class=HTMLResponse)
async def exam_point_detail(request: Request, kp: str):
    redir, ctx = _auth(request)
    if redir: return redir
    kp = unquote(kp)
    conn = ctx.get("conn")
    mistakes_html = ""
    if conn:
        from db import list_mistakes
        ms = list_mistakes(conn, knowledge_point=kp, limit=50)
        for m in ms:
            em = {"knowledge_gap": "知识盲区", "thinking_error": "思路错误", "careless": "粗心"}
            ec = "tag-kg" if m['error_type'] == 'knowledge_gap' else ("tag-te" if m['error_type'] == 'thinking_error' else "tag-cl")
            op = m["original_problem"]
            if op.startswith("IMAGE:"):
                mistakes_html += f'''<div class="crd">
                  <span class="tag" style="background:var(--c);color:var(--tw);">图片题</span>
                  <img src="/{op[6:]}" style="max-width:100%;border-radius:10px;max-height:200px;margin-top:8px;" alt="错题图片">
                </div>'''
            else:
                mistakes_html += f'''<div class="crd">
                  <span class="tag {ec}">{em.get(m["error_type"], "")}</span>
                  <div style="font-size:14px;color:var(--t);margin-top:8px;">{op[:100]}</div>
                </div>'''
    body = f"""<div class="pg">
    <div class="nb"><a href="/exam-points">← 返回</a><span class="tt">{kp}</span></div>
    {mistakes_html or "<div style='color:var(--ts);font-size:13px;padding:12px 0;'>暂无记录</div>"}
    <div style="display:flex;gap:12px;margin-top:16px;">
      <button class="btn btn-p" style="flex:1;" onclick="generateVariants()">举一反三</button>
      <button class="btn" style="flex:1;background:var(--c);color:var(--t);" onclick="window.print()">打印</button>
    </div>
    <div id="variants-result"></div>
    </div>
    <script>
    var currentKp = '{kp}';
    async function generateVariants() {{
      var r = document.getElementById('variants-result');
      r.innerHTML = '<div style="text-align:center;padding:20px;"><div class="spinner"></div><div style="color:var(--ts)">AI 正在生成变式题...</div></div>';
      var d = new FormData(); d.append('knowledge_point', currentKp);
      try {{
        var resp = await fetch('/generate-variants', {{method:'POST', body:d}});
        var j = await resp.json();
        if (j.error) {{ r.innerHTML = '<div class="err-msg">'+escHtml(j.error)+'</div>'; return; }}
        var html = '';
        j.variants.forEach(function(v, i) {{
          html += '<div class="crd" style="margin-top:12px;"><div style="font-size:11px;color:var(--ts);">变式题 '+(i+1)+'</div><div style="font-size:14px;color:var(--t);line-height:1.8;margin:8px 0;">'+escHtml(v.problem)+'</div><div style="font-size:12px;color:var(--tw);">答案：'+escHtml(v.correct_answer)+'</div></div>';
        }});
        r.innerHTML = html;
      }} catch(e) {{ r.innerHTML = '<div class="err-msg">生成失败，请重试</div>'; }}
    }}
    function escHtml(s) {{ var d = document.createElement('div'); d.textContent = s||''; return d.innerHTML; }}
    </script>"""
    return HTMLResponse(_pg(body, kp))

@app.post("/generate-variants")
async def generate_variants_post(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    form = await request.form()
    kp = form.get("knowledge_point", "")
    if not kp: return JSONResponse({"error": "知识点不能为空"}, 400)
    pf = ctx.get("profile", {})
    grade = pf.get("grade_level", "grade_4")
    curriculum = pf.get("curriculum_version", "人教版")
    from ai import generate_variants
    from knowledge_base import get_few_shot_examples
    examples = get_few_shot_examples(conn, kp, grade, "math") if conn else []
    variants = generate_variants(kp, "thinking_error", "", grade, curriculum, "same", 3, False, examples)
    return JSONResponse({"variants": variants})

# ─── 我的 ──────────────────────────────────────

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    n = ctx["student"]
    pf = ctx.get("profile", {})
    grade = GRADE_LABELS.get(pf.get("grade_level", "grade_4"), "小四")
    subjects = pf.get("subjects", ["math"])
    subj_labels = [SUBJECT_NAMES.get(s, s) for s in subjects]
    body = f"""<div class="pg">
    <div class="profile-header">
      <div class="avatar">{n[0].upper()}</div>
      <div class="profile-name">{n}</div>
      <div class="profile-grade">{grade}</div>
    </div>
    <div class="crd">
      <div class="label">学习科目</div>
      <div class="chip-row">{''.join(f'<span class="chip sel">{s}</span>' for s in subj_labels)}</div>
    </div>
    <div class="crd">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:14px;color:var(--t);">学习记录</span>
        <span style="font-size:12px;color:var(--tw);">开发中</span>
      </div>
    </div>
    <div class="crd">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:14px;color:var(--t);">站内消息</span>
        <span style="font-size:12px;color:var(--tw);">开发中</span>
      </div>
    </div>
    <div class="crd">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:14px;color:var(--t);">设置</span>
        <span style="font-size:12px;color:var(--tw);">开发中</span>
      </div>
    </div>
    <a href="/logout" class="btn" style="display:block;width:100%;height:50px;background:var(--rb);color:var(--r);border:none;border-radius:13px;font-size:15px;font-weight:600;text-align:center;line-height:50px;text-decoration:none;margin-top:16px;">退出登录</a>
    </div>"""
    return HTMLResponse(_pg(body, "我的", "profile"))

# ─── 辅助 ──────────────────────────────────────

@app.post("/update-grade")
async def update_grade(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    form = await request.form()
    grade = form.get("grade", "")
    valid_grades = [k for k, v in GRADE_OPTIONS]
    if grade in valid_grades:
        n = ctx["student"]
        _users[n]["grade_level"] = grade
        try:
            d = os.path.join(_DATA_ROOT, "user_data", n)
            pf = os.path.join(d, "profile.json")
            json.dump(_users[n], open(pf, "w"), ensure_ascii=False, indent=2)
        except: pass
    return JSONResponse({"ok": True})

@app.post("/add-subject")
async def add_subject(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    form = await request.form()
    subj = form.get("subject", "").strip()
    if subj in SUBJECT_NAMES:
        n = ctx["student"]
        subs = _users[n].get("subjects", ["math"])
        if subj not in subs:
            subs.append(subj)
            _users[n]["subjects"] = subs
            try:
                d = os.path.join(_DATA_ROOT, "user_data", n)
                json.dump(_users[n], open(os.path.join(d, "profile.json"), "w"), ensure_ascii=False, indent=2)
            except: pass
    return JSONResponse({"ok": True})

@app.post("/remove-subject")
async def remove_subject(request: Request):
    redir, ctx = _auth(request)
    if redir: return redir
    form = await request.form()
    subj = form.get("subject", "").strip()
    n = ctx["student"]
    subs = _users[n].get("subjects", ["math"])
    if subj in subs and len(subs) > 1:
        subs.remove(subj)
        _users[n]["subjects"] = subs
        try:
            d = os.path.join(_DATA_ROOT, "user_data", n)
            json.dump(_users[n], open(os.path.join(d, "profile.json"), "w"), ensure_ascii=False, indent=2)
        except: pass
    return JSONResponse({"ok": True})

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
.bn a{display:flex;flex-direction:column;align-items:center;font-size:10px;color:var(--tw);text-decoration:none;gap:4px;padding:4px 0}.bn a svg{width:24px;height:24px}.bn a.on{color:var(--b)}
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
.chip{padding:8px 14px;background:var(--c);border-radius:8px;font-size:13px;color:var(--t);cursor:pointer;border:2px solid transparent}.chip.sel{background:var(--bb);border-color:var(--b);color:var(--b);font-weight:600}
.grade-select{font-size:13px;background:var(--w);border:1px solid var(--br);border-radius:8px;padding:4px 8px;color:var(--t);font-family:inherit;outline:none}
.grade-select:focus{border-color:var(--b)}
.record-card{display:block;background:linear-gradient(135deg,var(--bb),rgba(91,127,255,.08));border:1.5px solid rgba(91,127,255,.12);border-radius:18px;padding:24px;text-align:center;text-decoration:none;margin-bottom:24px;transition:transform .15s}
.record-card:active{transform:scale(.98)}
.record-icon{font-size:36px;margin-bottom:8px}
.record-label{font-size:18px;font-weight:700;color:var(--b);margin-bottom:4px}
.record-desc{font-size:12px;color:var(--ts)}
.section-title{font-size:14px;font-weight:700;color:var(--t);margin-bottom:12px}
.subject-grid{display:flex;flex-direction:column;gap:8px}
.subject-card{display:flex;justify-content:space-between;align-items:center;background:var(--w);border-radius:14px;padding:16px;text-decoration:none;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.subject-card:active{background:var(--c)}
.subject-name{font-size:15px;font-weight:600;color:var(--t)}
.subject-count{font-size:12px;color:var(--tw);background:var(--c);padding:4px 10px;border-radius:99px}
.profile-header{text-align:center;padding:24px 0}
.avatar{width:64px;height:64px;background:var(--b);color:#FFF;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:700;margin:0 auto 12px}
.profile-name{font-size:20px;font-weight:700;color:var(--t)}
.profile-grade{font-size:13px;color:var(--ts);margin-top:4px}
.kp-card{display:flex;align-items:center;gap:8px;background:var(--w);border-radius:14px;padding:14px 16px;margin-bottom:8px;text-decoration:none;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.kp-name{flex:1;font-size:14px;font-weight:600;color:var(--t)}
.kp-score{font-size:14px;font-weight:700}
.subject-card-row{display:flex;align-items:center;gap:6px}
.subject-card-row .subject-card{flex:1}
.subject-remove{width:32px;height:32px;background:var(--rb);color:var(--r);border:none;border-radius:50%;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.subject-remove:active{opacity:.7}
.subject-add-btn{padding:6px 14px;background:var(--w);border:1.5px dashed var(--br);border-radius:10px;font-size:13px;color:var(--ts);cursor:pointer;font-family:inherit}
.subject-add-btn:active{background:var(--c);border-color:var(--b);color:var(--b)}.qcard{display:flex;gap:12px;background:var(--w);border-radius:14px;padding:14px;margin-bottom:8px;border:2px solid transparent;cursor:pointer;transition:border-color .15s}.qcard-marked{border-color:rgba(255,91,107,.2);background:rgba(255,91,107,.015)}.qcard-left{display:flex;align-items:flex-start;gap:8px;flex-shrink:0}.qcheck{width:20px;height:20px;accent-color:var(--b);cursor:pointer;margin-top:1px}.qcard-idx{font-size:11px;font-weight:700;color:var(--tw);background:var(--c);border-radius:6px;padding:2px 7px;min-width:28px;text-align:center}.qcard-body{flex:1;min-width:0}.qcard-text{font-size:14px;color:var(--t);line-height:1.6;word-break:break-word}.qcard-ans{font-size:12px;color:var(--a);margin-top:6px;background:rgba(255,159,67,.06);padding:4px 8px;border-radius:6px;display:inline-block}.qcard-corr{font-size:11px;color:var(--r);margin-top:4px}.qbadge-wrong{display:inline-block;font-size:10px;font-weight:600;color:#E04050;background:rgba(255,91,107,.08);padding:2px 8px;border-radius:4px;margin-top:6px}.sel-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}.sel-title{font-size:16px;font-weight:700;color:var(--t)}.sel-count{font-size:12px;color:var(--ts);margin-bottom:12px;padding:6px 12px;background:var(--c);border-radius:8px;display:inline-block}.sel-all-btn{padding:6px 14px;border:1.5px solid var(--b);border-radius:20px;background:var(--w);color:var(--b);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}.sel-all-btn:active{background:var(--bb)}.mistake-title{text-align:center;font-size:19px;font-weight:700;color:var(--t);margin:4px 0 20px}.section-label{font-size:15px;font-weight:700;color:var(--t);margin:16px 0 8px}.sub-label{font-size:14px;font-weight:700;color:var(--ts);margin:16px 0 8px}.photo-btns{display:flex;gap:12px;margin-bottom:8px}.photo-btn{flex:1;display:flex;flex-direction:column;align-items:center;gap:6px;padding:20px 12px;border-radius:14px;border:none;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;transition:opacity .15s}.photo-btn:active{opacity:.85}.photo-btn-camera{background:linear-gradient(135deg,#D6F6EB,#C5EDD8);color:#1A7D4E}.photo-btn-gallery{background:linear-gradient(135deg,#E4EFFC,#D0E0F8);color:#3D5FD9}.photo-btn-icon{font-size:28px}.draw-wrap{position:relative;width:100%;user-select:none;-webkit-user-select:none;touch-action:none}.draw-img{display:block;width:100%;height:auto;pointer-events:none}.draw-layer{position:absolute;top:0;left:0;width:100%;height:100%;z-index:2}.selbox{position:absolute;border:2px solid var(--b);background:rgba(91,127,255,0.08);border-radius:4px;z-index:3;pointer-events:auto}.selbox-tmp{border-style:dashed;background:rgba(91,127,255,0.04)}.selbox-del{position:absolute;top:-12px;right:-12px;width:24px;height:24px;background:#E04050;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;cursor:pointer;z-index:5;box-shadow:0 2px 6px rgba(0,0,0,.2)}.shandle{position:absolute;width:16px;height:16px;background:#fff;border:2px solid var(--b);border-radius:3px;z-index:4;pointer-events:auto}.sh-tl{top:-6px;left:-6px;cursor:nw-resize}.sh-tr{top:-6px;right:-6px;cursor:ne-resize}.sh-bl{bottom:-6px;left:-6px;cursor:sw-resize}.sh-br{bottom:-6px;right:-6px;cursor:se-resize}.sel-overlay{position:fixed;top:0;left:0;right:0;bottom:0;z-index:200;background:var(--w);display:flex;flex-direction:column}.sel-topbar{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;flex-shrink:0;border-bottom:1px solid rgba(0,0,0,.06)}.sel-topbar-title{font-size:16px;font-weight:700;color:var(--t)}.sel-close{width:36px;height:36px;border-radius:50%;border:1.5px solid rgba(0,0,0,.12);background:var(--w);color:var(--t);font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;font-family:inherit;line-height:1}.sel-hint{flex-shrink:0}.sel-scroll{flex:1;overflow-y:auto;padding:4px 8px}.sel-bottombar{flex-shrink:0;padding:8px 12px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px;border-top:1px solid rgba(0,0,0,.06)}.sel-bottombar .sel-count{font-size:13px;color:var(--t);background:var(--c);padding:6px 14px;border-radius:20px;margin:0;font-weight:600}.mcrd{background:var(--w);border-radius:14px;padding:14px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.04)}.mcrd-top{display:flex;align-items:center;gap:8px;margin-bottom:10px}.mcrd-check{width:18px;height:18px;accent-color:var(--b);cursor:pointer;flex-shrink:0}.fig-link{font-size:12px;color:var(--b);text-decoration:none;padding:2px 10px;border:1px solid var(--br);border-radius:10px;flex-shrink:0}.mcrd-kp{flex:1;font-size:14px;font-weight:600;color:var(--t)}.mcrd-date{font-size:11px;color:var(--ts)}.mcrd-txa{width:100%;min-height:80px;font-size:14px;line-height:1.7;color:var(--t);border:1.5px solid var(--br);border-radius:10px;padding:10px 12px;resize:vertical;box-sizing:border-box;font-family:inherit;background:var(--w)}.mcrd-txa:focus{outline:none;border-color:var(--b);box-shadow:0 0 0 3px rgba(91,127,255,.08)}.mcrd-acts{display:flex;align-items:center;gap:8px;margin-top:8px}.mbtn{padding:7px 16px;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;border:none;transition:opacity .15s}.mbtn:active{opacity:.8}.mbtn-save{background:var(--b);color:#FFF}.mbtn-del{background:var(--rb);color:var(--r)}.mbtn-exp{background:var(--b);color:#FFF}.mbtn-hint{font-size:12px;color:var(--a);display:none}.mcrd-img-wrap{position:relative;margin-top:10px}.mcrd-img{width:100%;border-radius:10px;cursor:pointer;border:1px solid var(--br)}.mcrd-img-label{text-align:center;font-size:11px;color:var(--ts);margin-top:4px}.mcrd-figs{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px}.fig-item{position:relative;width:80px;text-align:center}.fig-thumb{width:80px;height:80px;object-fit:cover;border-radius:8px;border:1px solid var(--br)}.fig-label{display:block;font-size:10px;color:var(--ts);margin-top:2px}.fig-del{position:absolute;top:-8px;right:-8px;width:20px;height:20px;background:#E04050;color:#fff;border:none;border-radius:50%;font-size:11px;cursor:pointer;display:flex;align-items:center;justify-content:center;line-height:1;padding:0}.mcrd-footer{display:flex;justify-content:flex-end;margin-top:10px;padding-top:10px;border-top:1px solid rgba(0,0,0,.04)}.batch-bar{position:sticky;bottom:0;z-index:100;background:var(--w);border-radius:14px 14px 0 0;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px;box-shadow:0 -2px 12px rgba(0,0,0,.08)}.batch-left{display:flex;align-items:center;gap:10px}.batch-right{display:flex;gap:8px}.batch-selall{font-size:13px;color:var(--t);cursor:pointer;display:flex;align-items:center;gap:4px}.batch-selall input{accent-color:var(--b)}.batch-count{font-size:13px;color:var(--ts);font-weight:600}.fig-overlay{position:fixed;top:0;left:0;right:0;bottom:0;z-index:200;background:var(--w);display:flex;flex-direction:column}.fig-topbar{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;flex-shrink:0;border-bottom:1px solid rgba(0,0,0,.06)}.fig-topbar-title{font-size:16px;font-weight:700;color:var(--t)}.fig-close{width:36px;height:36px;border-radius:50%;border:1.5px solid rgba(0,0,0,.12);background:var(--w);color:var(--t);font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;font-family:inherit;line-height:1}.fig-scroll{flex:1;overflow-y:auto;padding:4px 8px}.fig-bottombar{flex-shrink:0;padding:8px 12px 16px;display:flex;align-items:center;justify-content:space-between;border-top:1px solid rgba(0,0,0,.06)}.fig-draw-wrap{position:relative;width:100%;user-select:none;-webkit-user-select:none;touch-action:none}.fig-draw-img{display:block;width:100%;height:auto;pointer-events:none}.fig-draw-layer{position:absolute;top:0;left:0;width:100%;height:100%;z-index:2}.fig-hint{text-align:center;font-size:12px;color:var(--ts);padding:4px 12px}.date-filter{display:flex;gap:8px;align-items:center;margin-bottom:12px}.date-filter input[type=date]{font-size:13px;padding:6px 8px;border:1px solid var(--br);border-radius:8px;background:var(--w);color:var(--t);font-family:inherit;flex:1}.date-sep{font-size:12px;color:var(--ts);flex-shrink:0}.date-clear{font-size:12px;color:var(--r);background:none;border:none;cursor:pointer;padding:4px 8px}.pager{display:flex;justify-content:center;align-items:center;gap:12px;margin:12px 0}.pager-btn{padding:6px 16px;border:1px solid var(--br);border-radius:20px;background:var(--w);color:var(--t);font-size:13px;cursor:pointer;font-family:inherit}.pager-btn:disabled{opacity:.3;cursor:default}.pager-info{font-size:13px;color:var(--ts)}@media print{.nb,.mcrd-top,.mcrd-acts,.mcrd-footer,.batch-bar,.mcrd-check,.date-filter,.pager{display:none!important}.mcrd{box-shadow:none;border-bottom:1px solid #ccc;border-radius:0;page-break-inside:avoid;margin-bottom:16px;padding:8px 0}.mcrd-txa{border:none;resize:none;min-height:auto;padding:0}}</style>"""

def _pg(body, title="错题Pro", nav=None):
    nh = _nav_bar(nav) if nav else ""
    return f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no"><title>{title} - 错题Pro</title>{CSS}</head><body>{body}{nh}</body></html>'

# ─── 启动 ──────────────────────────────────────

# ─── 管理 ──────────────────────────────────────

@app.post("/admin/seed-knowledge-base")
async def admin_seed_kb(request: Request):
    """Seed the knowledge base for all grades 1-12"""
    from knowledge_base import seed_all_grades
    conn = None
    try:
        from db import get_conn
        conn = get_conn("demo")
        results = seed_all_grades(conn, "math", "人教版")
        return JSONResponse({"ok": True, "results": results})
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)
    finally:
        if conn:
            conn.close()

@app.get("/admin/kb-stats")
async def admin_kb_stats(request: Request):
    """Get knowledge base stats"""
    from knowledge_base import get_kb_stats
    conn = None
    try:
        from db import get_conn
        conn = get_conn("demo")
        stats = get_kb_stats(conn, "math")
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 错题Pro port={port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

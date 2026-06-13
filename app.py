"""错题Pro - Zeabur 入口点"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 初始化测试账号和数据库
def _init():
    import json, hashlib
    from db import init_db
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")
    os.makedirs(data_dir, exist_ok=True)
    # demo 账号
    demo_dir = os.path.join(data_dir, "demo")
    os.makedirs(demo_dir, exist_ok=True)
    pf_path = os.path.join(demo_dir, "profile.json")
    if not os.path.exists(pf_path):
        s = os.urandom(16)
        h = hashlib.pbkdf2_hmac("sha256", b"demo", s, 200000)
        pf = {
            "student_name": "demo", "password_hash": s.hex()+":"+h.hex(),
            "province": "广东省", "city": "广州市", "district": "天河区",
            "grade_level": "grade_4", "curriculum_version": "人教版",
            "subjects": ["math"], "version": "basic"
        }
        json.dump(pf, open(pf_path, "w"), ensure_ascii=False, indent=2)
        init_db("demo")
    # test 账号
    test_dir = os.path.join(data_dir, "test")
    os.makedirs(test_dir, exist_ok=True)
    test_pf = os.path.join(test_dir, "profile.json")
    if not os.path.exists(test_pf):
        s2 = os.urandom(16)
        h2 = hashlib.pbkdf2_hmac("sha256", b"test123", s2, 200000)
        pf2 = {
            "student_name": "test", "password_hash": s2.hex()+":"+h2.hex(),
            "province": "广东省", "city": "广州市", "district": "天河区",
            "grade_level": "grade_4", "curriculum_version": "人教版",
            "subjects": ["math"], "version": "basic"
        }
        json.dump(pf2, open(test_pf, "w"), ensure_ascii=False, indent=2)
        init_db("test")
    print("✅ 测试账号已就绪: demo/demo, test/test123")

_init()

# 启动 Web 应用
from web_app import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 错题Pro 启动于端口 {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

"""错题Pro - 最小化启动"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv; load_dotenv()
from fastapi import FastAPI
app = FastAPI(title="错题Pro")

@app.get("/health")
def health(): return {"ok": True}

@app.get("/")
def root(): return {"ok": True, "msg": "错题Pro v1", "routes": len(app.routes)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)

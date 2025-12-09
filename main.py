from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

from config import settings
from services.proxy_service import proxy_request
from utils.logger import log

# ✅ 关键变化：从 dependencies 模块导入 verify_api_key，而不是在这里定义它
from dependencies import verify_api_key

app = FastAPI(title=settings.API_TITLE, version="2.0.0")

# --- 数据模型 (也可以考虑移到单独的 schemas.py，但放在这里也行) ---
class ProxyRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: Dict[str, str] = {}
    data: Optional[Dict[str, Any]] = None
    json_body: Optional[Dict[str, Any]] = None

# --- 路由 ---

@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy", "service": settings.API_TITLE}

# ✅ 关键变化：dependencies=[Depends(verify_api_key)] 依然保留
# 但 verify_api_key 这个函数本身的代码已经移到了 dependencies.py
@app.post("/v1/proxy", dependencies=[Depends(verify_api_key)])
def proxy_handler(req: ProxyRequest):
    """
    通用代理接口
    """
    try:
        resp = proxy_request(
            url=req.url, 
            method=req.method, 
            headers=req.headers, 
            data=req.data, 
            json=req.json_body
        )
        
        return JSONResponse(content={
            "status": resp.status_code,
            "url": resp.url,
            "headers": dict(resp.headers),
            "cookies": resp.cookies.get_dict(),
            "text": resp.text
        })
    except Exception as e:
        log.error(f"API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=False)

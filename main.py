import time
from datetime import datetime
from urllib.parse import urlparse
from collections import deque

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from bypass import TurnstileBypasser
from browser_pool import browser_pool
from cf_session_manager import cf_sessions
from config import EXAMPLE_ENV, get_settings
from models import (
    BypassRequest,
    BypassResult,
    DashboardState,
    ErrorResponse,
    HealthResponse,
    ProxyRequest,
    ProxyResponse,
)
from rate_limiter import rate_limiter
from security import require_token, validate_target

settings = get_settings()
app = FastAPI(title="Cloudflare Proxy Service", version="2.0")
templates = Jinja2Templates(directory="templates")
startup_time = time.time()
# logs = []
logs = deque(maxlen=200)

@app.on_event("startup")
async def on_startup():
    await browser_pool.startup()


@app.on_event("shutdown")
async def on_shutdown():
    await browser_pool.shutdown()


@app.get("/healthz", response_model=HealthResponse)
async def healthz():
    uptime = time.time() - startup_time
    return HealthResponse(
        status="ok",
        active_sessions=cf_sessions.active_sessions(),
        active_browsers=browser_pool.total_count,
        uptime_seconds=uptime,
        timestamp=datetime.utcnow(),
    )


@app.post("/bypass_simple", response_model=BypassResult)
async def bypass_simple(payload: BypassRequest, token: str = Depends(require_token)):
    validate_target(payload.target_url)
    page = await browser_pool.acquire_page()
    bypasser = TurnstileBypasser()
    start = time.time()
    try:
        result = await bypasser.try_bypass(page, payload.target_url)
        logs.append(
            {
                "time": datetime.utcnow().isoformat(),
                "token": token,
                "method": "/bypass_simple",
                "domain": urlparse(payload.target_url).hostname,
                "elapsed": int((time.time() - start) * 1000),
                "status": result.status,
            }
        )
        return result
    finally:
        await browser_pool.release_page(page)


@app.post("/cf_proxy", response_model=ProxyResponse, responses={401: {"model": ErrorResponse}})
async def cf_proxy(payload: ProxyRequest, token: str = Depends(require_token)):
    validate_target(str(payload.url))
    domain = urlparse(str(payload.url)).hostname or ""
    rate_limiter.check(token, domain)
    start = time.time()
    response = await cf_sessions.request(
        method=payload.method,
        url=str(payload.url),
        headers=payload.headers,
        body=payload.body,
        timeout=payload.timeout,
    )
    logs.append(
        {
            "time": datetime.utcnow().isoformat(),
            "token": token,
            "method": payload.method,
            "domain": domain,
            "elapsed": int((time.time() - start) * 1000),
            "status": response.status_code,
        }
    )
    return ProxyResponse(status_code=response.status_code, headers=dict(response.headers), body=response.text)


@app.get("/browse/{path:path}", response_class=HTMLResponse)
async def browse(path: str, request: Request, token: str = Depends(require_token)):
    if path.startswith("http"):
        target = path
    else:
        target = "https://" + path
    validate_target(target)
    domain = urlparse(target).hostname or ""
    rate_limiter.check(token, domain)

    await cf_sessions.ensure_session(target)
    resp = await cf_sessions.request("GET", target, headers={}, body=None, timeout=None)
    logs.append(
        {
            "time": datetime.utcnow().isoformat(),
            "token": token,
            "method": "browse",
            "domain": domain,
            "elapsed": 0,
            "status": resp.status_code,
        }
    )
    return HTMLResponse(content=resp.text, status_code=resp.status_code)


# Panel

def is_logged_in(request: Request) -> bool:
    return request.cookies.get("panel_logged_in") == "1"


@app.get("/panel", response_class=HTMLResponse)
async def panel_home(request: Request):
    if not settings.panel_enabled:
        raise HTTPException(status_code=404)
    if not is_logged_in(request):
        return RedirectResponse(url="/panel/login")
    state = DashboardState(
        session_count=cf_sessions.active_sessions(),
        busy_browsers=browser_pool.busy_count,
        free_browsers=browser_pool.free_count,
        recent_logs=list(reversed(logs[-20:])),
        tokens=settings.api_tokens,
    )
    return templates.TemplateResponse("panel/dashboard.html", {"request": request, "state": state})


@app.get("/panel/login", response_class=HTMLResponse)
async def panel_login_form(request: Request):
    return templates.TemplateResponse("panel/login.html", {"request": request, "error": None})


@app.post("/panel/login")
async def panel_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == settings.admin_user and password == settings.admin_password:
        resp = RedirectResponse(url="/panel", status_code=302)
        resp.set_cookie("panel_logged_in", "1", httponly=True, max_age=3600)
        return resp
    return templates.TemplateResponse(
        "panel/login.html", {"request": request, "error": "用户名或密码错误"}, status_code=401
    )


@app.post("/panel/logout")
async def panel_logout():
    resp = RedirectResponse(url="/panel/login", status_code=302)
    resp.delete_cookie("panel_logged_in")
    return resp


@app.get("/.env.example", response_class=PlainTextResponse)
async def env_example():
    return PlainTextResponse(EXAMPLE_ENV)



@app.post("/bypass", response_model=BypassResult)
def bypass_endpoint(target_url: str = "https://nowsecure.in") -> BypassResult:
    try:
        return bypass_turnstile(target_url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=False)

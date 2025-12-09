import os
import sys
import time
import threading
import requests
from typing import Dict, Optional, Any
from urllib.parse import urlparse

from DrissionPage import ChromiumOptions, ChromiumPage
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

# ===========================
# 1. 配置与全局状态
# ===========================

app = FastAPI(title="CF-Clearance-Proxy", version="3.0.0")

# 缓存 Cookie 和 UA 的全局字典
# 结构: { "domain.com": { "cookies": {...}, "ua": "...", "timestamp": 123456 } }
COOKIE_STORE: Dict[str, Dict[str, Any]] = {}
STORE_LOCK = threading.Lock() # 读写锁

# 浏览器生成锁，防止对同一域名同时启动多个浏览器
BROWSER_LOCK = threading.Lock()

IS_LINUX = sys.platform.startswith("linux")
if IS_LINUX:
    from pyvirtualdisplay import Display

# ===========================
# 2. 核心过盾逻辑 (保留你原本的逻辑)
# ===========================

def create_page_options():
    co = ChromiumOptions()
    if IS_LINUX:
        co.set_browser_path("/usr/bin/google-chrome")
    
    # 核心配置
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-gpu")
    co.set_argument("--lang=en-US")
    co.headless(False) # 必须有头模式
    
    return co

def solve_challenge(target_url: str) -> Dict[str, Any]:
    """
    启动浏览器，访问 URL，过盾，提取 Cookie 和 UA。
    """
    display = None
    page = None
    try:
        # 1. 启动虚拟显示器 (Linux)
        if IS_LINUX:
            display = Display(visible=0, size=(1920, 1080))
            display.start()
        
        # 2. 启动浏览器
        co = create_page_options()
        page = ChromiumPage(co)
        
        print(f"🕵️ [Solver] 正在启动浏览器访问: {target_url}")
        page.get(target_url)
        
        # 3. 原始检测逻辑 (保留你的代码)
        # --- start of your logic ---
        print("🔄 [Solver] 正在检测 Turnstile...")
        time.sleep(2) # 等待加载
        
        # 尝试点击
        try:
            challenge_solution = page.ele("@name=cf-turnstile-response", timeout=5)
            if challenge_solution:
                print("👁️ [Solver] 发现验证组件，点击中...")
                challenge_wrapper = challenge_solution.parent()
                iframe = challenge_wrapper.shadow_root.ele("tag:iframe")
                checkbox = iframe.ele("tag:body").shadow_root.ele("tag:input")
                if checkbox:
                    checkbox.click()
                    time.sleep(3) # 等待验证结果
        except Exception as e:
            print(f"⚠️ [Solver] 交互检测跳过或失败: {e}")

        # 等待直到不再是 Just a moment 或者超时
        for _ in range(20):
            title = page.title.lower()
            if "just a moment" not in title and "cloudflare" not in title:
                print("✅ [Solver] 标题已变更，判断为通过。")
                break
            time.sleep(1)
        # --- end of your logic ---

        # 4. 提取凭证
        cookies = page.cookies(as_dict=True)
        user_agent = page.user_agent
        
        # 简单验证是否真的拿到了 clearance
        # 注意：有些站点可能只给 token 不给 clearance，视具体情况
        if not cookies:
             raise Exception("未获取到任何 Cookies")

        return {
            "cookies": cookies,
            "ua": user_agent,
            "title": page.title
        }

    except Exception as e:
        print(f"❌ [Solver] 失败: {e}")
        raise e
    finally:
        if page:
            page.quit()
        if display:
            display.stop()

# ===========================
# 3. 会话管理与代理逻辑
# ===========================

def get_cached_credentials(domain: str) -> Optional[Dict]:
    """从内存获取缓存的凭证"""
    with STORE_LOCK:
        data = COOKIE_STORE.get(domain)
        if not data:
            return None
        # 这里可以加过期时间判断，例如 30 分钟过期
        if time.time() - data['timestamp'] > 1800:
            print(f"⏰ [Cache] 域名 {domain} 的缓存已过期")
            del COOKIE_STORE[domain]
            return None
        return data

def update_cache(domain: str, cookies: dict, ua: str):
    """更新缓存"""
    with STORE_LOCK:
        COOKIE_STORE[domain] = {
            "cookies": cookies,
            "ua": ua,
            "timestamp": time.time()
        }
    print(f"💾 [Cache] 已更新 {domain} 的凭证")

async def perform_proxy_request(url: str, method: str = "GET", **kwargs):
    """
    核心代理函数：
    1. 检查缓存 -> 有则直接请求
    2. 无则启动浏览器 -> 获取凭证 -> 存缓存 -> 请求
    3. 请求失败(403/503) -> 强制刷新浏览器 -> 重试
    """
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # 获取凭证
    creds = get_cached_credentials(domain)
    
    if not creds:
        # 无缓存，需要在线程池中运行浏览器(因为是同步阻塞代码)
        print(f"⚡ [Proxy] 无缓存，启动过盾: {domain}")
        with BROWSER_LOCK:
             # 双重检查
            creds = get_cached_credentials(domain)
            if not creds:
                result = await run_in_threadpool(solve_challenge, url)
                update_cache(domain, result['cookies'], result['ua'])
                creds = get_cached_credentials(domain)

    # 构造请求
    # 注意：必须使用浏览器拿到的 UA
    headers = kwargs.get("headers", {})
    headers["User-Agent"] = creds["ua"]
    
    try:
        print(f"🚀 [Proxy] 发起请求: {url}")
        resp = requests.request(
            method=method,
            url=url,
            cookies=creds["cookies"],
            headers=headers,
            timeout=15,
            allow_redirects=True
        )
        
        # 简单的反爬判断：如果是 403 或 503，且包含 CF 特征，可能 Cookie 失效
        if resp.status_code in [403, 503] and ("Just a moment" in resp.text or "cloudflare" in resp.text.lower()):
            print("🔄 [Proxy] Cookie 可能失效，尝试重新过盾...")
            # 移除缓存
            with STORE_LOCK:
                if domain in COOKIE_STORE:
                    del COOKIE_STORE[domain]
            # 递归重试一次 (慎用递归，这里只试一次)
            # 实际生产中应抛出异常让客户端决定是否重试，这里为了方便直接重试
            # (简略处理：直接抛出错误让用户重试，防止死循环)
            raise HTTPException(status_code=503, detail="Cloudflare Challenge Triggered. Please retry.")
            
        return resp
        
    except Exception as e:
        print(f"💥 [Proxy] 请求发生错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===========================
# 4. API 接口定义
# ===========================

# --- Web 面板 ---
@app.get("/", response_class=HTMLResponse)
def dashboard():
    """简单的管理面板"""
    rows = ""
    with STORE_LOCK:
        for domain, data in COOKIE_STORE.items():
            age = int(time.time() - data['timestamp'])
            rows += f"""
            <tr>
                <td>{domain}</td>
                <td>{len(data['cookies'])} 个</td>
                <td>{age} 秒前</td>
                <td><button onclick="clearDomain('{domain}')">清除</button></td>
            </tr>
            """
            
    html_content = f"""
    <html>
    <head>
        <title>CF Proxy Dashboard</title>
        <style>
            body {{ font-family: sans-serif; max-width: 800px; margin: 2rem auto; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
            th {{ background: #f4f4f4; }}
            button {{ background: #ff4444; color: white; border: none; padding: 5px 10px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <h1>🛡️ Cloudflare Proxy 面板</h1>
        <p>当前缓存的域名会话：</p>
        <table>
            <thead><tr><th>域名</th><th>Cookies</th><th>更新时间</th><th>操作</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        <script>
            function clearDomain(d) {{
                fetch('/admin/clear?domain=' + d, {{method: 'POST'}}).then(() => location.reload());
            }}
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/admin/clear")
def clear_cache(domain: str):
    with STORE_LOCK:
        if domain in COOKIE_STORE:
            del COOKIE_STORE[domain]
    return {"status": "ok"}

# --- 核心：通用代理 API (程序调用) ---
class ProxyRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: Dict[str, str] = {}
    data: Optional[Dict[str, Any]] = None

@app.post("/v1/request")
async def proxy_api(req: ProxyRequest):
    """
    给爬虫用的 API。
    输入：目标 URL
    输出：目标网页的 HTML/JSON (由本服务代为请求)
    """
    resp = await perform_proxy_request(req.url, req.method, headers=req.headers, data=req.data)
    
    # 构造返回
    return {
        "status_code": resp.status_code,
        "headers": dict(resp.headers),
        "content": resp.text, # 如果是二进制文件可能需要 base64 处理，这里假设是网页
        "cookies": resp.cookies.get_dict() # 返回最新 cookie
    }

# --- 核心：浏览器直接反代 (人类使用) ---
@app.get("/proxy")
async def browser_proxy(url: str = Query(..., description="目标URL")):
    """
    给普通浏览器用的。
    访问 http://localhost:8000/proxy?url=https://xyz.com
    直接显示目标网页。
    """
    resp = await perform_proxy_request(url, "GET")
    
    # 这里做简单的 HTML 返回。
    # 注意：复杂网站的 CSS/JS 相对路径会失效，这是简单反代的通病。
    # 但对于查看内容已经足够。
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("Content-Type", "text/html")
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

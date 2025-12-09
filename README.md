# Cloudflare 反代 / 过盾服务

基于 FastAPI + DrissionPage + Chromium 的简易 Cloudflare 反代服务，同时支持 API、浏览器入口和可视化面板。

## 功能概览
- `/healthz` 健康检查
- `/bypass_simple` 单 URL 过盾调试接口
- `/cf_proxy` 面向程序的完整代理 API
- `/browse/{path}` 浏览器可直接访问的反代入口
- `/panel` 管理面板（登录后查看状态）

## 配置（.env 示例）
`/.env.example` 路由会返回完整示例，核心字段如下：
```
BROWSER_PATH=/usr/bin/google-chrome
HEADLESS=true
DISPLAY_WIDTH=1280
DISPLAY_HEIGHT=720
MAX_BROWSER_INSTANCES=2
REQUEST_TIMEOUT=15
API_HOST=0.0.0.0
API_PORT=8000
API_TOKENS=demo-token-1,demo-token-2
ALLOWED_DOMAINS=.example.com,.69shuba.com
BLOCK_PRIVATE_IP=true
ADMIN_USER=admin
ADMIN_PASSWORD=changeme
PANEL_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

## 本地运行
```
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Docker 部署
```
docker build -t cf-proxy .
docker run -d -p 8000:8000 --env-file .env cf-proxy
```

## 使用说明（给朋友）
- 管理员访问 `http://服务器:8000/panel`，使用 `ADMIN_USER/ADMIN_PASSWORD` 登录，查看当前会话与 Token 列表。
- 给朋友创建或分发一个 API Token，调用接口时在 Header 中携带 `X-Token`。
- 调试过盾：
  ```bash
  curl -X POST http://服务器:8000/bypass_simple \
    -H "X-Token: <TOKEN>" \
    -H "Content-Type: application/json" \
    -d '{"target_url": "https://目标站"}'
  ```
- 作为代理调用：
  ```bash
  curl -X POST http://服务器:8000/cf_proxy \
    -H "X-Token: <TOKEN>" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://目标站", "method": "GET"}'
  ```
- 浏览器访问：在地址栏输入 `http://服务器:8000/browse/https://目标站`，浏览器会通过服务端代理访问目标站。

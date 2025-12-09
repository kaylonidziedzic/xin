---


# 🛡️ Cloudflare Proxy / Bypass Service

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Framework-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/DrissionPage-Automation-orange?style=for-the-badge" alt="DrissionPage">
</p>

> 基于 **FastAPI** + **DrissionPage** + **Chromium** 的高性能 Cloudflare 反代/过盾服务。支持 REST API 调用、浏览器直接访问以及可视化管理面板。

---

## ✨ 功能特性

* 🚀 **自动过盾**：内置 Turnstile 验证码自动点击与通过逻辑。
* 🕵️ **高隐匿性**：注入 JS 补丁修复指纹（Stealth Patch），模拟真实用户行为。
* 💾 **会话保持**：自动缓存 Cookies 和 Session，减少重复过盾次数，提高响应速度。
* 🔌 **通用 API**：提供 `GET/POST` 通用代理接口，支持自定义 Headers 和 Body。
* 📊 **管理面板**：可视化的 Dashboard，实时查看 Token、活跃会话和浏览器实例状态。
* 🐳 **Docker 部署**：一键构建部署，开箱即用。

---

## 💻 服务器配置建议

由于 Chromium 浏览器极其消耗 CPU 和内存，请根据并发需求选择配置：

| 等级 | 适用场景 | CPU | 内存 (RAM) | 建议并发数 (`MAX_BROWSER_INSTANCES`) |
| :--- | :--- | :--- | :--- | :--- |
| **入门** | 个人测试、低频调用 | 1 核 | 1GB (+2GB Swap) | `1` |
| **推荐** | 生产环境、稳定运行 | **2 核** | **2GB - 4GB** | `2` - `4` |
| **高配** | 高并发采集 | 4 核+ | 8GB+ | `5`+ (每增加1实例需+500MB内存) |

> **注意**：如果内存低于 2GB 且未开启 Swap，浏览器启动时极易导致容器崩溃。

---
## 🐳 Docker 部署（推荐）

这是最简单、最稳定的部署方式。

### 1. 准备配置文件
在项目根目录创建 `.env` 文件（**注意：列表项必须使用 JSON 格式**）：

```ini
# 浏览器配置 (Docker内通常不需要改)
BROWSER_PATH=/usr/bin/chromium
HEADLESS=true
MAX_BROWSER_INSTANCES=2

# API 服务
API_HOST=0.0.0.0
API_PORT=8000

# 🔐 安全配置 (注意：必须使用 JSON 格式 ["..."])
API_TOKENS=["your-secret-token", "demo-token"]
ALLOWED_DOMAINS=[".example.com", ".google.com"]
BLOCK_PRIVATE_IP=true

# 面板配置
ADMIN_USER=admin
ADMIN_PASSWORD=your_secure_password
PANEL_ENABLED=true
````

### 2\. 启动服务

```bash
# 构建镜像
docker build -t cf-proxy .

# 启动容器
docker run -d \
  --name cf-proxy \
  -p 8000:8000 \
  --env-file .env \
  cf-proxy
```

-----

## 🛠️ 本地开发运行

如果您需要在本地（Windows/Linux/Mac）直接运行代码：

1.  **安装依赖**：
    ```bash
    pip install -r requirements.txt
    ```
2.  **配置环境**：
    修改 `.env` 文件，确保 `BROWSER_PATH` 指向您本机 Chrome/Edge 的实际路径。
3.  **运行**：
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

-----

## 🔌 API 使用指南

### 1\. 通用代理 (`/cf_proxy`)

通过服务端代理发起请求，自动处理 Cloudflare 验证。

  * **Endpoint**: `POST /cf_proxy`
  * **Headers**: `X-Token: <your-token>`

**Curl 示例**:

```bash
curl -X POST http://localhost:8000/cf_proxy \
  -H "X-Token: your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "[https://nowsecure.nl](https://nowsecure.nl)",
    "method": "GET",
    "headers": {"User-Agent": "Custom-UA"}
  }'
```

### 2\. 简单过盾测试 (`/bypass_simple`)

仅返回通过验证后的 Cookies 和 UserAgent，不返回页面内容。

**Curl 示例**:

```bash
curl -X POST http://localhost:8000/bypass_simple \
  -H "X-Token: your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"target_url": "[https://nowsecure.nl](https://nowsecure.nl)"}'
```

### 3\. 浏览器直连 (`/browse`)

在浏览器地址栏直接输入，即可通过代理浏览目标网站（适合调试）。

  * **格式**: `http://服务器IP:8000/browse/<目标URL>`
  * **示例**: `http://localhost:8000/browse/https://www.google.com`

-----

## 📊 管理面板

访问 `http://服务器IP:8000/panel` 查看系统状态。

  * **默认用户**: `admin`
  * **默认密码**: `changeme` (请在 .env 中修改)

面板功能：

  * 查看当前活跃的 Cloudflare 会话数。
  * 监控浏览器实例的繁忙/空闲状态。
  * 查看最近的 API 请求日志与耗时。

-----

## ❓ 常见问题 (FAQ)

**Q: 启动报错 `SettingsError: error parsing env var "api_tokens"`**

> **A:** 这是因为 Pydantic 版本兼容性问题。请确保 `.env` 文件中的列表变量使用严格的 JSON 格式。
>
>   * ❌ 错误：`API_TOKENS=token1,token2`
>   * ✅ 正确：`API_TOKENS=["token1", "token2"]`

**Q: Docker 启动后立即退出，日志提示找不到浏览器？**

> **A:** 请检查 `.env` 中的 `BROWSER_PATH`。
>
>   * Docker 环境下应固定为：`/usr/bin/chromium`
>   * 本地环境下请改为您本机的 Chrome 路径。

-----

## ⚠️ 免责声明

本项目仅供技术研究与学习使用。请勿用于任何非法用途（如攻击网站、绕过付费墙等）。使用者需自行承担使用本工具产生的一切法律责任。


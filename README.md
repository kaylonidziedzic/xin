这是一个按**开源基础设施级项目**标准撰写的 `README.md`。

它去掉了具体的 APP 配置指南，转而专注于**架构设计、接口规范、部署运维**等后端视角的内容。这会让你的 GitHub 仓库看起来非常专业，像是一个值得信赖的长期维护项目。

---

# 🛡️ Cloudflare Gateway Pro

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python" alt="Python Version">
  <img src="https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/Cloudflare-Bypass-orange?style=for-the-badge&logo=cloudflare" alt="Bypass">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

> **企业级 Cloudflare 穿透网关与反爬虫代理服务。**  
> 专为高难度目标站点设计，集成了 TLS 指纹模拟、自动化过盾与智能编码清洗功能。

---

## 📖 简介 (Introduction)

**Cloudflare Gateway Pro** 是一个高性能的中间件服务。它旨在解决现代爬虫和数据采集工具面临的 "Cloudflare Turnstile" 验证与 TLS 指纹识别难题。

该项目采用 **"读写分离"** 的架构设计：
1.  **Solver (浏览器层)**：使用 `DrissionPage` 进行自动化交互，解决 JS 挑战、5秒盾和 Turnstile 验证码，获取高信任度 Cookie。
2.  **Requester (请求层)**：使用 `curl_cffi` 模拟真实的 Chrome TLS 指纹 (JA3/JA4)，携带 Cookie 发起高并发请求。

这种架构既保证了过盾的成功率，又确保了数据采集的高吞吐量与低资源占用。

---

## ✨ 核心特性 (Features)

*   **🛡️ 全自动过盾**
    *   智能识别 Cloudflare 拦截页面。
    *   自动处理 Shadow DOM 下的 Turnstile 验证码点击。
    *   支持 5秒盾（Under Attack Mode）的自动等待与判定。

*   **🕵️ 完美指纹模拟**
    *   集成 `curl_cffi`，在协议层模拟 Chrome 110+ 的 TLS 握手特征。
    *   有效绕过对 Python `requests`/`urllib` 等标准库的指纹封锁。

*   **🧩 智能响应清洗**
    *   **自动解码**：智能识别 HTML Meta 标签，自动将 GBK/Big5 等老旧编码转换为 UTF-8。
    *   **资源修复**：自动注入 `<base>` 标签，修复 HTML 中的相对路径（图片/CSS/JS），确保直连访问时的页面渲染正常。

*   **🔐 企业级鉴权**
    *   支持 API Key 认证，提供 Header (`X-API-KEY`) 和 URL Query (`?key=`) 两种鉴权方式。

---

## 🏗️ 部署指南 (Deployment)

### 1. Docker Compose 部署 (推荐)

在生产环境中，建议使用 Docker Compose 进行管理。

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  cf-gateway:
    image: cf-gateway-pro:latest
    build: .
    container_name: cf-gateway
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
      - API_KEY=change_me_strong_password  # 请务必修改此密码
      - HEADLESS=False  # 生产环境通常配合 xvfb 使用，保持 False 即可
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs  # 挂载日志目录
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G      # 建议限制内存，防止 Chrome 内存泄漏
```

启动服务：
```bash
docker-compose up -d
```

### 2. Docker CLI 部署

```bash
# 构建镜像
docker build -t cf-gateway-pro .

# 启动容器
docker run -d \
  -p 8000:8000 \
  -e API_KEY="your_secret_key" \
  -v $(pwd)/logs:/app/logs \
  --name cf-gateway \
  cf-gateway-pro
```

### 3. 建议服务器配置

由于内置了 Chrome 浏览器内核，建议服务器配置如下：
*   **CPU**: 1 Core+
*   **RAM**: 1GB+ (Chrome 运行时需占用 300MB-500MB 内存)
*   **OS**: Debian 11/12 (推荐), Ubuntu 20.04+

---

## 🔌 API 文档 (API Reference)

服务默认运行在 HTTP 协议上。

### 1. 通用代理接口 (API Mode)
适用于爬虫程序、后端服务调用。返回结构化的 JSON 数据。

*   **URL**: `/v1/proxy`
*   **Method**: `POST`
*   **Auth**: Header `X-API-KEY: <your_key>`
*   **Content-Type**: `application/json`

**请求参数 (Body):**

| 字段 | 类型 | 必选 | 说明 |
| :--- | :--- | :--- | :--- |
| `url` | string | 是 | 目标 URL |
| `method` | string | 否 | 请求方法，默认 `GET` |
| `headers` | dict | 否 | 自定义请求头 |
| `data` | dict | 否 | 表单数据 (用于 POST) |
| `json_body` | dict | 否 | JSON 数据 (用于 POST) |

**响应示例:**

```json
{
  "status": 200,
  "url": "https://target.com",
  "headers": { ... },
  "cookies": { "cf_clearance": "..." },
  "encoding": "utf-8",
  "text": "<html>...</html>"
}
```

---

### 2. 网页/资源代理接口 (Reader Mode)
适用于浏览器直接访问、RSS 阅读器、WebView 集成。返回处理后的 HTML 或二进制流。

#### A. 获取内容 (GET)
*   **URL**: `/reader`
*   **Method**: `GET`
*   **Auth**: Query Param `?key=<your_key>`
*   **Query Params**:
    *   `url`: 目标 URL (需 URLEncode)

**示例:**
```bash
curl -L "http://localhost:8000/reader?key=123&url=https%3A%2F%2Fexample.com"
```

#### B. 提交搜索 (POST)
支持直接转发 Form 表单数据，适合对接搜索框。

*   **URL**: `/reader`
*   **Method**: `POST`
*   **Auth**: Query Param `?key=<your_key>`
*   **Query Params**: `url=https://target.com/search`
*   **Body**: `application/x-www-form-urlencoded` 表单数据

---

### 3. 原始数据接口 (Raw Mode)
不做任何 HTML 处理，直接返回二进制数据。适合图片、文件下载。

*   **URL**: `/raw`
*   **Method**: `GET`
*   **Auth**: Query Param `?key=<your_key>`

---

## 🗺️ 演进路线 (Roadmap)

本项目正处于快速迭代中，未来的版本规划如下：

### v2.x - 稳定性与持久化
- [x] **v2.0**: 核心过盾逻辑、TLS 指纹模拟、多模式 API (Current)
- [ ] **v2.1**: SQLite/Redis Cookie 持久化（重启服务不丢失会话）
- [ ] **v2.2**: 僵尸进程自动清理与内存看门狗

### v3.x - 网络增强
- [ ] **v3.0**: 上游代理池集成 (Socks5/HTTP Proxy)，解决 IP 被封锁问题
- [ ] **v3.1**: 浏览器 Canvas/WebGL 指纹随机化

### v4.x - 集群与管理
- [ ] **v4.0**: 浏览器对象池 (Browser Pool) 支持高并发过盾
- [ ] **v4.1**: Web 管理面板 (Dashboard)，可视化监控与配置

---

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request。在提交 PR 之前，请确保你的代码符合 PEP8 规范并通过了本地测试。

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

<p align="center">Made with ❤️ for the Open Source Community</p>

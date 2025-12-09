import os
from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    # Browser
    browser_path: str = Field("/usr/bin/google-chrome", env="BROWSER_PATH")
    headless: bool = Field(True, env="HEADLESS")
    display_width: int = Field(1280, env="DISPLAY_WIDTH")
    display_height: int = Field(720, env="DISPLAY_HEIGHT")
    max_browser_instances: int = Field(2, env="MAX_BROWSER_INSTANCES")
    request_timeout: int = Field(15, env="REQUEST_TIMEOUT")

    # API server
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")

    # Security
    api_tokens: List[str] = Field([], env="API_TOKENS")
    allowed_domains: List[str] = Field([], env="ALLOWED_DOMAINS")
    block_private_ip: bool = Field(True, env="BLOCK_PRIVATE_IP")

    # Panel
    admin_user: str = Field("admin", env="ADMIN_USER")
    admin_password: str = Field("admin", env="ADMIN_PASSWORD")
    panel_enabled: bool = Field(True, env="PANEL_ENABLED")

    # Rate limiting
    rate_limit_per_minute: int = Field(60, env="RATE_LIMIT_PER_MINUTE")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("api_tokens", "allowed_domains", pre=True)
    def split_csv(cls, v):  # type: ignore
        if not v:
            return []
        if isinstance(v, list):
            return v
        return [item.strip() for item in str(v).split(",") if item.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


EXAMPLE_ENV = """\
# 浏览器配置
BROWSER_PATH=/usr/bin/google-chrome
HEADLESS=true
DISPLAY_WIDTH=1280
DISPLAY_HEIGHT=720
MAX_BROWSER_INSTANCES=2
REQUEST_TIMEOUT=15

# API 服务
API_HOST=0.0.0.0
API_PORT=8000

# 安全
API_TOKENS=demo-token-1,demo-token-2
ALLOWED_DOMAINS=.example.com,.69shuba.com
BLOCK_PRIVATE_IP=true

# 面板
ADMIN_USER=admin
ADMIN_PASSWORD=changeme
PANEL_ENABLED=true

# 限流
RATE_LIMIT_PER_MINUTE=60
"""

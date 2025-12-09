from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, HttpUrl


class BypassRequest(BaseModel):
    target_url: HttpUrl


class BypassResult(BaseModel):
    success: bool
    status: str
    title: Optional[str] = None
    token: Optional[str] = None
    message: str
    screenshot_base64: Optional[str] = None


class ProxyRequest(BaseModel):
    url: HttpUrl
    method: str = Field("GET", regex="^[A-Z]+$")
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    timeout: Optional[int] = None


class ProxyResponse(BaseModel):
    status_code: int
    headers: Dict[str, str]
    body: str


class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    active_sessions: int
    active_browsers: int
    uptime_seconds: float
    timestamp: datetime


class SessionInfo(BaseModel):
    domain: str
    user_agent: str
    expires_at: Optional[datetime]
    last_validated_at: datetime


class DashboardState(BaseModel):
    session_count: int
    busy_browsers: int
    free_browsers: int
    recent_logs: list
    tokens: list

from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlparse

import requests

from browser_pool import browser_pool
from config import get_settings
from models import BypassResult
from bypass import TurnstileBypasser


class CFSession:
    def __init__(self, domain: str, cookies: Dict[str, str], user_agent: str):
        self.domain = domain
        self.cookies = cookies
        self.user_agent = user_agent
        self.last_validated_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(hours=2)

    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at


class CFSessionManager:
    def __init__(self):
        self.settings = get_settings()
        self.sessions: Dict[str, CFSession] = {}
        self.bypasser = TurnstileBypasser()

    def get_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.hostname or parsed.netloc

    async def ensure_session(self, url: str) -> CFSession:
        domain = self.get_domain(url)
        if domain in self.sessions and self.sessions[domain].is_valid():
            return self.sessions[domain]

        page = await browser_pool.acquire_page()
        try:
            result: BypassResult = await self.bypasser.try_bypass(page, url)
            cookies_list = page.cookies()
            cookies = {item['name']: item['value'] for item in cookies_list}
            
            ua = page.user_agent
            session = CFSession(domain=domain, cookies=cookies, user_agent=ua)
            self.sessions[domain] = session
            return session
        finally:
            await browser_pool.release_page(page)

    async def request(self, method: str, url: str, headers: Dict[str, str], body: Optional[str], timeout: Optional[int]) -> requests.Response:
        session = await self.ensure_session(url)
        req_headers = {"User-Agent": session.user_agent, **headers}
        resp = requests.request(
            method=method,
            url=url,
            headers=req_headers,
            data=body,
            cookies=session.cookies,
            timeout=timeout or self.settings.request_timeout,
        )
        return resp

    def active_sessions(self) -> int:
        return len(self.sessions)


cf_sessions = CFSessionManager()

import time
from collections import defaultdict
from typing import Tuple

from fastapi import HTTPException

from config import get_settings


class RateLimiter:
    def __init__(self) -> None:
        self.buckets = defaultdict(list)
        self.settings = get_settings()

    def check(self, token: str, domain: str) -> None:
        key: Tuple[str, str] = (token, domain)
        now = time.time()
        window_start = now - 60
        self.buckets[key] = [ts for ts in self.buckets[key] if ts >= window_start]
        if len(self.buckets[key]) >= self.settings.rate_limit_per_minute:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        self.buckets[key].append(now)


def get_rate_limiter() -> RateLimiter:
    return RateLimiter()


rate_limiter = RateLimiter()

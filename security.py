import ipaddress
from typing import List
from urllib.parse import urlparse

from fastapi import Header, HTTPException

from config import get_settings


def require_token(x_token: str = Header(None)) -> str:
    settings = get_settings()
    if settings.api_tokens and x_token in settings.api_tokens:
        return x_token
    raise HTTPException(status_code=401, detail="Invalid or missing token")


def is_private_address(hostname: str) -> bool:
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def domain_allowed(url: str, allowed_domains: List[str]) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if not allowed_domains:
        return True
    for suffix in allowed_domains:
        if hostname.endswith(suffix.lstrip(".")):
            return True
    return False


def validate_target(url: str) -> None:
    settings = get_settings()
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if settings.block_private_ip and is_private_address(hostname):
        raise HTTPException(status_code=400, detail="Private address blocked")
    if not domain_allowed(url, settings.allowed_domains):
        raise HTTPException(status_code=400, detail="Domain not allowed")

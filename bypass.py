import time
from typing import Optional

from DrissionPage import ChromiumPage

from models import BypassResult


class TurnstileBypasser:
    async def try_bypass(self, page: ChromiumPage, target_url: str, max_wait: int = 15) -> BypassResult:
        page.get(target_url)
        time.sleep(2)

        token = self._extract_token(page)
        status = "NoChallenge" if token else "Clicked"
        if not token:
            token = self._click_checkbox(page, max_wait)
            status = "AutoPassed" if token else "Failed"

        title = page.title
        screenshot = page.get_screenshot(as_base64=True)
        message = "Bypass executed"
        return BypassResult(
            success=token is not None,
            status=status,
            title=title,
            token=token,
            message=message,
            screenshot_base64=screenshot if isinstance(screenshot, str) else None,
        )

    def _extract_token(self, page: ChromiumPage) -> Optional[str]:
        try:
            return page.run_js("try { return turnstile.getResponse() } catch(e) { return null }")
        except Exception:
            return None

    def _click_checkbox(self, page: ChromiumPage, max_wait: int) -> Optional[str]:
        start = time.time()
        while time.time() - start < max_wait:
            try:
                checkbox = page.ele("@name=cf-turnstile-response", timeout=3)
                if checkbox:
                    wrapper = checkbox.parent()
                    iframe = wrapper.shadow_root.ele("tag:iframe")
                    inner = iframe.ele("tag:body").shadow_root.ele("tag:input")
                    inner.click()
                    time.sleep(2)
                    token = self._extract_token(page)
                    if token:
                        return token
            except Exception:
                time.sleep(1)
        return None

import asyncio
import contextlib
from typing import Optional

from DrissionPage import ChromiumOptions, ChromiumPage

try:
    from pyvirtualdisplay import Display
except Exception:  # pragma: no cover - optional dependency on non-linux
    Display = None

from config import get_settings


class BrowserPool:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._semaphore = asyncio.Semaphore(self.settings.max_browser_instances)
        self._pages = []
        self._display: Optional[Display] = None
        self._lock = asyncio.Lock()

    async def startup(self) -> None:
        if Display and self._display is None:
            self._display = Display(
                visible=0,
                size=(self.settings.display_width, self.settings.display_height),
            )
            self._display.start()
        # lazy create pages on demand

    async def shutdown(self) -> None:
        async with self._lock:
            for page in self._pages:
                with contextlib.suppress(Exception):
                    page.quit()
            self._pages.clear()
            if self._display:
                with contextlib.suppress(Exception):
                    self._display.stop()
                self._display = None

    def _create_page(self) -> ChromiumPage:
        co = ChromiumOptions()
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-gpu")
        co.set_argument("--lang=en-US")
        if self.settings.headless:
            co.headless()
        if self.settings.browser_path:
            co.set_browser_path(self.settings.browser_path)
        return ChromiumPage(co)

    async def acquire_page(self) -> ChromiumPage:
        await self._semaphore.acquire()
        async with self._lock:
            for page in self._pages:
                if not getattr(page, "_busy", False):
                    page._busy = True  # type: ignore
                    return page
            page = self._create_page()
            page._busy = True  # type: ignore
            self._pages.append(page)
            return page

    async def release_page(self, page: ChromiumPage) -> None:
        page._busy = False  # type: ignore
        self._semaphore.release()

    @property
    def busy_count(self) -> int:
        return sum(1 for p in self._pages if getattr(p, "_busy", False))

    @property
    def free_count(self) -> int:
        return len(self._pages) - self.busy_count

    @property
    def total_count(self) -> int:
        return len(self._pages)


browser_pool = BrowserPool()

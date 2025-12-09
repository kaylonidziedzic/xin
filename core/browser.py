import threading
from DrissionPage import ChromiumOptions, ChromiumPage
from config import settings
from utils.logger import log
import sys

# Linux下启动虚拟显示器
if sys.platform.startswith("linux"):
    from pyvirtualdisplay import Display
    _display = Display(visible=0, size=(1920, 1080))
    _display.start()

class BrowserManager:
    _instance = None
    _lock = threading.Lock()
    page = None

    @classmethod
    def get_browser(cls):
        """获取浏览器实例（懒加载）"""
        with cls._lock:
            if cls.page is None or not cls.page.process_id:
                log.info("🖥️ 初始化 Chromium 浏览器...")
                try:
                    co = ChromiumOptions()
                    if sys.platform.startswith("linux"):
                        co.set_browser_path("/usr/bin/google-chrome")
                    
                    for arg in settings.BROWSER_ARGS:
                        co.set_argument(arg)
                    
                    co.headless(settings.HEADLESS)
                    cls.page = ChromiumPage(co)
                except Exception as e:
                    log.error(f"❌ 浏览器启动失败: {e}")
                    raise e
            return cls.page

    @classmethod
    def restart(cls):
        """强制重启浏览器（用于处理崩溃或内存泄漏）"""
        with cls._lock:
            if cls.page:
                try:
                    cls.page.quit()
                except:
                    pass
                cls.page = None
            log.warning("🔄 浏览器已重置")

browser_manager = BrowserManager()

import time
from core.browser import browser_manager
from utils.logger import log

def solve_turnstile(url: str):
    """
    核心过盾逻辑
    返回: {"cookies": dict, "ua": str}
    """
    page = browser_manager.get_browser()
    
    try:
        log.info(f"🕵️ 正在访问: {url}")
        
        # ⚠️ 关键优化：使用 tab 而不是整个 page，防止多线程上下文混乱
        # 但 DrissionPage 对多 Tab 并发支持有限，这里简单起见还是控制主 Page
        # 加锁确保同一时间只有一个线程在操作浏览器过盾
        with browser_manager._lock:
            page.get(url)
            
            # --- 你的原始判定逻辑 (优化版) ---
            start_time = time.time()
            success = False
            
            while time.time() - start_time < 20: # 最多等待20秒
                title = page.title.lower()
                
                # 1. 尝试点击验证 (如果存在)
                try:
                    # 使用较短的超时，避免阻塞太久
                    box = page.ele("@name=cf-turnstile-response", timeout=1) 
                    if box:
                        wrapper = box.parent()
                        iframe = wrapper.shadow_root.ele("tag:iframe")
                        cb = iframe.ele("tag:body").shadow_root.ele("tag:input")
                        if cb:
                            log.info("👆 发现验证码，点击中...")
                            cb.click()
                except:
                    pass

                # 2. 判断成功条件
                if "just a moment" not in title and "cloudflare" not in title:
                    log.success(f"✅ 过盾成功，当前标题: {title}")
                    success = True
                    break
                
                time.sleep(1)
            
            if not success:
                # 失败时才截图，且只返回 base64，不存文件
                err_img = page.get_screenshot(as_base64=True)
                log.error("❌ 验证超时")
                raise Exception("Cloudflare Bypass Timeout")

            # 3. 提取凭证
            return {
                "cookies": page.cookies(as_dict=True),
                "ua": page.user_agent
            }

    except Exception as e:
        log.error(f"💥 过盾过程异常: {e}")
        # 遇到严重错误尝试重启浏览器
        browser_manager.restart()
        raise e

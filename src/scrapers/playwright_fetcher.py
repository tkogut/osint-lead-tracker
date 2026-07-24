import asyncio
import logging
import re
from curl_cffi.requests import AsyncSession as CffiAsyncSession
from playwright.async_api import async_playwright

logger = logging.getLogger("osint.playwright")

async def fetch_with_playwright(url: str, user: str = "", pwd: str = "") -> str:
    """
    Fetches the URL using Playwright Chromium headless, performing multi-step login on xtech.pl
    if credentials are provided, duplicating cookies for .automatyka.pl, and returning HTML content.
    """
    logger.info("Starting Playwright fetch for: %s", url)
    cookies_for_playwright = []
    
    # Optional login step via HTTP first to extract auth cookies
    if user and pwd:
        try:
            logger.info("Logging in to xtech.pl JSON API to grab session cookies...")
            async with CffiAsyncSession(impersonate="chrome124") as s:
                r = await s.post(
                    "https://www.xtech.pl/zaloguj",
                    json={"LoginName": user, "Password": pwd, "Step": 1, "ServiceId": 3},
                    timeout=15
                )
                if r.status_code == 200:
                    for cookie in s.cookies.jar:
                        domain = cookie.domain if cookie.domain else ".xtech.pl"
                        # Replicate for both domains
                        cookies_for_playwright.append({
                            "name": cookie.name,
                            "value": cookie.value,
                            "domain": ".xtech.pl",
                            "path": "/",
                        })
                        cookies_for_playwright.append({
                            "name": cookie.name,
                            "value": cookie.value,
                            "domain": ".automatyka.pl",
                            "path": "/",
                        })
                    logger.info("Successfully fetched %d session cookies", len(cookies_for_playwright))
        except Exception as e:
            logger.warning("Optional pre-login cookie grab failed: %s", e)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
        )
        if cookies_for_playwright:
            await ctx.add_cookies(cookies_for_playwright)
            
        page = await ctx.new_page()
        try:
            logger.info("Navigating to target URL: %s", url)
            await page.goto(url, wait_until="load", timeout=30000)
            # Wait for dynamic AJAX content to load
            await page.wait_for_timeout(3000)
            html = await page.content()
            return html
        finally:
            await browser.close()

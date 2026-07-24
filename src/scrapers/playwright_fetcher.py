import asyncio
import logging
import re
from playwright.async_api import async_playwright

logger = logging.getLogger("osint.playwright")

async def fetch_with_playwright(url: str, user: str = "", pwd: str = "") -> str:
    """
    Fetches the URL using Playwright Chromium headless. If credentials are provided,
    performs multi-step login directly on automatyka.pl/zaloguj (which redirects to xtech.pl),
    extracts the active cookies, duplicates them for .automatyka.pl, and returns the notice content.
    """
    logger.info("Starting Playwright fetch for: %s", url)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()
        
        try:
            if user and pwd:
                logger.info("Navigating to login page...")
                await page.goto("https://www.automatyka.pl/zaloguj", wait_until="load", timeout=25000)
                
                await page.wait_for_selector("#LoginName", timeout=10000)
                await page.fill("#LoginName", user)
                logger.info("Filled LoginName, clicking DALEJ (#next)...")
                await page.click("#next")
                
                await page.wait_for_selector("#Password", timeout=10000)
                await page.fill("#Password", pwd)
                logger.info("Filled Password, clicking ZALOGUJ (#submit)...")
                await page.click("#submit")
                
                await page.wait_for_load_state("networkidle", timeout=20000)
                logger.info("Login process completed. Current URL: %s", page.url)
                
                # Extract and duplicate cookies
                xtech_cookies = await ctx.cookies()
                logger.info("Found %d cookies in session", len(xtech_cookies))
                
                duplicated_cookies = []
                for c in xtech_cookies:
                    duplicated_cookies.append(c)
                    if "xtech.pl" in c["domain"]:
                        new_c = c.copy()
                        new_c["domain"] = c["domain"].replace("xtech.pl", "automatyka.pl")
                        duplicated_cookies.append(new_c)
                        
                await ctx.add_cookies(duplicated_cookies)
                logger.info("Injected duplicated cookies. Total cookies: %d", len(await ctx.cookies()))

            logger.info("Navigating to target URL: %s", url)
            await page.goto(url, wait_until="load", timeout=30000)
            # Wait for dynamic AJAX content to load
            await page.wait_for_timeout(3000)
            html = await page.content()
            return html
        finally:
            await browser.close()

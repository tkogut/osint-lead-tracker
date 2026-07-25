import asyncio
import logging
import re
from typing import List, Dict
from playwright.async_api import async_playwright

logger = logging.getLogger("osint.playwright")

async def _login_session(ctx, page, user: str, scraper_password: str, context: str) -> None:
    if not (user and scraper_password):
        return

    if context == "Automatyka":
        logger.info("Navigating to login page...")
        await page.goto("https://www.automatyka.pl/zaloguj", wait_until="load", timeout=25000)
        
        await page.wait_for_selector("#LoginName", timeout=10000)
        await page.fill("#LoginName", user)
        logger.info("Filled LoginName, clicking DALEJ (#next)...")
        await page.click("#next")
        
        await page.wait_for_selector("#Password", timeout=10000)
        await page.fill("#Password", scraper_password)
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
    elif context == "BiznesPolska":
        logger.info("Playwright: Logging in to biznes-polska.pl...")
        await page.goto("https://www.biznes-polska.pl/logowanie/", wait_until="load", timeout=25000)
        
        await page.wait_for_selector("#username", timeout=10000)
        await page.fill("#username", user)
        
        await page.wait_for_selector("#password", timeout=10000)
        await page.fill("#password", scraper_password)
        
        logger.info("Playwright: Clicking login button...")
        await page.click("#login-form button.login")
        
        await page.wait_for_load_state("networkidle", timeout=20000)
        logger.info("Playwright: BiznesPolska login process completed. Current URL: %s", page.url)
    else:
        logger.warning("Unknown context for login: %s", context)

async def fetch_with_playwright(url: str, user: str = "", scraper_password: str = "", context: str = "Automatyka") -> str:
    """
    Fetches the URL using Playwright Chromium headless. If credentials are provided,
    performs multi-step login directly on automatyka.pl/zaloguj (which redirects to xtech.pl),
    extracts the active cookies, duplicates them for .automatyka.pl, and returns the notice content.
    """
    logger.info("Starting Playwright fetch for: %s in context %s", url, context)
    
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
            await _login_session(ctx, page, user, scraper_password, context)
            logger.info("Navigating to target URL: %s", url)
            await page.goto(url, wait_until="load", timeout=30000)
            # Wait for dynamic AJAX content to load
            await page.wait_for_timeout(3000)
            html = await page.content()
            return html
        finally:
            await browser.close()

async def fetch_multiple_with_playwright(
    urls: List[str],
    user: str = "",
    scraper_password: str = "",
    context: str = "Automatyka"
) -> Dict[str, str]:
    """
    Launches Playwright Chromium headless once.
    Performs login once at the start of the session if credentials (user/scraper_password) are provided,
    using logic specific to the context.
    Iterates through the list of URLs, navigates to each one (wait_until="load", timeout=30000),
    waits 3 seconds, and stores the HTML content in the returning dict.
    Handles per-URL exceptions gracefully without crashing the whole session.
    """
    logger.info("Starting multiple Playwright fetch for %d URLs in context %s", len(urls), context)
    results = {}
    if not urls:
        return results

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
            await _login_session(ctx, page, user, scraper_password, context)
            
            for url in urls:
                try:
                    logger.info("Navigating to target URL: %s", url)
                    await page.goto(url, wait_until="load", timeout=30000)
                    await page.wait_for_timeout(3000)
                    html = await page.content()
                    results[url] = html
                except Exception as url_err:
                    logger.error("Failed to fetch %s with Playwright: %s", url, url_err)
        finally:
            await browser.close()
            
    return results

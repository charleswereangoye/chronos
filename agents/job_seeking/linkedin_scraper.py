import os
import json
import logging
import asyncio
from typing import Dict, Any
from playwright.async_api import async_playwright

logger = logging.getLogger("LinkedinScraper")

class LinkedinScraper:
    def __init__(self):
        self.profile_url = os.getenv("LINKEDIN_PROFILE_URL")
        self.state_file = os.path.join(os.path.dirname(__file__), "state", "linkedin_state.json")

    async def scrape_profile(self) -> Dict[str, Any]:
        """Uses stored session state to dynamically scrape user profile details."""
        if not self.profile_url:
            logger.warning("Missing LINKEDIN_PROFILE_URL in .env")
            return {"error": "Missing LINKEDIN_PROFILE_URL in .env"}
            
        if not os.path.exists(self.state_file):
            logger.warning(f"Missing state file at {self.state_file}")
            return {"error": f"Missing state file at {self.state_file}"}
            
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()

                # Normalize and load cookies regardless of json format (list or dict)
                raw_cookies = cookie_data if isinstance(cookie_data, list) else cookie_data.get("cookies", [])
                valid_cookies = []
                for c in raw_cookies:
                    cookie_dict = dict(c)
                    # Clean up unsupported sameSite values for Playwright
                    if "sameSite" in cookie_dict and cookie_dict["sameSite"] not in ["Strict", "Lax", "None"]:
                        del cookie_dict["sameSite"]
                    valid_cookies.append(cookie_dict)

                if valid_cookies:
                    await context.add_cookies(valid_cookies)

                page = await context.new_page()
                logger.info(f"Navigating to LinkedIn profile: {self.profile_url}")
                await page.goto(self.profile_url, wait_until="domcontentloaded", timeout=35000)
                await page.wait_for_timeout(3000)

                page_title = await page.title()
                if "Sign In" in page_title or "Join LinkedIn" in page_title:
                    logger.warning("LinkedIn session appears expired or unauthorized.")
                    await browser.close()
                    return {"error": "LinkedIn session expired. Please refresh linkedin_state.json."}

                # Smoothly scroll down to trigger lazy loading of profile sections
                for _ in range(3):
                    await page.mouse.wheel(0, 1000)
                    await page.wait_for_timeout(1000)

                # Extract main container text for full LLM understanding
                main_el = page.locator("main")
                full_text = await main_el.inner_text() if await main_el.count() > 0 else ""

                # Extract key profile sections
                lines = [line.strip() for line in full_text.split("\n") if line.strip()]
                name = lines[0] if len(lines) > 0 else ""
                
                headline = ""
                for line in lines[1:6]:
                    if "Verify" not in line and "Nairobi" not in line and "connections" not in line and "Open to" not in line:
                        headline = line
                        break

                await browser.close()

                return {
                    "name": name,
                    "headline": headline,
                    "profile_url": self.profile_url,
                    "raw_profile_text": full_text[:4000]
                }

        except Exception as e:
            logger.error(f"Failed to scrape LinkedIn profile: {e}")
            return {"error": str(e)}

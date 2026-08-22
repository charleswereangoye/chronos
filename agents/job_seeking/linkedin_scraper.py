import os
import logging
import asyncio
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class LinkedinScraper:
    def __init__(self):
        self.profile_url = os.getenv("LINKEDIN_PROFILE_URL")
        # Define the path to the state.json file
        self.state_file = os.path.join(os.path.dirname(__file__), "state", "linkedin_state.json")

    async def scrape_profile(self):
        """Uses stored session state to scrape the user profile."""
        if not self.profile_url:
            logger.warning("Missing LINKEDIN_PROFILE_URL in .env")
            return {"error": "Missing LINKEDIN_PROFILE_URL in .env"}
            
        if not os.path.exists(self.state_file):
            logger.warning(f"Missing state file at {self.state_file}")
            return {"error": "Please place your exported state.json into the assets folder as linkedin_state.json"}
            
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # Load the browser context with the stored cookies/state
                context = await browser.new_context(storage_state=self.state_file)
                page = await context.new_page()
                
                # Navigate straight to profile since we are already authenticated
                await page.goto(self.profile_url, wait_until="networkidle")
                
                # Basic scraping (this is a simplified example as LinkedIn DOM is complex and dynamic)
                await page.wait_for_selector("h1", timeout=10000)
                name = await page.locator("h1").first.text_content()
                
                # Headline
                headline_loc = page.locator("div.text-body-medium.break-words")
                headline = await headline_loc.first.text_content() if await headline_loc.count() > 0 else ""
                
                # About section (simplified)
                about_loc = page.locator("div#about ~ div .display-flex .visually-hidden")
                about = await about_loc.first.text_content() if await about_loc.count() > 0 else ""
                
                await browser.close()
                
                return {
                    "name": name.strip() if name else "",
                    "headline": headline.strip() if headline else "",
                    "about": about.strip() if about else ""
                }
        except Exception as e:
            logger.error(f"Failed to scrape LinkedIn: {e}")
            return {"error": str(e)}

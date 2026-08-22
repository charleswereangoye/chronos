import os
import logging
from playwright.async_api import async_playwright
from google import genai
from agents.job_seeking.profile_synthesizer import ProfileSynthesizer
from shared.config import get_gemini_client_and_model

logger = logging.getLogger(__name__)

class CoverLetterGenerator:
    def __init__(self):
        self.client, self.model_name = get_gemini_client_and_model()
        self.synthesizer = ProfileSynthesizer()
        self.output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(self.output_dir, exist_ok=True)

    async def scrape_job_description(self, url: str) -> str:
        text_content = ""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                # extract body text
                text_content = await page.locator("body").inner_text()
                await browser.close()
        except Exception as e:
            logger.error(f"Failed to scrape job description: {e}")
            text_content = f"Failed to scrape description from {url}."
        return text_content[:5000] # Limit tokens

    async def generate(self, url: str) -> str:
        logger.info("Synthesizing candidate data for cover letter...")
        candidate_data = await self.synthesizer.synthesize()
        
        logger.info("Scraping job posting...")
        job_description = await self.scrape_job_description(url)
        
        prompt = f"""
You are an expert career coach and copywriter.
Write a compelling, professional cover letter for the candidate below applying to the job described below.
Do not use placeholders like [Date] or [Company Name] if you can extract them from the job description or context.

CRITICAL INSTRUCTIONS TO AVOID "AI" TONE:
1. ABSOLUTELY NO em-dashes (—). Do not use them anywhere.
2. DO NOT use robotic or overly enthusiastic transitions (e.g., "I am thrilled to apply", "Furthermore", "In conclusion", "A testament to my...").
3. Write like a real, confident human being. Keep the language grounded, direct, and conversational.
4. Keep the structure simple, matching a standard formal business letter (like a Google Doc template).

--- CANDIDATE DATA ---
{candidate_data}

--- JOB DESCRIPTION ---
{job_description}

Write the cover letter in plain text, well-formatted.
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        
        return response.text.strip()

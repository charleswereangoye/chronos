import logging
from playwright.async_api import async_playwright
from google import genai
from agents.job_seeking.profile_synthesizer import ProfileSynthesizer
import os
from shared.config import get_gemini_client_and_model

logger = logging.getLogger(__name__)

class InterviewPrepBot:
    def __init__(self):
        self.client, self.model_name = get_gemini_client_and_model()
        self.synthesizer = ProfileSynthesizer()

    async def scrape_job_description(self, url: str) -> str:
        text_content = ""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                text_content = await page.locator("body").inner_text()
                await browser.close()
        except Exception as e:
            logger.error(f"Failed to scrape job description: {e}")
            text_content = f"Failed to scrape description from {url}."
        return text_content[:5000]

    async def generate_prep_guide(self, url: str) -> str:
        logger.info("Synthesizing candidate data for interview prep...")
        candidate_data = await self.synthesizer.synthesize()
        
        logger.info("Scraping job posting...")
        job_description = await self.scrape_job_description(url)
        
        prompt = f"""
You are an expert technical interviewer and career coach.
You are preparing a candidate for an upcoming interview for the job described below.
Here is the candidate's profile:
{candidate_data}

Here is the Job Description:
{job_description}

Please provide a highly tailored Interview Prep Guide formatted in Markdown.
It should include:
1. 3 highly probable Behavioral Questions tailored to the company/role, along with a suggested bullet-point strategy for the candidate to answer based on their experience.
2. 3 highly probable Technical/Hard-Skill Questions based on the requirements, and how the candidate should relate them to their past projects.
3. 2 intelligent questions the candidate should ask the interviewers at the end.
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        
        return response.text.strip()

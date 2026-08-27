import os
import logging
from playwright.async_api import async_playwright
from agents.job_seeking.profile_synthesizer import ProfileSynthesizer
from agents.job_seeking.html_cleaner import clean_html_to_text
from shared.llm import generate_content_with_failover

logger = logging.getLogger("InterviewPrepBot")

class InterviewPrepBot:
    def __init__(self):
        self.synthesizer = ProfileSynthesizer()
        self.output_dir = os.path.join(os.path.dirname(__file__), 'state', 'output')
        os.makedirs(self.output_dir, exist_ok=True)

    async def scrape_job_description(self, url: str) -> str:
        raw_html = ""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                raw_html = await page.content()
                await browser.close()
        except Exception as e:
            logger.warning(f"Failed to scrape job description from {url}: {e}")
            raw_html = f"Job Posting URL: {url}"
            
        return clean_html_to_text(raw_html, max_chars=4500)

    async def generate_prep_guide(self, url_or_text: str) -> str:
        if url_or_text.startswith("http://") or url_or_text.startswith("https://"):
            logger.info(f"Scraping job posting for interview prep from: {url_or_text}...")
            job_description = await self.scrape_job_description(url_or_text)
        else:
            job_description = url_or_text[:4500]
            
        logger.info("Retrieving candidate data for interview prep...")
        candidate_data = await self.synthesizer.synthesize(job_description=job_description)
        
        prompt = f"""
You are a Principal Engineering Director and Senior Technical Interviewer.
Generate a comprehensive, high-standard Technical Interview Preparation Guide for this candidate applying to the target position below.

Candidate Background:
{candidate_data}

Target Role Description:
{job_description}

FORMAT YOUR PREPARATION GUIDE IN CLEAN MARKDOWN:

# 🎯 Strategic Interview Brief

### 1. Architectural & Technical Deep Dives (3 Core Questions)
For each question, provide:
* **Question**: A realistic scenario-based question (e.g. distributed concurrency, caching strategies, scaling async pipelines, container orchestration).
* **Key Concept Tested**: What the interviewer is evaluating.
* **Suggested Candidate Talking Points**: Concrete architectural choices and trade-offs the candidate should mention based on their Python, Docker, and API experience.

### 2. Behavioral & Leadership Scenarios (3 STAR Questions)
For each behavioral question, provide:
* **Question**: Common executive/leadership question (e.g. handling outages, resolving engineering disagreements, scaling under tight deadlines).
* **STAR Framework Response Strategy**:
  - **Situation & Task**: Specific context from candidate projects.
  - **Action**: Direct engineering leadership step taken.
  - **Result**: Quantifiable improvement and business outcome.

### 3. High-Impact Reverse-Interview Questions (3 Questions to Ask)
* 3 thoughtful questions to ask the VP of Engineering or Tech Lead that demonstrate deep technical maturity (e.g., questions about technical debt management, deployment cadence, telemetry, or system bottlenecks).

### 4. Critical Red Flags / Pitfalls to Avoid
* 2-3 specific mistakes or buzzwords to avoid during this particular interview.
"""
        response = generate_content_with_failover(prompt_text=prompt)
        return response.text.strip()

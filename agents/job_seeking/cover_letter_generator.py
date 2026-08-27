import os
import uuid
import logging
from playwright.async_api import async_playwright
from jinja2 import Template
from agents.job_seeking.profile_synthesizer import ProfileSynthesizer
from agents.job_seeking.html_cleaner import clean_html_to_text
from shared.llm import generate_content_with_failover

logger = logging.getLogger("CoverLetterGenerator")

COVER_LETTER_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Cover Letter - {{ candidate.name }}</title>
    <style>
        @page { size: A4; margin: 20mm 20mm; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 10.5pt;
            line-height: 1.6;
            color: #2D3748;
            margin: 0;
            padding: 0;
        }
        .header {
            border-bottom: 2px solid {{ dynamic_color | default('#0F52BA') }};
            padding-bottom: 15px;
            margin-bottom: 25px;
        }
        h1 {
            font-size: 20pt;
            font-weight: 800;
            color: #1A202C;
            margin: 0 0 6px 0;
            text-transform: uppercase;
            letter-spacing: -0.5px;
        }
        .contact {
            font-size: 9.5pt;
            color: #718096;
            font-weight: 500;
        }
        .content {
            white-space: pre-line;
            color: #2D3748;
            text-align: justify;
        }
        p {
            margin-bottom: 14px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ candidate.name | default('Charles Were Angoye') }}</h1>
        <div class="contact">
            {{ candidate.location }} &bull; {{ candidate.email }} &bull; {{ candidate.phone }}
        </div>
    </div>
    <div class="content">
{{ letter_body }}
    </div>
</body>
</html>
"""

class CoverLetterGenerator:
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
            logger.warning(f"Failed to scrape full HTML from {url}: {e}")
            raw_html = f"Job Posting URL: {url}"
            
        return clean_html_to_text(raw_html, max_chars=4500)

    async def generate_text(self, url_or_text: str) -> tuple[str, dict]:
        if url_or_text.startswith("http://") or url_or_text.startswith("https://"):
            logger.info(f"Scraping job posting for cover letter from: {url_or_text}...")
            job_description = await self.scrape_job_description(url_or_text)
        else:
            job_description = url_or_text[:4500]
            
        logger.info("Retrieving candidate data for tailored cover letter...")
        candidate_data = await self.synthesizer.synthesize(job_description=job_description)
        
        prompt = f"""
You are an elite software engineering director and executive copywriter.
Write a highly compelling, authentic cover letter for the candidate applying to the position described below.

CRITICAL INSTRUCTIONS TO ELIMINATE ALL "AI" SIGNATURES:
1. ABSOLUTELY NO em-dashes (—).
2. DO NOT use generic AI openings (e.g., "I am thrilled to submit my application", "I am writing with great enthusiasm").
   - OPEN STRONG: State the target role and immediately highlight 1-2 core architectural strengths directly relevant to their engineering challenges.
3. CONCRETE PROOF OVER BUZZWORDS:
   - Mention specific technical mechanisms (e.g., containerized async workflows in Python, high-throughput microservices, Redis caching, CI/CD pipelines).
   - Explain how you approach engineering trade-offs (system resilience, reliability, latency).
4. TONE: Confident, peer-to-peer, professional senior engineer communicating directly with an engineering leader.
5. NO PLACEHOLDERS: If company name cannot be found, address to "Engineering Hiring Team". Do not leave square brackets like [Date] or [Company Name].

--- CANDIDATE DATA ---
{candidate_data}

--- TARGET JOB DESCRIPTION ---
{job_description}

Write the complete cover letter text:
"""
        response = generate_content_with_failover(prompt_text=prompt)
        return response.text.strip(), candidate_data

    async def generate(self, url_or_text: str) -> str:
        letter_text, _ = await self.generate_text(url_or_text)
        return letter_text

    async def generate_pdf(self, letter_text: str, candidate_data: dict, color_hex: str = "#0F52BA") -> str:
        """Renders the cover letter to a sleek PDF and saves it in state/output/."""
        pdf_filename = f"cover_letter_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(self.output_dir, pdf_filename)
        
        template = Template(COVER_LETTER_HTML_TEMPLATE)
        html_rendered = template.render(
            candidate=candidate_data,
            letter_body=letter_text,
            dynamic_color=color_hex
        )
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_content(html_rendered, wait_until="networkidle")
                await page.pdf(
                    path=output_path,
                    print_background=True,
                    format="A4",
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
                )
                await browser.close()
            logger.info(f"Generated PDF cover letter at {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to generate cover letter PDF: {e}")
            raise

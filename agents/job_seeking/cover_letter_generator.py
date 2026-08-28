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

    def _is_bot_protected(self, text: str) -> bool:
        """Checks if the scraped text indicates a bot protection wall (Cloudflare, etc.)"""
        text_lower = text.lower()
        bot_phrases = [
            "verify you are human",
            "attention required! | cloudflare",
            "cloudflare, inc.",
            "please stand by, while we are checking your browser",
            "enable javascript to view the page",
            "pardon our interruption",
            "we want to make sure it is actually you we are dealing with",
            "are you a robot",
            "checking your browser before accessing",
            "one more step",
            "to continue, please click the box below",
            "security by perimeterx",
            "incapsula incident id",
            "automated requests",
            "distil networks"
        ]
        return any(phrase in text_lower for phrase in bot_phrases)

    async def scrape_job_description(self, url: str) -> str:
        logger.info(f"Attempting to scrape {url} via Playwright...")
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
            
        cleaned_text = clean_html_to_text(raw_html, max_chars=4500)
        
        # 1. Quick regex check for bot protection
        if self._is_bot_protected(cleaned_text):
            logger.warning("Bot protection detected by Playwright. Attempting Jina Reader API fallback...")
            import requests
            try:
                resp = requests.get(f"https://r.jina.ai/{url}", timeout=15)
                if resp.status_code == 200 and not self._is_bot_protected(resp.text):
                    logger.info("Jina API fallback successful!")
                    cleaned_text = resp.text[:4500]
                else:
                    raise ValueError("Anti-bot protection active.")
            except Exception as jina_err:
                logger.error(f"Jina fallback failed: {jina_err}")
                raise ValueError(
                    "❌ Anti-Bot Protection Detected! I couldn't read the job description because the site blocked me. "
                    "Please copy and paste the raw text of the job description into the chat instead of sending the URL."
                )

        # 2. LLM Validation to ensure it's a real job description and not a redirect/generic page
        if not self._validate_job_description(cleaned_text):
            logger.warning("LLM Validation failed: The scraped text does not look like a job description.")
            raise ValueError(
                "❌ The scraped page does not appear to contain a valid job description. "
                "The site might have redirected me to the homepage, a list of jobs, or a security check. "
                "Please copy and paste the raw text of the job description instead of using the URL!"
            )
            
        return cleaned_text

    def _validate_job_description(self, text: str) -> bool:
        """Uses an LLM to quickly verify if the scraped text is an actual job description."""
        prompt = f"""
Analyze the following scraped text from a webpage.
Determine if it contains a specific, distinct job description (e.g. mentions a specific role, responsibilities, requirements).
If the text is just a generic company homepage, a list of random jobs, or a security/captcha page, it is invalid.

If it is a valid job description, reply EXACTLY with "YES".
If it is invalid, reply EXACTLY with "NO".

Scraped Text:
{text[:2000]}
"""
        try:
            response = generate_content_with_failover(prompt_text=prompt)
            return "YES" in response.text.strip().upper()
        except Exception as e:
            logger.error(f"Validation LLM failed: {e}. Defaulting to assuming it's valid.")
            return True

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
        company_name = candidate_data.get('target_company', '').strip()
        safe_company_name = "".join([c for c in company_name if c.isalnum() or c.isspace()]).replace(" ", "_").lower()
        if not safe_company_name:
            safe_company_name = f"company_{uuid.uuid4().hex[:8]}"
            
        pdf_filename = f"{safe_company_name}_cover_letter.pdf"
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

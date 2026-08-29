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
    <title>Cover Letter - {{ candidate.name | default('Charles Were Angoye') }}</title>
    <style>
        @page { size: A4; margin: 22mm 22mm; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: #2D3748;
            margin: 0;
            padding: 0;
        }
        .header {
            border-bottom: 2px solid {{ dynamic_color | default('#0F52BA') }};
            padding-bottom: 14px;
            margin-bottom: 24px;
        }
        h1 {
            font-size: 18pt;
            font-weight: 800;
            color: #1A202C;
            margin: 0 0 6px 0;
            text-transform: uppercase;
            letter-spacing: -0.5px;
        }
        .contact {
            font-size: 9pt;
            color: #718096;
            font-weight: 500;
            line-height: 1.5;
        }
        .contact a {
            color: #2D3748;
            text-decoration: none;
            font-weight: 600;
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
            {{ candidate.location | default('Kigali, Rwanda / Nairobi, Kenya (GMT+2 / EAT)') }} &bull; {{ candidate.phone | default('KE: +254 719 403 678 | RW: +250 795 589 824') }}<br>
            {{ candidate.email | default('charleswereangoye@gmail.com') }} &bull; <a href="https://{{ candidate.portfolio | default('charleswereangoye.dev') }}" target="_blank">{{ candidate.portfolio | default('charleswereangoye.dev') }}</a> &bull; <a href="https://{{ candidate.github | default('github.com/charleswereangoye') }}" target="_blank">{{ candidate.github | default('github.com/charleswereangoye') }}</a>
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
        
        company = candidate_data.get("target_company") or "Hiring Team"
        portfolio_url = candidate_data.get("portfolio", "charleswereangoye.dev")
        skills_str = ", ".join(candidate_data.get("skills", []))

        prompt = f"""
You are Charles Were Angoye, a passionate, pragmatic Full-Stack & Backend Software Engineer writing a cover letter to {company}.
Write an authentic, highly natural human cover letter that reads like it was written by a real, thoughtful software engineer communicating directly with an engineering manager.

CRITICAL INSTRUCTIONS FOR NATURAL HUMAN WRITING:
1. WRITE IN FLUID, COHESIVE PARAGRAPHS:
   - Absolutely NO bullet points, NO numbered lists, and NO bold pseudo-headers (e.g. do NOT write 'Data Reliability:', 'System Resilience:', or 'My Technical Approach:').
   - Keep the flow conversational, confident, and engaging.
2. SHOW AUTHENTIC CONNECTION & PRACTICAL EXPERIENCE:
   - State the target position naturally in the opening.
   - Explain why the company's product or engineering mission genuinely interests you.
   - Highlight your practical experience: leading backend workflows at Infinity Innovations, designing robust REST APIs in Python/Node.js, building data architectures in PostgreSQL, and containerizing services with Docker.
   - Mention your real projects (like Trajour, InternLink, or Chronos Multi-Agent OS) and invite them to explore your live projects and code on your portfolio website ({portfolio_url}).
3. NO AI CLICHES OR ROBOTIC PHRASES:
   - Avoid generic phrases like 'I am writing with great enthusiasm', 'I am thrilled to apply', 'delve into', 'testament', or 'in today\\'s fast-paced world'.
   - Avoid overly academic jargon or corporate memo speak. Speak peer-to-peer.
4. FORMAT:
   - Address to 'Dear {company} Team,' or 'Dear Hiring Team,'.
   - 3 to 4 well-structured paragraphs.
   - Close with 'Best regards,' followed by '{candidate_data.get("name", "Charles Were Angoye")}'.
5. ABSOLUTELY NO em-dashes (—).

--- CANDIDATE DATA ---
{candidate_data}

--- TARGET JOB DESCRIPTION ---
{job_description}

Write the complete natural cover letter text:
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

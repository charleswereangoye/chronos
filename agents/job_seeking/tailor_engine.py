import os
import asyncio
import uuid
import logging
from playwright.async_api import async_playwright
from colorthief import ColorThief
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

class TailorEngine:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.output_dir = os.path.join(os.path.dirname(__file__), 'output')
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.jinja_env = Environment(loader=FileSystemLoader(self.template_dir))

    async def get_brand_color(self, url: str) -> str:
        """
        Visits the URL, takes a screenshot, extracts the dominant color, and returns the HEX code.
        """
        temp_img = os.path.join(self.output_dir, f"temp_screenshot_{uuid.uuid4().hex}.png")
        fallback_color = "#333333"
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.screenshot(path=temp_img)
                await browser.close()
                
            color_thief = ColorThief(temp_img)
            dominant_color = color_thief.get_color(quality=1)
            # dominant_color is a tuple (r, g, b)
            hex_color = "#{:02x}{:02x}{:02x}".format(dominant_color[0], dominant_color[1], dominant_color[2])
            return hex_color
        except Exception as e:
            logger.error(f"Failed to get brand color from {url}: {e}")
            return fallback_color
        finally:
            if os.path.exists(temp_img):
                os.remove(temp_img)

    def render_html_cv(self, color_hex: str, candidate_data: dict) -> str:
        """
        Injects the HEX code and candidate data into resume_template.html.
        """
        try:
            template = self.jinja_env.get_template('resume_template.html')
            return template.render(dynamic_color=color_hex, candidate=candidate_data)
        except Exception as e:
            logger.error(f"Failed to render HTML CV: {e}")
            raise

    async def generate_pdf(self, html_content: str, output_path: str):
        """
        Renders the final HTML and saves it as a high-resolution, print-ready PDF.
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_content(html_content, wait_until="networkidle")
                await page.pdf(
                    path=output_path, 
                    print_background=True, 
                    format="A4",
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
                )
                await browser.close()
            logger.info(f"Successfully generated PDF at {output_path}")
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise

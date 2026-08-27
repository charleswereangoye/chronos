import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger("JobHTMLCleaner")

def clean_html_to_text(html_content: str, max_chars: int = 5000) -> str:
    """Cleans raw HTML or inner text, removing nav, footer, scripts, and styling noise."""
    if not html_content:
        return ""
        
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove noisy tags
        for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form", "iframe"]):
            element.decompose()
            
        # Target main content containers if present
        main_content = (
            soup.find("main") or 
            soup.find("article") or 
            soup.find(id=re.compile(r"job|description|content|posting", re.I)) or 
            soup.find(class_=re.compile(r"job-description|posting-content|job_description|details", re.I)) or
            soup.body or
            soup
        )
        
        text = main_content.get_text(separator="\n", strip=True)
        # Collapse multiple blank lines
        cleaned_text = re.sub(r"\n{3,}", "\n\n", text)
        return cleaned_text[:max_chars]
    except Exception as e:
        logger.warning(f"Error cleaning HTML with BeautifulSoup: {e}")
        # Simple regex fallback
        no_tags = re.sub(r"<[^>]+>", " ", html_content)
        cleaned = re.sub(r"\s+", " ", no_tags).strip()
        return cleaned[:max_chars]

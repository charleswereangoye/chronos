import os
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)

class ResumeParser:
    def __init__(self, file_path: str = None):
        if file_path is None:
            # Default to assets/base_resume.pdf in root
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            file_path = os.path.join(root_dir, "assets", "base_resume.pdf")
        self.file_path = file_path

    def extract_text(self) -> str:
        """Reads the PDF resume and returns all raw text."""
        if not os.path.exists(self.file_path):
            logger.error(f"Resume not found at {self.file_path}")
            return ""
            
        try:
            reader = PdfReader(self.file_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"Failed to parse resume PDF: {e}")
            return ""

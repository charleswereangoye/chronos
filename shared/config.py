import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GEMINI_API_KEY_1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY_2 = os.getenv("GEMINI_API_KEY_2", GEMINI_API_KEY_1)

PRIMARY_MODEL = "gemini-3.1-flash-lite"
SECONDARY_MODEL = "gemini-3.5-flash-lite"

def get_gemini_client_and_model(attempt=1):
    if attempt == 1:
        return genai.Client(api_key=GEMINI_API_KEY_1) if GEMINI_API_KEY_1 else genai.Client(), PRIMARY_MODEL
    else:
        return genai.Client(api_key=GEMINI_API_KEY_2) if GEMINI_API_KEY_2 else genai.Client(), SECONDARY_MODEL

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
IG_USER_ID = os.getenv("IG_USER_ID")
META_PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
X_USERNAME = os.getenv("X_USERNAME")
X_PASSWORD = os.getenv("X_PASSWORD")

# Using string parsing in case DRY_RUN is in .env, otherwise default to True
DRY_RUN = os.getenv("DRY_RUN", "True").lower() in ("true", "1", "yes")

# Paths
STATE_DIR = BASE_DIR / "agents" / "social_agent" / "state"
TEMPLATES_DIR = BASE_DIR / "agents" / "social_agent" / "templates"
HISTORY_FILE_PATH = STATE_DIR / "history.json"
STATE_FILE_PATH = STATE_DIR / "state.json"
OUTPUT_DIR = STATE_DIR / "output"

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
import random

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GEMINI_API_KEY_1 = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY_2 = os.getenv("GEMINI_API_KEY_2", GEMINI_API_KEY_1)

PRIMARY_MODEL = "gemini-3.1-flash-lite"
SECONDARY_MODEL = "gemini-3.5-flash-lite"

def get_gemini_client_and_model(attempt=None):
    # Map API keys to their designated models
    key_model_pairs = []
    
    # Keys 1 and 2 use PRIMARY_MODEL (gemini-3.1-flash-lite)
    for i in [1, 2]:
        key = os.getenv(f"GEMINI_API_KEY_{i}")
        if key:
            key_model_pairs.append((key, PRIMARY_MODEL))
            
    # Keys 3 and 4 use SECONDARY_MODEL (gemini-3.5-flash-lite)
    for i in [3, 4]:
        key = os.getenv(f"GEMINI_API_KEY_{i}")
        if key:
            key_model_pairs.append((key, SECONDARY_MODEL))
            
    # Fallback to un-numbered GEMINI_API_KEY if no numbered ones exist
    if not key_model_pairs:
        fallback_key = os.getenv("GEMINI_API_KEY")
        if fallback_key:
            key_model_pairs.append((fallback_key, PRIMARY_MODEL))

    # Load Balancing: If no specific attempt is forced, randomly pick a pair
    if attempt is not None and attempt <= len(key_model_pairs) and key_model_pairs:
        # Use specific pair based on attempt index (e.g. attempt=1 -> first available key)
        selected_key, selected_model = key_model_pairs[attempt - 1]
    elif key_model_pairs:
        # True Load Balancing: Randomly select a pair
        selected_key, selected_model = random.choice(key_model_pairs)
    else:
        selected_key, selected_model = None, PRIMARY_MODEL

    client = genai.Client(api_key=selected_key) if selected_key else genai.Client()
    
    return client, selected_model

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
IG_USER_ID = os.getenv("IG_USER_ID")
META_PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
X_USERNAME = os.getenv("X_USERNAME")
X_PASSWORD = os.getenv("X_PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Using string parsing in case DRY_RUN is in .env, otherwise default to True
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")

# Paths
STATE_DIR = BASE_DIR / "agents" / "social_agent" / "state"
TEMPLATES_DIR = BASE_DIR / "agents" / "social_agent" / "templates"
HISTORY_FILE_PATH = STATE_DIR / "history.json"
STATE_FILE_PATH = STATE_DIR / "state.json"
OUTPUT_DIR = STATE_DIR / "output"

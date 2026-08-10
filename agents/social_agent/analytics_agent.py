import os
import json
# pyrefly: ignore [missing-import]
from twikit import Client
from shared.config import STATE_DIR, STATE_FILE_PATH, X_USERNAME
from shared.logger import get_logger

logger = get_logger("AnalyticsAgent")

class AnalyticsAgent:
    def __init__(self):
        self.analytics_file = STATE_DIR / "analytics.json"
        
    async def fetch_and_save_performance(self) -> dict:
        logger.info("Fetching recent post engagement analytics...")
        
        # Default fallback analytics
        analytics_data = {
            "best_performing_format": "RELATABLE_MEME_TEXT",
            "avg_engagement_rate": 4.2,
            "top_post_id": "12345",
            "format_scores": {
                "RELATABLE_MEME_TEXT": 85,
                "SARCASM_HOT_TAKE": 70,
                "ENGAGEMENT_QUESTION": 90,
                "RAW_FRIEND_ADVICE": 60
            }
        }
        
        try:
            if os.path.exists(self.analytics_file):
                with open(self.analytics_file, "r", encoding="utf-8") as f:
                    analytics_data = json.load(f)
        except Exception as e:
            logger.warning(f"Could not read analytics.json, using defaults: {e}")
            
        try:
            twikit_client = Client('en-US')
            with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
            cookies_list = cookie_data.get("cookies", cookie_data) if isinstance(cookie_data, dict) else cookie_data
            cookies_dict = {c['name']: c['value'] for c in cookies_list}
            twikit_client.set_cookies(cookies_dict)
            
            if X_USERNAME:
                tweets = await twikit_client.search_tweet(f"from:{X_USERNAME}", "Latest", count=5)
                if tweets:
                    likes = sum([int(getattr(t, 'favorite_count', 0) or 0) for t in tweets])
                    retweets = sum([int(getattr(t, 'retweet_count', 0) or 0) for t in tweets])
                    replies = sum([int(getattr(t, 'reply_count', 0) or 0) for t in tweets])
                    views = sum([int(getattr(t, 'view_count', 0) or 0) for t in tweets])
                    logger.info(f"Recent X engagement - Likes: {likes}, RTs: {retweets}, Replies: {replies}, Views: {views}")
                    analytics_data["avg_engagement_rate"] = round((likes + retweets + replies) / len(tweets), 2)
        except Exception as e:
            logger.error(f"Failed to fetch live analytics via Twikit: {e}")
            
        try:
            os.makedirs(os.path.dirname(self.analytics_file), exist_ok=True)
            with open(self.analytics_file, "w", encoding="utf-8") as f:
                json.dump(analytics_data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save analytics.json: {e}")
            
        return analytics_data

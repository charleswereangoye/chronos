import os
import json
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
                "RAW_FRIEND_ADVICE": 60,
                "EXHAUSTED_TRADER": 50,
                "FRIENDLY_MENTOR": 50,
                "GROUNDED_PHILOSOPHER": 50,
                "HYPED_ANALYST": 50,
                "SARCASTIC_REALIST": 50
            }
        }
        
        try:
            if os.path.exists(self.analytics_file):
                with open(self.analytics_file, "r", encoding="utf-8") as f:
                    analytics_data = json.load(f)
        except Exception as e:
            logger.warning(f"Could not read analytics.json, using defaults: {e}")
            
        current_engagement = 0
        try:
            if os.path.exists(STATE_FILE_PATH):
                twikit_client = Client('en-US')
                with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                    cookie_data = json.load(f)
                cookies_list = cookie_data.get("cookies", cookie_data) if isinstance(cookie_data, dict) else cookie_data
                cookies_dict = {c['name']: c['value'] for c in cookies_list if 'name' in c and 'value' in c}
                if cookies_dict:
                    twikit_client.set_cookies(cookies_dict)
                    
                    if X_USERNAME:
                        user = await twikit_client.get_user_by_screen_name(X_USERNAME)
                        tweets = await user.get_tweets("Tweets", count=5)
                        if tweets:
                            likes = sum([int(getattr(t, 'favorite_count', 0) or 0) for t in tweets])
                            retweets = sum([int(getattr(t, 'retweet_count', 0) or 0) for t in tweets])
                            replies = sum([int(getattr(t, 'reply_count', 0) or 0) for t in tweets])
                            views = sum([int(getattr(t, 'view_count', 0) or 0) for t in tweets])
                            logger.info(f"Recent X engagement - Likes: {likes}, RTs: {retweets}, Replies: {replies}, Views: {views}")
                            
                            current_engagement = round((likes + retweets * 2 + replies * 3) / len(tweets), 2)
                            analytics_data["avg_engagement_rate"] = current_engagement
        except Exception as e:
            logger.warning(f"Failed to fetch live analytics via Twikit: {e}. Keeping existing data.")
            
        # A/B Testing Logic: Update scores based on the last used filter
        try:
            from shared.memory import MemoryManager
            mem = MemoryManager()
            history = mem.load_history()
            last_filter = history.get("last_emotional_filter", "None")
            
            if last_filter and last_filter in analytics_data.get("format_scores", {}):
                if current_engagement > 10:
                    analytics_data["format_scores"][last_filter] += 2
                else:
                    analytics_data["format_scores"][last_filter] = max(10, analytics_data["format_scores"][last_filter] - 1)
                    
                best_format = max(analytics_data["format_scores"], key=analytics_data["format_scores"].get)
                analytics_data["best_performing_format"] = best_format
                logger.info(f"Updated A/B scores. Best format is now: {best_format}")
        except Exception as e:
            logger.error(f"Failed to run A/B testing logic: {e}")
            
        try:
            target_dir = os.path.dirname(self.analytics_file)
            os.makedirs(target_dir, exist_ok=True)
            temp_file = os.path.join(target_dir, f".tmp_analytics_{os.getpid()}.json")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(analytics_data, f, indent=4)
            os.replace(temp_file, self.analytics_file)
        except Exception as e:
            logger.error(f"Failed to save analytics.json: {e}")
            
        return analytics_data

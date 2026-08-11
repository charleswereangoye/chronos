import json
import traceback
from twikit import Client
from shared.config import STATE_FILE_PATH, X_USERNAME, get_gemini_client_and_model
from shared.logger import get_logger

logger = get_logger("CommunityAgent")

class CommunityAgent:
    def __init__(self):
        pass

    async def reply_to_mentions(self, persona_profile: dict):
        """
        Reads recent mentions/replies on X and posts automated replies based on the persona.
        """
        logger.info("Community Agent checking for recent mentions...")
        twikit_client = Client('en-US')
        
        try:
            with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
            cookies_list = cookie_data.get("cookies", cookie_data) if isinstance(cookie_data, dict) else cookie_data
            cookies_dict = {c['name']: c['value'] for c in cookies_list}
            twikit_client.set_cookies(cookies_dict)
            
            if not X_USERNAME:
                logger.error("X_USERNAME not set in .env")
                return
                
            # Note: twikit might not have a direct "get_mentions" method easily exposed, 
            # so we'll simulate searching for mentions using the search endpoint
            mentions = await twikit_client.search_tweet(f"@{X_USERNAME}", "Latest", count=5)
            if not mentions:
                logger.info("No recent mentions found to reply to.")
                return
                
            emotional_filter = persona_profile.get("emotional_filter", "FRIENDLY_MENTOR")
            
            for tweet in mentions:
                # Basic check to avoid replying to ourselves
                if getattr(tweet.user, 'screen_name', '') == X_USERNAME:
                    continue
                    
                prompt = f"""
                You are a highly authentic human trader.
                Your current emotional filter is: {emotional_filter}
                Someone just mentioned you on X (Twitter).
                
                User: {getattr(tweet.user, 'screen_name', 'user')}
                Their Tweet: "{tweet.text}"
                
                Generate a short, witty, 1-2 sentence reply to them matching your emotional filter.
                DO NOT use emojis. DO NOT use hashtags. 
                Keep it conversational and sound like a real person.
                """
                
                client, model_name = get_gemini_client_and_model(1)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                reply_text = response.text.strip().replace('"', '')
                
                # In a real app we'd keep track of what we replied to so we don't spam.
                # For this demo, we'll just log what it would have done unless forced to post.
                logger.info(f"Generated reply to @{getattr(tweet.user, 'screen_name', 'user')}: {reply_text}")
                
                # await twikit_client.create_tweet(text=reply_text, reply_to=tweet.id)
                # logger.info("Successfully replied.")
                break # Just demoing with one reply
                
        except Exception as e:
            logger.error(f"Failed to run community agent: {e}")
            traceback.print_exc()

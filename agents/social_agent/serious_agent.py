import json
from shared.config import get_gemini_client_and_model
from shared.logger import get_logger

logger = get_logger("SeriousAgent")

class SeriousAgent:
    def __init__(self):
        pass

    def generate_serious_quote(self, research_data: dict) -> dict:
        logger.info("Generating serious trading quote based on research data...")
        
        prompt = f"""
        You are a highly experienced, disciplined, and professional Forex and Gold (XAUUSD) trader.
        You provide serious, actionable trading wisdom or observations without any emotion or mood swings.
        
        Given the following latest market news, write a serious trading quote for an image post, 
        along with a text post for X, and a caption for Instagram/Facebook.

        LATEST NEWS:
        {research_data.get("macro_news", "Standard volatility.")}

        Your response MUST be valid JSON in this exact format:
        {{
            "image_quote": "A single profound and serious trading observation or piece of advice.",
            "x_post_text": "The text for the X post including hashtags. Keep it under 280 characters.",
            "meta_caption": "The caption for Instagram/Facebook with relevant hashtags."
        }}
        """

        for attempt in range(1, 4):
            try:
                logger.info(f"Generating content using Attempt {attempt}")
                client, model_name = get_gemini_client_and_model(attempt)
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:-3].strip()
                elif text.startswith("```"):
                    text = text[3:-3].strip()
                    
                content = json.loads(text)
                return content
            except Exception as e:
                logger.error(f"Generation attempt {attempt} failed: {e}")
                
        return {
            "image_quote": "Risk management is the only holy grail in trading.",
            "x_post_text": "Risk management is the only holy grail in trading. #Forex #Trading",
            "meta_caption": "Risk management is the only holy grail in trading. Protect your capital at all costs. #ForexTrading #RiskManagement #XAUUSD"
        }

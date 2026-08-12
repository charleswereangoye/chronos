import json
from shared.config import get_gemini_client_and_model
from shared.logger import get_logger

logger = get_logger("NewsAgent")

class NewsAgent:
    def __init__(self):
        pass

    def generate_news_post(self, research_data: dict) -> dict:
        """
        Generates a concise breaking news summary suitable for a social media post,
        given the latest macro news from the ResearchAgent.
        """
        logger.info("Generating breaking news post based on research data...")
        
        macro_news = research_data.get("macro_news", "No recent news available.")
        
        prompt = f"""
        You are a financial news social media manager for a Gold (XAUUSD) and Forex trader.
        Your goal is to recreate a 'Red Folder' economic calendar alert (similar to Forex Factory or MyFxBook).
        Given the following latest market news, identify any major high-impact events (e.g., CPI, NFP, FOMC, rate decisions).
        
        For the image text, simply state the exact name of the high-impact event (e.g., "Core CPI m/m" or "FOMC Statement") as it would appear on Forex Factory.
        Also write a caption for the post itself outlining the potential impact on Gold or the USD.

        LATEST NEWS:
        {macro_news}

        Your response MUST be valid JSON in this exact format:
        {{
            "news_content": "The exact short event name (e.g. 'Core CPI m/m', 'Non-Farm Employment Change').",
            "meta_caption": "The caption for all social media including hashtags. MUST be under 280 characters."
        }}
        """

        for attempt in range(1, 4):
            try:
                logger.info(f"Generating news content using Attempt {attempt}")
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
                logger.error(f"News generation attempt {attempt} failed: {e}")
                
        return {
            "news_content": "Major market updates are happening today. Stay tuned for details.",
            "x_post_text": "Major market updates are happening today. #news #markets",
            "meta_caption": "Major market updates are happening today. 📊📉 #news #finance #markets"
        }

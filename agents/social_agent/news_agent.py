from shared.logger import get_logger
from shared.llm import generate_json_with_failover

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

        fallback = {
            "news_content": "High Impact Market Update",
            "x_post_text": "High Impact Market Update. Keep risk tightly managed today. #Forex #Gold #Economy",
            "meta_caption": "High impact market updates today. Protect your capital and manage your risk. 📊📉 #news #finance #markets"
        }

        try:
            content = generate_json_with_failover(
                prompt_text=prompt,
                max_attempts=3,
                default_fallback=fallback
            )
            if "x_post_text" not in content and "news_content" in content:
                content["x_post_text"] = f"{content['news_content']} #news #markets"
            return content
        except Exception as e:
            logger.error(f"News generation failed: {e}")
            return fallback

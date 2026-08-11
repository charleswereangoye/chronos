import feedparser
from shared.config import get_gemini_client_and_model
from shared.logger import get_logger

logger = get_logger("MonitorAgent")

class MonitorAgent:
    def __init__(self):
        pass

    def check_for_breaking_news(self) -> dict:
        """
        Scans RSS feeds for massive breaking news in the last 1-2 hours.
        Returns {"is_breaking": True/False, "event_summary": "..."}
        """
        logger.info("Monitor Agent scanning for breaking market events...")
        rss_feeds = [
            "https://www.dailyforex.com/rss/forex-news",
            "https://finance.yahoo.com/news/rssindex"
        ]
        news_snippets = []
        try:
            for url in rss_feeds:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]: # Top 5 latest
                    title = getattr(entry, 'title', '')
                    summary = getattr(entry, 'summary', '')
                    if title or summary:
                        news_snippets.append(f"Title: {title}\nSummary: {summary}")
        except Exception as e:
            logger.error(f"Monitor RSS fetch failed: {e}")
            return {"is_breaking": False, "event_summary": ""}
            
        combined_news = "\n\n".join(news_snippets)
        if not combined_news:
            return {"is_breaking": False, "event_summary": ""}
            
        prompt = f"""
        You are a financial market monitor. Review the following recent news snippets.
        Determine if there is a MASSIVE BREAKING EVENT occurring right now (e.g., unexpected interest rate hike, sudden stock market crash, huge crypto hack, unexpected war escalation).
        Standard daily volatility or regular earnings reports do NOT count as breaking.
        
        News:
        {combined_news}
        
        If there is a breaking event, output a JSON object: {{"is_breaking": true, "event_summary": "A 1 sentence summary of the shocking event"}}
        If it's just normal market news, output: {{"is_breaking": false, "event_summary": ""}}
        
        Output ONLY valid JSON.
        """
        
        try:
            client, model_name = get_gemini_client_and_model(1)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            import json
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(raw_text)
            if result.get("is_breaking"):
                logger.warning(f"BREAKING NEWS DETECTED: {result.get('event_summary')}")
            else:
                logger.info("No breaking news detected.")
            return result
        except Exception as e:
            logger.error(f"Monitor analysis failed: {e}")
            return {"is_breaking": False, "event_summary": ""}

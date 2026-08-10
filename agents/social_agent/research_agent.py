import json
import traceback
from google import genai
from google.genai import types
from twikit import Client
import feedparser

from shared.config import get_gemini_client_and_model, STATE_FILE_PATH
from shared.logger import get_logger

logger = get_logger("ResearchAgent")

def generate_content_with_failover(prompt_text, config=None):
    for attempt in [1, 2]:
        try:
            client, model_name = get_gemini_client_and_model(attempt)
            logger.info(f"Generating content using Attempt {attempt}: {model_name}")
            kwargs = {"model": model_name, "contents": prompt_text}
            if config:
                kwargs["config"] = config
            response = client.models.generate_content(**kwargs)
            return response
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed with error: {e}")
            if attempt == 2:
                logger.error("All Gemini model/key attempts exhausted.")
                raise e

class ResearchAgent:
    def __init__(self):
        pass

    def fetch_rss_market_news(self) -> str:
        logger.info("Fetching RSS market news...")
        rss_feeds = [
            "https://www.dailyforex.com/rss/forex-news",
            "https://www.myfxbook.com/rss/forex-news",
            "https://finance.yahoo.com/news/rssindex"
        ]
        news_snippets = []
        try:
            for url in rss_feeds:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    title = getattr(entry, 'title', '')
                    summary = getattr(entry, 'summary', '')
                    if title or summary:
                        news_snippets.append(f"Title: {title}\nSummary: {summary}")
        except Exception as e:
            logger.error(f"RSS fetch failed: {e}")
        return "\n\n".join(news_snippets)
        
    async def fetch_daily_research(self) -> dict:
        logger.info("Fetching real-time market data...")
        
        macro_news = "Default: Markets are experiencing standard volatility."
        try:
            logger.info("Querying Gemini for Live Macro News using RSS snippets...")
            snippets = self.fetch_rss_market_news()
            
            prompt = f"Here is the latest financial news from reliable RSS feeds:\n{snippets}\n\nSummarize the high-impact Forex and Gold (XAUUSD) events, interest rate shifts, CPI, NFP, or central bank announcements from the past 24 hours in 2-3 sentences."
            
            response = generate_content_with_failover(prompt_text=prompt)
            macro_news = response.text.strip()
        except Exception as e:
            logger.error(f"Failed to fetch macro news: {e}")
            
        retail_sentiment = "Default: Retail traders are mixed."
        try:
            logger.info("Querying Twikit for Retail Sentiment...")
            twikit_client = Client('en-US')
            with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
            cookies_list = cookie_data.get("cookies", cookie_data) if isinstance(cookie_data, dict) else cookie_data
            cookies_dict = {c['name']: c['value'] for c in cookies_list}
            twikit_client.set_cookies(cookies_dict)
            
            tweets = await twikit_client.search_tweet("(#XAUUSD OR #Forex) min_faves:10", "Latest", count=10)
            if tweets:
                texts = [tweet.text for tweet in tweets[:5]]
                sentiment_prompt = f"Analyze these recent tweets and summarize the current retail trader sentiment (panic, hype, greed, frustration) in 1 sentence: {texts}"
                resp = generate_content_with_failover(prompt_text=sentiment_prompt)
                retail_sentiment = resp.text.strip()
            else:
                retail_sentiment = "Default: No recent tweets found for sentiment analysis."
        except Exception as e:
            logger.error(f"Failed to fetch retail sentiment: {e}")
            
        return {
            "macro_news": macro_news,
            "retail_sentiment": retail_sentiment,
            "key_keywords": ["Gold", "Risk Management", "FOMC", "Volatility"]
        }

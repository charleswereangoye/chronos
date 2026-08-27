import json
import asyncio
import feedparser
from twikit import Client

from shared.config import STATE_FILE_PATH
from shared.logger import get_logger
from shared.llm import generate_content_with_failover

logger = get_logger("ResearchAgent")

class ResearchAgent:
    def __init__(self):
        pass

    def _sync_fetch_rss_market_news(self) -> str:
        logger.info("Fetching RSS market news...")
        rss_feeds = [
            "https://www.dailyforex.com/rss/forex-news",
            "https://www.myfxbook.com/rss/forex-news",
            "https://finance.yahoo.com/news/rssindex"
        ]
        news_snippets = []
        try:
            # Set User-Agent to prevent 403 Forbidden / Cloudflare blocks
            feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            for url in rss_feeds:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:5]:
                        title = getattr(entry, 'title', '')
                        summary = getattr(entry, 'summary', '')
                        if title or summary:
                            news_snippets.append(f"Title: {title}\nSummary: {summary}")
                except Exception as feed_err:
                    logger.warning(f"Error parsing RSS feed {url}: {feed_err}")
        except Exception as e:
            logger.error(f"RSS fetch failed: {e}")
        return "\n\n".join(news_snippets)

    async def fetch_rss_market_news(self) -> str:
        return await asyncio.to_thread(self._sync_fetch_rss_market_news)
        
    async def fetch_daily_research(self) -> dict:
        logger.info("Fetching real-time market data...")
        
        macro_news = "Default: Markets are experiencing standard volatility."
        try:
            logger.info("Querying Gemini for Live Macro News using RSS snippets...")
            snippets = await self.fetch_rss_market_news()
            
            if snippets.strip():
                prompt = (
                    f"Here is the latest financial news from reliable RSS feeds:\n{snippets}\n\n"
                    "Summarize the high-impact Forex and Gold (XAUUSD) events, interest rate shifts, "
                    "CPI, NFP, or central bank announcements from the past 24 hours in 2-3 sentences."
                )
                response = generate_content_with_failover(prompt_text=prompt)
                macro_news = response.text.strip()
            else:
                logger.warning("No RSS snippets available, using fallback macro news.")
        except Exception as e:
            logger.error(f"Failed to fetch macro news: {e}")
            
        retail_sentiment = "Default: Retail traders are cautious with mixed positioning."
        try:
            import os
            if os.path.exists(STATE_FILE_PATH):
                logger.info("Querying Twikit for Retail Sentiment...")
                twikit_client = Client('en-US')
                with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                    cookie_data = json.load(f)
                cookies_list = cookie_data.get("cookies", cookie_data) if isinstance(cookie_data, dict) else cookie_data
                cookies_dict = {c['name']: c['value'] for c in cookies_list if 'name' in c and 'value' in c}
                if cookies_dict:
                    twikit_client.set_cookies(cookies_dict)
                    tweets = await twikit_client.search_tweet("(#XAUUSD OR #Forex) min_faves:10", "Latest", count=10)
                    if tweets:
                        texts = [tweet.text for tweet in tweets[:5]]
                        sentiment_prompt = f"Analyze these recent tweets and summarize the current retail trader sentiment (panic, hype, greed, frustration) in 1 sentence: {texts}"
                        resp = generate_content_with_failover(prompt_text=sentiment_prompt)
                        retail_sentiment = resp.text.strip()
            else:
                logger.info("No Twikit state file found. Using default sentiment.")
        except Exception as e:
            logger.warning(f"Failed to fetch retail sentiment from Twitter/Twikit: {e}. Falling back safely.")
            
        return {
            "macro_news": macro_news,
            "retail_sentiment": retail_sentiment,
            "key_keywords": ["Gold", "Risk Management", "FOMC", "Volatility"]
        }

import logging
from typing import Dict, Any, Optional, List
import requests
import feedparser
from shared.base_agent import BaseAgent, AgentResult, AgentStatus

logger = logging.getLogger("ForexMonitor")

class ForexMonitor(BaseAgent):
    """
    Monitors economic calendar announcements, high-impact red-folder events, 
    and macroeconomic news feeds to feed context into the orchestrator.
    """
    def __init__(self):
        super().__init__(name="ForexMonitor")

    def fetch_forexfactory_calendar(self) -> List[Dict[str, Any]]:
        """
        Parses ForexFactory weekly economic calendar RSS.
        """
        calendar_events = []
        try:
            feed_url = "https://www.forexfactory.com/calendar.xml"
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                calendar_events.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "published": entry.get("published", "")
                })
        except Exception as e:
            self.logger.warning(f"Failed to parse ForexFactory calendar: {e}")
        return calendar_events

    def get_market_sessions(self) -> Dict[str, str]:
        """
        Returns current session volatility context.
        """
        return {
            "Asian_Session": "00:00 - 09:00 UTC (Tokyo/Sydney)",
            "London_Session": "08:00 - 17:00 UTC (High Volatility EUR/GBP)",
            "New_York_Session": "13:00 - 22:00 UTC (Peak Volatility USD/Gold)"
        }

    async def execute(self, payload: Optional[Dict[str, Any]] = None) -> AgentResult:
        events = self.fetch_forexfactory_calendar()
        sessions = self.get_market_sessions()

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "calendar_events": events,
                "market_sessions": sessions,
                "has_high_impact_news": len(events) > 0
            }
        )

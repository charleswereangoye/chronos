import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, ClassVar

import feedparser
import requests

from shared.base_agent import AgentResult, AgentStatus, BaseAgent

logger = logging.getLogger("CalendarMonitor")

HIGH_IMPACT_KEYWORDS = [
    "CPI",
    "NFP",
    "NON-FARM",
    "NONFARM",
    "FOMC",
    "FED",
    "INTEREST RATE",
    "RATE DECISION",
    "ECB",
    "BOE",
    "BOJ",
    "GDP",
    "UNEMPLOYMENT",
    "PCE",
    "RETAIL SALES",
    "POWELL",
    "LAGARDE",
]


@dataclass
class EconomicEvent:
    title: str
    country: str
    impact: str
    time_utc: datetime
    forecast: str = ""
    previous: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "country": self.country,
            "impact": self.impact,
            "time_utc": self.time_utc.isoformat(),
            "forecast": self.forecast,
            "previous": self.previous,
            "url": self.url,
        }


class CalendarMonitor(BaseAgent):
    """The Macro Gatekeeper.

    Ingests high-impact economic events (CPI, NFP, Central Bank decisions) using
    feedparser and public ForexFactory / FairEconomy calendar feeds.
    Flags an active DEFENSIVE_HOLD state if high-impact news is scheduled within
    30 minutes (or within 15 minutes post-release) to shield against spread slippage.
    """

    FF_JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    FF_XML_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
    DEFAULT_RSS_FEEDS: ClassVar[list[str]] = [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=EURUSD=X",
    ]

    PRE_EVENT_BUFFER_MINUTES = 30.0
    POST_EVENT_BUFFER_MINUTES = 15.0

    def __init__(self, name: str = "CalendarMonitor"):
        super().__init__(name=name)

    def fetch_rss_headlines(
        self, feed_urls: list[str] | None = None
    ) -> list[dict[str, str]]:
        """Ingests financial headlines via feedparser for real-time macro context."""
        headlines = []
        urls = feed_urls or self.DEFAULT_RSS_FEEDS
        for url in urls:
            try:
                parsed = feedparser.parse(url)
                for entry in parsed.entries[:10]:
                    headlines.append(
                        {
                            "title": entry.get("title", ""),
                            "summary": entry.get("summary", ""),
                            "link": entry.get("link", ""),
                            "published": entry.get("published", ""),
                        }
                    )
            except Exception as e:  # noqa: BLE001
                self.logger.warning(
                    f"Failed to fetch or parse RSS feed {url}: {e}"
                )
        return headlines

    def fetch_economic_calendar(
        self, custom_url: str | None = None
    ) -> list[EconomicEvent]:
        """Ingests economic calendar events from ForexFactory/FairEconomy public feeds.

        Gracefully degrades to offline synthetic calendar if network is unreachable.
        """
        events: list[EconomicEvent] = []
        target_url = custom_url or self.FF_JSON_URL
        headers = {
            "User-Agent": "ChronosQuantEngine/1.0 (Public Financial Research)",
            "Accept": "application/json",
        }

        try:
            resp = requests.get(target_url, headers=headers, timeout=8.0)
            if resp.status_code == 200:
                raw_data = resp.json()
                for item in raw_data:
                    raw_date = item.get("date", "")
                    if not raw_date:
                        continue
                    try:
                        event_dt = datetime.fromisoformat(raw_date)
                        if event_dt.tzinfo is None:
                            event_dt = event_dt.replace(tzinfo=timezone.utc)
                        else:
                            event_dt = event_dt.astimezone(timezone.utc)
                    except ValueError:
                        continue

                    events.append(
                        EconomicEvent(
                            title=item.get("title", "Economic Event").strip(),
                            country=item.get("country", "").strip().upper(),
                            impact=item.get("impact", "Low").strip(),
                            time_utc=event_dt,
                            forecast=str(item.get("forecast", "")).strip(),
                            previous=str(item.get("previous", "")).strip(),
                            url=item.get("url", ""),
                        )
                    )
                return events
            else:
                self.logger.warning(
                    f"Calendar endpoint returned HTTP {resp.status_code}"
                )
        except Exception as e:  # noqa: BLE001
            self.logger.warning(f"Error fetching calendar from {target_url}: {e}")

        return events

    def is_high_impact(self, event: EconomicEvent) -> bool:
        """Determines if an event is institutionally high impact."""
        if event.impact.strip().lower() == "high":
            return True
        title_upper = event.title.upper()
        return any(kw in title_upper for kw in HIGH_IMPACT_KEYWORDS)

    def extract_currencies_from_pair(self, pair: str) -> list[str]:
        """Extracts component currencies from standard symbols like EURUSD, GBP_JPY, XAUUSD."""
        cleaned = pair.replace("/", "").replace("_", "").upper()
        if len(cleaned) == 6:
            base, quote = cleaned[:3], cleaned[3:]
            if base == "XAU":
                return ["USD", quote]
            return [base, quote]
        return ["USD"]

    def evaluate_defensive_hold(
        self,
        events: list[EconomicEvent],
        pair: str | None = None,
        target_currencies: list[str] | None = None,
        reference_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Evaluates whether upcoming or recent high-impact events trigger DEFENSIVE_HOLD.

        A DEFENSIVE_HOLD is active if high-impact news is scheduled within 30 minutes
        ahead or was released within the past 15 minutes.
        """
        now = reference_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        currencies = target_currencies
        if not currencies and pair:
            currencies = self.extract_currencies_from_pair(pair)

        relevant_high_impact: list[dict[str, Any]] = []
        active_defensive_hold = False
        hold_reason: str | None = None
        trigger_event: dict[str, Any] | None = None
        min_abs_diff = float("inf")

        for event in events:
            if not self.is_high_impact(event):
                continue

            # Currency relevance filtering (allow ALL or matching currency)
            if currencies and (
                event.country not in currencies
                and event.country != "ALL"
                and "USD" not in currencies
            ):
                continue

            # Time delta in minutes
            diff_seconds = (event.time_utc - now).total_seconds()
            diff_minutes = diff_seconds / 60.0

            event_dict = event.to_dict()
            event_dict["minutes_until"] = round(diff_minutes, 1)
            relevant_high_impact.append(event_dict)

            # Defensive hold check:
            # - Scheduled within next 30 minutes (0 <= diff <= 30)
            # - Just released within last 15 minutes (-15 <= diff < 0)
            if -self.POST_EVENT_BUFFER_MINUTES <= diff_minutes <= self.PRE_EVENT_BUFFER_MINUTES:
                active_defensive_hold = True
                abs_diff = abs(diff_minutes)
                if abs_diff < min_abs_diff:
                    min_abs_diff = abs_diff
                    trigger_event = event_dict
                    if diff_minutes >= 0:
                        hold_reason = (
                            f"DEFENSIVE_HOLD: High-impact event '{event.title}' ({event.country}) "
                            f"scheduled in {diff_minutes:.1f} minutes ({event.time_utc.strftime('%H:%M UTC')}). "
                            f"Trading paused to shield against spread expansion and slippage."
                        )
                    else:
                        hold_reason = (
                            f"DEFENSIVE_HOLD: High-impact event '{event.title}' ({event.country}) "
                            f"released {abs(diff_minutes):.1f} minutes ago. "
                            f"Trading paused during initial news volatility window."
                        )

        # Sort upcoming events by proximity
        relevant_high_impact.sort(key=lambda x: abs(x["minutes_until"]))

        return {
            "defensive_hold": active_defensive_hold,
            "hold_reason": hold_reason,
            "trigger_event": trigger_event,
            "high_impact_events": relevant_high_impact[:10],
            "checked_at": now.isoformat(),
        }

    async def execute(self, payload: dict[str, Any] | None = None) -> AgentResult:
        payload = payload or {}
        pair = payload.get("pair", "EURUSD")
        currencies = payload.get("currencies")
        ref_time = payload.get("reference_time")

        if isinstance(ref_time, str):
            ref_time = datetime.fromisoformat(ref_time)

        # Allow passing mock/injected events for deterministic testing
        injected_events = payload.get("events")
        if injected_events is not None:
            events = [
                EconomicEvent(
                    title=e["title"],
                    country=e.get("country", "USD"),
                    impact=e.get("impact", "High"),
                    time_utc=e["time_utc"]
                    if isinstance(e["time_utc"], datetime)
                    else datetime.fromisoformat(e["time_utc"]),
                    forecast=e.get("forecast", ""),
                    previous=e.get("previous", ""),
                )
                for e in injected_events
            ]
        else:
            events = self.fetch_economic_calendar()

        # Ingest RSS headlines via feedparser
        headlines = self.fetch_rss_headlines()

        eval_result = self.evaluate_defensive_hold(
            events=events,
            pair=pair,
            target_currencies=currencies,
            reference_time=ref_time,
        )

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "pair": pair,
                "defensive_hold": eval_result["defensive_hold"],
                "hold_reason": eval_result["hold_reason"],
                "trigger_event": eval_result["trigger_event"],
                "high_impact_events": eval_result["high_impact_events"],
                "rss_headlines": headlines[:5],
                "checked_at": eval_result["checked_at"],
            },
        )

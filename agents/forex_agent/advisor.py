import logging
from typing import Dict, Any, Optional
from shared.base_agent import BaseAgent, AgentResult, AgentStatus
from shared.llm import generate_content_with_failover
from agents.forex_agent.monitor import ForexMonitor

logger = logging.getLogger("ForexAdvisor")

class ForexAdvisor(BaseAgent):
    """
    Analyzes technical market setups, price action sentiment, 
    and economic calendars to produce disciplined trading advisories.
    """
    def __init__(self):
        super().__init__(name="ForexAdvisor")
        self.monitor = ForexMonitor()

    async def generate_market_advisory(self, pair: str = "XAUUSD", timeframe: str = "4H") -> str:
        """
        Synthesizes macro data and technical bias for a specified currency pair / asset.
        """
        monitor_res = await self.monitor.run()
        calendar_events = monitor_res.data.get("calendar_events", [])

        prompt = f"""
You are a Senior Risk Manager and Institutional Market Analyst.
Generate a structured, professional market advisory for {pair} on the {timeframe} timeframe.

Context / Upcoming High Impact News:
{calendar_events[:5]}

STRICT RULES:
1. Focus on risk management, liquidity zones, key psychological levels, and volatility precautions.
2. Include a clear disclaimer: 'Not financial advice. Trade at your own risk.'
3. Provide concrete talking points:
   - **Market Bias**: [Bullish / Bearish / Range-Bound Consolidation]
   - **Key Price Levels**: Support & Resistance zones to monitor
   - **Risk Management Rule**: Mandatory stop loss, maximum risk per trade (1-2%)
   - **Upcoming Economic Catalyst**: Potential event volatility

Format with clean, professional Markdown.
"""
        response = generate_content_with_failover(prompt_text=prompt)
        return response.text.strip()

    async def execute(self, payload: Optional[Dict[str, Any]] = None) -> AgentResult:
        payload = payload or {}
        pair = payload.get("pair", "XAUUSD")
        timeframe = payload.get("timeframe", "4H")
        
        advisory_text = await self.generate_market_advisory(pair=pair, timeframe=timeframe)
        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "pair": pair,
                "timeframe": timeframe,
                "advisory": advisory_text
            }
        )

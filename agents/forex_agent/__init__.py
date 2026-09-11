"""Forex Agent Module for Chronos Multi-Agent Framework.

Provides macro economic calendar monitoring, deterministic regime analysis,
mathematical risk guarding, Gemini context synthesis, and pipeline coordination.
"""

from agents.forex_agent.advisor import ForexAdvisor
from agents.forex_agent.calendar_monitor import CalendarMonitor, EconomicEvent
from agents.forex_agent.forex_coordinator import ForexCoordinator
from agents.forex_agent.regime_analyzer import Candle, RegimeAnalyzer, RegimeSnapshot
from agents.forex_agent.risk_guard import RiskGuard, RiskValidationResult

__all__ = [
    "CalendarMonitor",
    "Candle",
    "EconomicEvent",
    "ForexAdvisor",
    "ForexCoordinator",
    "RegimeAnalyzer",
    "RegimeSnapshot",
    "RiskGuard",
    "RiskValidationResult",
]

import logging
from typing import Any

from agents.forex_agent.advisor import ForexAdvisor
from agents.forex_agent.calendar_monitor import CalendarMonitor
from agents.forex_agent.regime_analyzer import RegimeAnalyzer
from agents.forex_agent.risk_guard import RiskGuard
from shared.base_agent import AgentResult, AgentStatus, BaseAgent

logger = logging.getLogger("ForexCoordinator")


class ForexCoordinator(BaseAgent):
    """Forex Pipeline Master Coordinator.

    Orchestrates the complete quantitative analysis pipeline:
    1. Macro Gatekeeper (CalendarMonitor): Ingests high-impact news & evaluates DEFENSIVE_HOLD.
    2. Deterministic State (RegimeAnalyzer): Calculates 1H/4H trend & market sessions.
    3. Gemini Synthesis (ForexAdvisor): Synthesizes technicals + macro into a structured setup.
    4. Mathematical Safety (RiskGuard): Strictly enforces 1% account risk & 1:2 R:R constraints.
    5. Produces standardized AgentResult ready for Human-In-The-Loop (HITL) Telegram card review.
    """

    def __init__(self, name: str = "ForexCoordinator"):
        super().__init__(name=name)
        self.calendar_monitor = CalendarMonitor()
        self.regime_analyzer = RegimeAnalyzer()
        self.advisor = ForexAdvisor()
        self.risk_guard = RiskGuard()

    async def analyze_market(
        self,
        pair: str = "EURUSD",
        account_balance: float = 10000.0,
        reference_time: Any | None = None,
        custom_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Runs the complete 4-step pipeline and produces an institutional trade setup."""
        pair = pair.upper().strip()
        custom_payload = custom_payload or {}

        # Step 1: Macro Gatekeeper
        calendar_payload = {
            "pair": pair,
            "reference_time": reference_time,
            **custom_payload.get("calendar", {}),
        }
        calendar_res = await self.calendar_monitor.run(calendar_payload)
        calendar_data = calendar_res.data if calendar_res.is_success else {}
        defensive_hold = calendar_data.get("defensive_hold", False)
        hold_reason = calendar_data.get("hold_reason")

        # Step 2: Deterministic Regime Analysis
        regime_payload = {
            "pair": pair,
            "reference_time": reference_time,
            **custom_payload.get("regime", {}),
        }
        regime_res = await self.regime_analyzer.run(regime_payload)
        regime_data = regime_res.data if regime_res.is_success else {}

        # Step 3: Advisor Synthesis
        advisor_payload = {
            "pair": pair,
            "calendar_data": calendar_data,
            "regime_data": regime_data,
            **custom_payload.get("advisor", {}),
        }
        advisor_res = await self.advisor.run(advisor_payload)
        briefing = advisor_res.data.get("briefing", {}) if advisor_res.is_success else {}

        market_bias = briefing.get("market_bias", "NEUTRAL")
        key_levels = briefing.get("key_levels", {})
        thesis = briefing.get("thesis", "No thesis generated.")

        entry_price = float(key_levels.get("entry_price", regime_data.get("current_price", 1.0)))
        stop_loss = float(key_levels.get("stop_loss", entry_price * 0.99))
        target_price = float(key_levels.get("target", entry_price * 1.02))
        invalidation = float(key_levels.get("invalidation", stop_loss))
        entry_range = key_levels.get("entry_range", f"{entry_price}")

        # Step 4: Mathematical Safety Bounds via RiskGuard
        direction = "BUY" if market_bias == "BULLISH" else ("SELL" if market_bias == "BEARISH" else "NEUTRAL")
        risk_res = await self.risk_guard.run(
            {
                "pair": pair,
                "direction": direction,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "target_price": target_price,
                "account_balance": account_balance,
            }
        )
        risk_data = risk_res.data.get("validation", {}) if risk_res.is_success else {}
        is_risk_approved = risk_data.get("is_approved", False)

        # Pipeline Decision Logic
        if defensive_hold:
            trade_action = "DEFENSIVE_HOLD"
            summary_status = "HOLD: High-impact macro news scheduled within 30 minutes."
        elif not is_risk_approved:
            trade_action = "REJECTED_BY_RISK_GUARD"
            reasons = "; ".join(risk_data.get("rejection_reasons", ["Risk bounds violated"]))
            summary_status = f"REJECTED: {reasons}"
        elif market_bias == "NEUTRAL":
            trade_action = "NEUTRAL_STANDBY"
            summary_status = "STANDBY: Market is in horizontal consolidation; awaiting directional break."
        else:
            trade_action = "READY_FOR_HITL_REVIEW"
            summary_status = "VALIDATED: Setup fulfills 1% risk ceiling and >= 1:2 R:R institutional bounds."

        return {
            "pair": pair,
            "trade_action": trade_action,
            "summary_status": summary_status,
            "defensive_hold": defensive_hold,
            "hold_reason": hold_reason,
            "market_bias": market_bias,
            "current_price": regime_data.get("current_price", entry_price),
            "key_levels": {
                "entry_range": entry_range,
                "entry_price": entry_price,
                "invalidation": invalidation,
                "stop_loss": stop_loss,
                "target": target_price,
            },
            "risk_evaluation": risk_data,
            "thesis": thesis,
            "sessions": regime_data.get("market_sessions", {}),
            "regime_1h": regime_data.get("regime_1h", {}),
            "regime_4h": regime_data.get("regime_4h", {}),
            "high_impact_events": calendar_data.get("high_impact_events", []),
        }

    async def execute(self, payload: dict[str, Any] | None = None) -> AgentResult:
        payload = payload or {}
        pair = payload.get("pair", "EURUSD")
        balance = float(payload.get("account_balance", payload.get("balance", 10000.0)))
        ref_time = payload.get("reference_time")

        setup_data = await self.analyze_market(
            pair=pair,
            account_balance=balance,
            reference_time=ref_time,
            custom_payload=payload,
        )

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data=setup_data,
        )

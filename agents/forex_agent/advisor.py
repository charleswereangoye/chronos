import logging
from typing import Any

from shared.base_agent import AgentResult, AgentStatus, BaseAgent
from shared.llm import generate_json_with_failover

logger = logging.getLogger("ForexAdvisor")


class ForexAdvisor(BaseAgent):
    """Gemini Context Synthesis Engine.

    Ingests the output of the Macro Calendar Monitor and Regime Analyzer.
    Uses Gemini (with zero-cost failover) to synthesize macro headlines,
    session liquidity, and multi-timeframe price structure into a structured
    institutional trade briefing.
    """

    def __init__(self, name: str = "ForexAdvisor"):
        super().__init__(name=name)

    def _build_deterministic_fallback(
        self,
        pair: str,
        regime_data: dict[str, Any],
        calendar_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Provides a mathematically sound, deterministic briefing if LLM generation fails."""
        trend = regime_data.get("aligned_trend", "RANGE").upper()
        current_price = float(regime_data.get("current_price", 1.0850))
        regime_1h = regime_data.get("regime_1h", {})
        regime_15m = regime_data.get("regime_15m", {})
        is_gold = "XAU" in pair.upper() or "GOLD" in pair.upper()

        # For Gold or intraday scalping, prioritize 15M ATR for tighter day-trading bounds
        if regime_15m and float(regime_15m.get("atr_14", 0.0)) > 0:
            atr = float(regime_15m["atr_14"])
        else:
            atr = float(regime_1h.get("atr_14", 0.0015))
        if atr <= 0:
            atr = 5.0

        defensive_hold = calendar_data.get("defensive_hold", False)
        hold_reason = calendar_data.get("hold_reason", "")

        decimals = 2
        sl_multiplier = 1.2
        tp_multiplier = 2.6

        if trend == "BULLISH":
            bias = "BULLISH"
            entry_price = current_price
            entry_1 = round(entry_price - 0.15 * atr, decimals)
            entry_2 = round(entry_price - 0.20 * atr, decimals)
            stop_loss = round(entry_price - sl_multiplier * atr, decimals)
            target_1 = round(entry_price + 1.5 * atr, decimals)
            target_2 = round(entry_price + tp_multiplier * atr, decimals)
            thesis = (
                f"Waiting for XAUUSD to tap the 1H/4H Order Block near {entry_2}. "
                f"Upon a 5m ChoCh with FVG displacement, limit orders activate at 50% FVG ({entry_1}) and Extreme OB ({entry_2})."
            )
        elif trend == "BEARISH":
            bias = "BEARISH"
            entry_price = current_price
            entry_1 = round(entry_price + 0.15 * atr, decimals)
            entry_2 = round(entry_price + 0.20 * atr, decimals)
            stop_loss = round(entry_price + sl_multiplier * atr, decimals)
            target_1 = round(entry_price - 1.5 * atr, decimals)
            target_2 = round(entry_price - tp_multiplier * atr, decimals)
            thesis = (
                f"Waiting for XAUUSD to tap the 1H/4H Order Block near {entry_2}. "
                f"Upon a 5m ChoCh with FVG displacement, limit orders activate at 50% FVG ({entry_1}) and Extreme OB ({entry_2})."
            )
        else:
            bias = "NEUTRAL"
            entry_price = current_price
            entry_1 = round(entry_price - 0.1 * atr, decimals)
            entry_2 = round(entry_price - 0.2 * atr, decimals)
            stop_loss = round(entry_price - sl_multiplier * atr, decimals)
            target_1 = round(entry_price + 1.5 * atr, decimals)
            target_2 = round(entry_price + tp_multiplier * atr, decimals)
            thesis = (
                f"XAUUSD Intraday Standby: Consolidating ahead of institutional liquidity catalysts. "
                "Awaiting clear sweep of session boundaries and 5m ChoCh to form entries."
            )

        if defensive_hold:
            thesis = (
                f"DEFENSIVE HOLD ACTIVE: {hold_reason or 'Upcoming high-impact macro catalyst presents severe slippage risk.'} "
                f"Despite underlying {bias.lower()} bias, all new order executions remain paused until volatility subsides."
            )

        return {
            "market_bias": bias,
            "key_levels": {
                "htf_ob_zone": f"{entry_2} - {entry_price}",
                "entry_1_aggressive_fvg": entry_1,
                "entry_2_extreme_ob": entry_2,
                "stop_loss": stop_loss,
                "target_1": target_1,
                "target_2": target_2,
            },
            "thesis": thesis,
        }

    async def synthesize_trade_briefing(
        self,
        pair: str,
        regime_data: dict[str, Any],
        calendar_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Prompts Gemini with market context to generate a structured trade briefing."""
        current_price = regime_data.get("current_price", 1.0)
        aligned_trend = regime_data.get("aligned_trend", "RANGE")
        regime_15m = regime_data.get("regime_15m", {})
        regime_1h = regime_data.get("regime_1h", {})
        regime_4h = regime_data.get("regime_4h", {})
        sessions = regime_data.get("market_sessions", {})
        high_impact_events = calendar_data.get("high_impact_events", [])
        defensive_hold = calendar_data.get("defensive_hold", False)
        hold_reason = calendar_data.get("hold_reason", "")
        atr = float(regime_1h.get("atr_14", 5.0))
        pair = "XAUUSD"

        gold_strategy_text = ""
        try:
            import os
            strategy_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "forex_strategies", "my_strategy.md"
            )
            if os.path.exists(strategy_path):
                with open(strategy_path, "r", encoding="utf-8") as f:
                    gold_strategy_text = f"\n=== PROPRIETARY SMC GOLD STRATEGY (MANDATORY) ===\n{f.read()}\n"
        except Exception as e:
            self.logger.warning(f"Failed to load Gold strategy: {e}")

        intraday_section = (
            f"\n- 15M Intraday Regime: Trend={regime_15m.get('trend', 'N/A')}, "
            f"EMA20={regime_15m.get('ema_20', 'N/A')}, EMA50={regime_15m.get('ema_50', 'N/A')}, "
            f"RSI14={regime_15m.get('rsi_14', 'N/A')}, 15M ATR={regime_15m.get('atr_14', 'N/A')}\n"
            "- TRADING PROFILE: INTRADAY DAY TRADER. "
            "Provide precise intraday execution levels, using 15M pullbacks/sweeps. "
            "Ensure a tight structural stop loss and a realistic target honoring >= 1:2.0 Risk-to-Reward ratio."
        )

        default_fallback = self._build_deterministic_fallback(
            pair=pair, regime_data=regime_data, calendar_data=calendar_data
        )

        prompt = f"""
You are an Elite Institutional FX & Gold Quantitative Strategist and Senior Risk Manager.
Synthesize the technical market regime and macroeconomic calendar into a high-conviction trade briefing for {pair}.

=== MARKET REGIME CONTEXT ===
- Asset Pair: {pair}
- Current Market Price: {current_price}
- Higher Timeframe Trend: {aligned_trend}
- 1H Regime: Trend={regime_1h.get('trend')}, EMA20={regime_1h.get('ema_20')}, EMA50={regime_1h.get('ema_50')}, RSI14={regime_1h.get('rsi_14')}, ATR14={atr}
- 4H Regime: Trend={regime_4h.get('trend')}, Swing High={regime_4h.get('swing_high')}, Swing Low={regime_4h.get('swing_low')}
- Active Market Sessions: {sessions.get('active_sessions')} (Liquidity Rating: {sessions.get('liquidity_rating')}){intraday_section}
{gold_strategy_text}
=== MACROECONOMIC CALENDAR CONTEXT ===
- Defensive Hold Status: {'ACTIVE DEFENSIVE_HOLD' if defensive_hold else 'NORMAL MARKET EXECUTION'}
- Defensive Hold Detail: {hold_reason if hold_reason else 'None'}
- Upcoming High-Impact Catalysts: {high_impact_events[:3]}

=== MANDATORY RISK INSTRUCTIONS ===
1. Return a single strictly valid JSON object. Do not wrap in conversational chit-chat.
2. Market Bias MUST be one of: "BULLISH", "BEARISH", or "NEUTRAL".
3. Key levels MUST respect strict mathematical risk geometry from the Performance-Based SMC Strategy:
   - For BULLISH bias: stop_loss < entry_2_extreme_ob <= entry_1_aggressive_fvg < target_1 < target_2. 
   - For BEARISH bias: target_2 < target_1 < entry_1_aggressive_fvg <= entry_2_extreme_ob < stop_loss.
4. Target_1 MUST be a 1:1 or 1:2 R:R from Entry 1. Target_2 MUST target the opposing HTF liquidity pool.
5. If Defensive Hold is active, the thesis MUST clearly acknowledge the macro hold state.
6. The 'thesis' MUST explicitly state the wait condition: "Waiting for XAUUSD to tap the HTF Order Block. Upon a 5m ChoCh with FVG displacement, limit orders activate at 50% FVG and Extreme OB."

JSON Output Format:
{{
  "market_bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "key_levels": {{
    "htf_ob_zone": "4320.00 - 4322.00",
    "entry_1_aggressive_fvg": 4323.50,
    "entry_2_extreme_ob": 4321.00,
    "stop_loss": 4319.00,
    "target_1": 4328.00,
    "target_2": 4335.00
  }},
  "thesis": "Waiting for XAUUSD to tap the 1H/4H Order Block near [Price]. Upon a 5m ChoCh with FVG displacement, limit orders activate at 50% FVG and Extreme OB."
}}
"""
        system_instruction = (
            "You are a quantitative FX strategist producing strict, high-conviction JSON market briefings. "
            "Never violate the 1:2 Risk-to-Reward constraint."
        )

        try:
            briefing = generate_json_with_failover(
                prompt_text=prompt,
                system_instruction=system_instruction,
                temperature=0.2,
                max_attempts=2,
                default_fallback=default_fallback,
            )

            # Sanity validation on briefing keys
            if (
                not isinstance(briefing, dict)
                or "market_bias" not in briefing
                or "key_levels" not in briefing
                or "thesis" not in briefing
            ):
                return default_fallback

            levels = briefing.get("key_levels", {})
            if (
                "entry_1_aggressive_fvg" not in levels
                or "stop_loss" not in levels
                or "target_1" not in levels
            ):
                return default_fallback

            # Ensure numeric float conversion
            levels["entry_1_aggressive_fvg"] = float(levels.get("entry_1_aggressive_fvg", default_fallback["key_levels"]["entry_1_aggressive_fvg"]))
            levels["entry_2_extreme_ob"] = float(levels.get("entry_2_extreme_ob", levels["entry_1_aggressive_fvg"]))
            levels["stop_loss"] = float(levels["stop_loss"])
            levels["target_1"] = float(levels.get("target_1", default_fallback["key_levels"]["target_1"]))
            levels["target_2"] = float(levels.get("target_2", levels["target_1"]))

            return briefing

        except Exception as e:  # noqa: BLE001
            self.logger.warning(f"Failed to generate LLM briefing, using fallback: {e}")
            return default_fallback

    async def execute(self, payload: dict[str, Any] | None = None) -> AgentResult:
        payload = payload or {}
        pair = payload.get("pair", "EURUSD").upper()
        regime_data = payload.get("regime_data", {})
        calendar_data = payload.get("calendar_data", {})

        briefing = await self.synthesize_trade_briefing(
            pair=pair,
            regime_data=regime_data,
            calendar_data=calendar_data,
        )

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "pair": pair,
                "briefing": briefing,
            },
        )

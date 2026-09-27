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
            entry_low = round(entry_price - 0.15 * atr, decimals)
            entry_high = round(entry_price + 0.1 * atr, decimals)
            stop_loss = round(entry_price - sl_multiplier * atr, decimals)
            invalidation = stop_loss
            target = round(entry_price + tp_multiplier * atr, decimals)
            thesis = (
                f"Gold (XAUUSD) Day Trade & Scalp: Price respects 15M EMA dynamic support aligned with broader market structure. "
                f"We initiate long scalp exposure on pullbacks toward support with thesis invalidation below {invalidation}."
            )
        elif trend == "BEARISH":
            bias = "BEARISH"
            entry_price = current_price
            entry_low = round(entry_price - 0.1 * atr, decimals)
            entry_high = round(entry_price + 0.15 * atr, decimals)
            stop_loss = round(entry_price + sl_multiplier * atr, decimals)
            invalidation = stop_loss
            target = round(entry_price - tp_multiplier * atr, decimals)
            thesis = (
                f"Gold (XAUUSD) Day Trade & Scalp: Spot price rejects dynamic resistance with 15M EMA cluster confirming intraday supply. "
                f"Short scalp orders target local liquidity pools below, invalidating strictly above {invalidation}."
            )
        else:
            bias = "NEUTRAL"
            entry_price = current_price
            entry_low = round(entry_price - 0.1 * atr, decimals)
            entry_high = round(entry_price + 0.1 * atr, decimals)
            stop_loss = round(entry_price - sl_multiplier * atr, decimals)
            invalidation = stop_loss
            target = round(entry_price + tp_multiplier * atr, decimals)
            thesis = (
                f"Gold (XAUUSD) Intraday Standby: Gold consolidates in a narrow range ahead of institutional liquidity catalysts. "
                "Scalp entries are withheld until price sweeps session boundaries with confirmed volume."
            )

        if defensive_hold:
            thesis = (
                f"DEFENSIVE HOLD ACTIVE: {hold_reason or 'Upcoming high-impact macro catalyst presents severe slippage risk.'} "
                f"Despite underlying {bias.lower()} bias, all new order executions remain paused until volatility subsides."
            )

        return {
            "market_bias": bias,
            "key_levels": {
                "entry_range": f"{entry_low} - {entry_high}",
                "entry_price": round(entry_price, decimals),
                "invalidation": invalidation,
                "stop_loss": stop_loss,
                "target": target,
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
3. Key levels MUST respect strict mathematical risk geometry:
   - For BULLISH bias: stop_loss < entry_price < target. The target MUST provide AT LEAST a 1:2.0 Risk-to-Reward ratio (target - entry >= 2.0 * (entry - stop_loss)).
   - For BEARISH bias: target < entry_price < stop_loss. The target MUST provide AT LEAST a 1:2.0 Risk-to-Reward ratio (entry - target >= 2.0 * (stop_loss - entry)).
   - For NEUTRAL bias: provide standard breakout bounds with stop_loss and target honoring >= 1:2 RR.
4. If Defensive Hold is active, the thesis MUST clearly acknowledge the macro hold state.
5. The 'thesis' MUST be exactly 2 concise, professional sentences.

JSON Output Format:
{{
  "market_bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "key_levels": {{
    "entry_range": "low_val - high_val",
    "entry_price": 1.0850,
    "invalidation": 1.0800,
    "stop_loss": 1.0800,
    "target": 1.0960
  }},
  "thesis": "First sentence analyzing institutional catalyst and trend confluence. Second sentence defining execution trigger and risk boundary."
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
                "entry_price" not in levels
                or "stop_loss" not in levels
                or "target" not in levels
            ):
                return default_fallback

            # Ensure numeric float conversion
            levels["entry_price"] = float(levels["entry_price"])
            levels["stop_loss"] = float(levels["stop_loss"])
            levels["target"] = float(levels["target"])
            if "invalidation" in levels:
                levels["invalidation"] = float(levels["invalidation"])
            else:
                levels["invalidation"] = levels["stop_loss"]

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

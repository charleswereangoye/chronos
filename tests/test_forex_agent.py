from datetime import datetime, timedelta, timezone

import pytest

from agents.forex_agent.advisor import ForexAdvisor
from agents.forex_agent.calendar_monitor import CalendarMonitor, EconomicEvent
from agents.forex_agent.forex_coordinator import ForexCoordinator
from agents.forex_agent.regime_analyzer import Candle, RegimeAnalyzer
from agents.forex_agent.risk_guard import RiskGuard
from orchestrator.telegram_orchestrator import format_forex_card
from shared.base_agent import AgentStatus


# ==========================================================
# 1. CalendarMonitor Tests (The Macro Gatekeeper)
# ==========================================================
def test_economic_event_dataclass():
    now = datetime.now(timezone.utc)
    event = EconomicEvent(
        title="US Non-Farm Payrolls",
        country="USD",
        impact="High",
        time_utc=now,
        forecast="180K",
        previous="150K",
    )
    d = event.to_dict()
    assert d["title"] == "US Non-Farm Payrolls"
    assert d["country"] == "USD"
    assert d["impact"] == "High"
    assert d["time_utc"] == now.isoformat()


def test_calendar_monitor_is_high_impact():
    monitor = CalendarMonitor()
    now = datetime.now(timezone.utc)

    # By impact string
    e1 = EconomicEvent("Trade Balance", "USD", "High", now)
    assert monitor.is_high_impact(e1) is True

    # By keyword
    e2 = EconomicEvent("Core CPI m/m", "USD", "Medium", now)
    assert monitor.is_high_impact(e2) is True

    e3 = EconomicEvent("FOMC Statement", "USD", "Low", now)
    assert monitor.is_high_impact(e3) is True

    # Low impact without keywords
    e4 = EconomicEvent("Minor Consumer Survey", "NZD", "Low", now)
    assert monitor.is_high_impact(e4) is False


def test_calendar_monitor_defensive_hold_windows():
    monitor = CalendarMonitor()
    ref_time = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Event scheduled in 10 minutes -> DEFENSIVE_HOLD active
    event_in_10m = EconomicEvent(
        title="US CPI YoY",
        country="USD",
        impact="High",
        time_utc=ref_time + timedelta(minutes=10),
    )
    res_10m = monitor.evaluate_defensive_hold(
        events=[event_in_10m], pair="EURUSD", reference_time=ref_time
    )
    assert res_10m["defensive_hold"] is True
    assert "DEFENSIVE_HOLD" in res_10m["hold_reason"]

    # 2. Event scheduled in 29 minutes -> DEFENSIVE_HOLD active
    event_in_29m = EconomicEvent(
        title="Non-Farm Employment Change",
        country="USD",
        impact="High",
        time_utc=ref_time + timedelta(minutes=29),
    )
    res_29m = monitor.evaluate_defensive_hold(
        events=[event_in_29m], pair="EURUSD", reference_time=ref_time
    )
    assert res_29m["defensive_hold"] is True

    # 3. Event scheduled in 45 minutes -> DEFENSIVE_HOLD NOT active
    event_in_45m = EconomicEvent(
        title="US CPI YoY",
        country="USD",
        impact="High",
        time_utc=ref_time + timedelta(minutes=45),
    )
    res_45m = monitor.evaluate_defensive_hold(
        events=[event_in_45m], pair="EURUSD", reference_time=ref_time
    )
    assert res_45m["defensive_hold"] is False

    # 4. Event released 10 minutes ago -> DEFENSIVE_HOLD active (post-release volatility window)
    event_past_10m = EconomicEvent(
        title="ECB Interest Rate Decision",
        country="EUR",
        impact="High",
        time_utc=ref_time - timedelta(minutes=10),
    )
    res_past = monitor.evaluate_defensive_hold(
        events=[event_past_10m], pair="EURUSD", reference_time=ref_time
    )
    assert res_past["defensive_hold"] is True

    # 5. Irrelevant currency -> DEFENSIVE_HOLD not triggered
    event_jpy = EconomicEvent(
        title="BOJ Rate Decision",
        country="JPY",
        impact="High",
        time_utc=ref_time + timedelta(minutes=10),
    )
    res_jpy = monitor.evaluate_defensive_hold(
        events=[event_jpy],
        pair="EURUSD",
        target_currencies=["EUR"],
        reference_time=ref_time,
    )
    assert res_jpy["defensive_hold"] is False


@pytest.mark.asyncio
async def test_calendar_monitor_agent_lifecycle():
    monitor = CalendarMonitor()
    ref_time = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    injected_events = [
        {
            "title": "US CPI m/m",
            "country": "USD",
            "impact": "High",
            "time_utc": (ref_time + timedelta(minutes=15)).isoformat(),
        }
    ]
    result = await monitor.run(
        {
            "pair": "EURUSD",
            "reference_time": ref_time.isoformat(),
            "events": injected_events,
        }
    )
    assert result.status == AgentStatus.SUCCESS
    assert result.data["defensive_hold"] is True
    assert result.data["trigger_event"]["title"] == "US CPI m/m"


# ==========================================================
# 2. RegimeAnalyzer Tests (Deterministic Market State)
# ==========================================================
def test_regime_analyzer_market_sessions():
    analyzer = RegimeAnalyzer()

    # London Open: 08:30 UTC
    t_london = datetime(2026, 9, 11, 8, 30, tzinfo=timezone.utc)
    s_london = analyzer.identify_market_sessions(ref_time=t_london)
    assert s_london["is_london_open"] is True
    assert "London Open" in s_london["active_sessions"]

    # London/NY Overlap: 14:00 UTC
    t_overlap = datetime(2026, 9, 11, 14, 0, tzinfo=timezone.utc)
    s_overlap = analyzer.identify_market_sessions(ref_time=t_overlap)
    assert s_overlap["is_overlap"] is True
    assert "London/NY Overlap" in s_overlap["active_sessions"]
    assert s_overlap["liquidity_rating"] == "PEAK"

    # Asian Session: 03:00 UTC
    t_asian = datetime(2026, 9, 11, 3, 0, tzinfo=timezone.utc)
    s_asian = analyzer.identify_market_sessions(ref_time=t_asian)
    assert "Asian Session" in s_asian["active_sessions"]


def test_regime_analyzer_deterministic_indicators():
    analyzer = RegimeAnalyzer()
    candles = analyzer._generate_fallback_candles(pair="EURUSD", count=60)
    assert len(candles) == 60

    # ATR test
    atr = analyzer.calculate_atr(candles, 14)
    assert atr > 0.0

    # Resampling test
    candles_4h = analyzer.resample_to_4h(candles)
    assert len(candles_4h) == 15

    # Structure & Regime evaluation
    snapshot = analyzer.evaluate_timeframe(candles, "1H")
    assert snapshot.trend in ("BULLISH", "BEARISH", "RANGE")
    assert snapshot.ema_20 > 0.0
    assert 0.0 <= snapshot.rsi_14 <= 100.0


@pytest.mark.asyncio
async def test_regime_analyzer_agent_lifecycle():
    analyzer = RegimeAnalyzer()
    now_ts = int(datetime.now(timezone.utc).timestamp())
    # Deterministic rising candles
    test_candles = [
        Candle(
            timestamp=now_ts + i * 3600,
            open=1.0800 + i * 0.0010,
            high=1.0820 + i * 0.0010,
            low=1.0795 + i * 0.0010,
            close=1.0815 + i * 0.0010,
            volume=500.0,
        )
        for i in range(40)
    ]
    raw_payload = [
        {"timestamp": c.timestamp, "open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume}
        for c in test_candles
    ]

    result = await analyzer.run({"pair": "EURUSD", "candles_1h": raw_payload})
    assert result.status == AgentStatus.SUCCESS
    assert result.data["aligned_trend"] == "BULLISH"
    assert result.data["key_resistance"] > result.data["key_support"]


# ==========================================================
# 3. RiskGuard Tests (Mathematical Safety Bounds)
# ==========================================================
def test_risk_guard_mandatory_rr_rejection():
    guard = RiskGuard()

    # LONG setup with R:R = 1.0 (Entry 1.1000, SL 1.0900 -> Risk 100 pips; TP 1.1100 -> Reward 100 pips)
    res_bad_rr = guard.validate_setup(
        direction="BUY",
        entry_price=1.1000,
        stop_loss=1.0900,
        target_price=1.1100,
        account_balance=10000.0,
        pair="EURUSD",
    )
    assert res_bad_rr.is_approved is False
    assert res_bad_rr.status == "REJECTED"
    assert res_bad_rr.risk_reward_ratio == 1.0
    assert any("Risk-to-Reward ratio" in reason for reason in res_bad_rr.rejection_reasons)

    # LONG setup with valid R:R >= 2.0 (Entry 1.1000, SL 1.0950 -> Risk 50 pips; TP 1.1120 -> Reward 120 pips -> R:R 2.4)
    res_good_rr = guard.validate_setup(
        direction="BUY",
        entry_price=1.1000,
        stop_loss=1.0950,
        target_price=1.1120,
        account_balance=10000.0,
        pair="EURUSD",
    )
    assert res_good_rr.is_approved is True
    assert res_good_rr.status == "APPROVED"
    assert res_good_rr.risk_reward_ratio == 2.4


def test_risk_guard_short_setup_geometry():
    guard = RiskGuard()

    # Valid SHORT: Stop loss above entry, target below entry
    # Entry 1.1000, SL 1.1050 (Risk 50 pips), TP 1.0850 (Reward 150 pips) -> R:R 3.0
    res_short = guard.validate_setup(
        direction="SELL",
        entry_price=1.1000,
        stop_loss=1.1050,
        target_price=1.0850,
        account_balance=10000.0,
        pair="EURUSD",
    )
    assert res_short.is_approved is True
    assert res_short.risk_reward_ratio == 3.0

    # Invalid SHORT: Stop loss below entry (structural violation)
    res_invalid_short = guard.validate_setup(
        direction="SELL",
        entry_price=1.1000,
        stop_loss=1.0950,
        target_price=1.0850,
        account_balance=10000.0,
        pair="EURUSD",
    )
    assert res_invalid_short.is_approved is False
    assert any("Structural violation" in r for r in res_invalid_short.rejection_reasons)


def test_risk_guard_maximum_1_percent_account_risk():
    guard = RiskGuard()
    balance = 10000.0  # 1% = $100 max risk
    # 50 pips risk on EURUSD ($10 per pip per lot -> $500 risk per lot)
    # Expected lots = $100 / $500 = 0.20 lots
    res = guard.validate_setup(
        direction="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        target_price=1.0970,
        account_balance=balance,
        pair="EURUSD",
    )
    assert res.is_approved is True
    assert res.recommended_lots == 0.20
    assert res.actual_risk_dollars <= 100.0
    assert res.actual_risk_pct <= 1.0


def test_risk_guard_insufficient_balance_micro_risk():
    guard = RiskGuard()
    tiny_balance = 100.0  # 1% = $1.00 max risk
    # 100 pips risk -> 0.01 lot on EURUSD risks $10.00 (which is 10% of account!)
    res = guard.validate_setup(
        direction="BUY",
        entry_price=1.1000,
        stop_loss=1.0900,
        target_price=1.1300,
        account_balance=tiny_balance,
        pair="EURUSD",
    )
    assert res.is_approved is False
    assert any("exceeding the strict 1.0% account ceiling" in r for r in res.rejection_reasons)


# ==========================================================
# 4. ForexAdvisor Tests (Gemini Synthesis & Fallback)
# ==========================================================
def test_forex_advisor_deterministic_fallback():
    advisor = ForexAdvisor()
    regime_data = {
        "aligned_trend": "BULLISH",
        "current_price": 1.0850,
        "regime_1h": {"atr_14": 0.0020, "trend": "BULLISH"},
    }
    calendar_data = {"defensive_hold": False}

    briefing = advisor._build_deterministic_fallback(
        pair="EURUSD", regime_data=regime_data, calendar_data=calendar_data
    )
    assert briefing["market_bias"] == "BULLISH"
    levels = briefing["key_levels"]
    risk = levels["entry_price"] - levels["stop_loss"]
    reward = levels["target"] - levels["entry_price"]
    assert reward / risk >= 2.0
    assert len(briefing["thesis"].split(".")) >= 2


@pytest.mark.asyncio
async def test_forex_advisor_agent_lifecycle():
    advisor = ForexAdvisor()
    regime_data = {
        "aligned_trend": "BEARISH",
        "current_price": 1.2500,
        "regime_1h": {"atr_14": 0.0025, "trend": "BEARISH"},
    }
    calendar_data = {"defensive_hold": True, "hold_reason": "High impact NFP news in 15m."}

    # Runs with offline fallback resilience
    result = await advisor.run(
        {
            "pair": "GBPUSD",
            "regime_data": regime_data,
            "calendar_data": calendar_data,
        }
    )
    assert result.status == AgentStatus.SUCCESS
    briefing = result.data["briefing"]
    assert "defensive hold" in briefing["thesis"].lower()


# ==========================================================
# 5. ForexCoordinator Tests (End-to-End Pipeline)
# ==========================================================
@pytest.mark.asyncio
async def test_forex_coordinator_defensive_hold_pipeline():
    coordinator = ForexCoordinator()
    ref_time = datetime(2026, 9, 11, 14, 0, tzinfo=timezone.utc)
    injected_events = [
        {
            "title": "US Non-Farm Employment",
            "country": "USD",
            "impact": "High",
            "time_utc": (ref_time + timedelta(minutes=20)).isoformat(),
        }
    ]

    result = await coordinator.run(
        {
            "pair": "EURUSD",
            "account_balance": 10000.0,
            "reference_time": ref_time.isoformat(),
            "calendar": {"events": injected_events},
        }
    )

    assert result.status == AgentStatus.SUCCESS
    assert result.data["trade_action"] == "DEFENSIVE_HOLD"
    assert result.data["defensive_hold"] is True


@pytest.mark.asyncio
async def test_forex_coordinator_approved_pipeline():
    coordinator = ForexCoordinator()
    ref_time = datetime(2026, 9, 11, 14, 0, tzinfo=timezone.utc)

    # Empty calendar (no high-impact news)
    result = await coordinator.run(
        {
            "pair": "EURUSD",
            "account_balance": 10000.0,
            "reference_time": ref_time.isoformat(),
            "calendar": {"events": []},
        }
    )

    assert result.status == AgentStatus.SUCCESS
    assert result.data["defensive_hold"] is False
    assert result.data["risk_evaluation"]["is_approved"] is True
    assert result.data["risk_evaluation"]["risk_reward_ratio"] >= 2.0
    assert result.data["risk_evaluation"]["actual_risk_pct"] <= 1.0


# ==========================================================
# 6. Telegram Orchestrator Card Formatting Tests
# ==========================================================
def test_format_forex_card():
    sample_setup = {
        "pair": "EURUSD",
        "trade_action": "READY_FOR_HITL_REVIEW",
        "market_bias": "BULLISH",
        "current_price": 1.0855,
        "key_levels": {
            "entry_range": "1.0845 - 1.0865",
            "entry_price": 1.0855,
            "stop_loss": 1.0815,
            "target": 1.0955,
            "invalidation": 1.0815,
        },
        "risk_evaluation": {
            "is_approved": True,
            "risk_reward_ratio": 2.5,
            "actual_risk_pct": 0.95,
            "actual_risk_dollars": 95.0,
            "recommended_lots": 0.24,
            "risk_pips": 40.0,
            "reward_pips": 100.0,
        },
        "sessions": {
            "active_sessions": ["London/NY Overlap"],
            "liquidity_rating": "PEAK",
        },
        "thesis": "Bullish trend supported by institutional order flow. Looking for long entries on pullbacks.",
        "defensive_hold": False,
    }

    card_text, reply_markup = format_forex_card(sample_setup, "test1234")

    assert "CHRONOS QUANTITATIVE FOREX ALERT" in card_text
    assert "EURUSD" in card_text
    assert "1:2.50" in card_text
    assert "0.24 Lots" in card_text
    assert "London/NY Overlap" in card_text

    # Verify inline keyboard buttons
    buttons = reply_markup.inline_keyboard
    flat_buttons = [btn for row in buttons for btn in row]
    callbacks = [btn.callback_data for btn in flat_buttons]
    assert "forex_approve_test1234" in callbacks
    assert "forex_dismiss_test1234" in callbacks
    assert "forex_refresh_EURUSD" in callbacks


# ==========================================================
# 6. Orchestrator Forex Menu & State Wiring Tests
# ==========================================================
@pytest.mark.asyncio
async def test_orchestrator_main_menu_to_forex_menu():
    from unittest.mock import AsyncMock, MagicMock
    from orchestrator.telegram_orchestrator import (
        main_menu_handler,
        FOREX_MENU,
        MAIN_MENU,
        forex_menu_handler,
        FOREX_CUSTOM_PAIR,
        safe_reply,
    )
    from telegram import ReplyKeyboardMarkup

    # Test main_menu_handler option "3"
    update = MagicMock()
    update.effective_chat = MagicMock(id=12345)
    update.message = MagicMock()
    update.message.text = "3. 💱 Forex Agent"
    update.message.reply_text = AsyncMock()

    context = MagicMock()
    state = await main_menu_handler(update, context)
    assert state == FOREX_MENU
    assert update.message.reply_text.called
    call_args = update.message.reply_text.call_args
    assert "Forex Trading Agent Menu" in call_args[0][0]
    assert isinstance(call_args[1]["reply_markup"], ReplyKeyboardMarkup)

    # Test forex_menu_handler option "0" -> returns MAIN_MENU
    update_back = MagicMock()
    update_back.message = MagicMock()
    update_back.message.text = "0. 🔙 Back to Main Menu"
    update_back.message.reply_text = AsyncMock()

    back_state = await forex_menu_handler(update_back, context)
    assert back_state == MAIN_MENU

    # Test forex_menu_handler option "2" (Quick Check Other Pair) -> returns FOREX_CUSTOM_PAIR
    update_quick = MagicMock()
    update_quick.message = MagicMock()
    update_quick.message.text = "2. ⚡ Quick Check Other Pair"
    update_quick.message.reply_text = AsyncMock()

    quick_state = await forex_menu_handler(update_quick, context)
    assert quick_state == FOREX_CUSTOM_PAIR

    # Test receive_forex_pair cancel -> returns FOREX_MENU
    from orchestrator.telegram_orchestrator import receive_forex_pair
    update_cancel = MagicMock()
    update_cancel.message = MagicMock()
    update_cancel.message.text = "0. 🔙 Back to Forex Menu"
    update_cancel.message.reply_text = AsyncMock()

    cancel_state = await receive_forex_pair(update_cancel, context)
    assert cancel_state == FOREX_MENU


@pytest.mark.asyncio
async def test_format_forex_card_gold_day_trading():
    from orchestrator.telegram_orchestrator import format_forex_card

    sample_gold = {
        "pair": "XAUUSD",
        "market_bias": "BULLISH",
        "trade_action": "READY_FOR_HITL_REVIEW",
        "current_price": 2650.50,
        "key_levels": {
            "entry_range": "2649.50 - 2651.00",
            "entry_price": 2650.50,
            "stop_loss": 2645.50,
            "target": 2662.50,
            "invalidation": 2645.50,
        },
        "risk_evaluation": {
            "is_approved": True,
            "risk_reward_ratio": 2.4,
            "risk_pips": 50.0,
            "reward_pips": 120.0,
            "actual_risk_pct": 1.0,
            "actual_risk_dollars": 100.0,
            "recommended_lots": 0.20,
        },
        "sessions": {
            "active_sessions": ["London Open", "London Session"],
            "liquidity_rating": "PEAK",
        },
        "regime_15m": {
            "trend": "BULLISH",
            "rsi_14": 58.5,
            "atr_14": 4.5,
        },
        "thesis": "Gold intraday structure confirms 15M EMA pullback with strong institutional buying.",
        "defensive_hold": False,
    }

    card_text, markup = format_forex_card(sample_gold, "gold1234")
    assert "CHRONOS GOLD (XAUUSD) DAY TRADE & SCALP ALERT" in card_text
    assert "XAUUSD" in card_text
    assert "Intraday Scalp & Day Trade" in card_text
    assert "15M Structure" in card_text
    assert "2650.50" in card_text
    assert "1:2.40" in card_text


@pytest.mark.asyncio
async def test_safe_reply_entity_parse_fallback():
    from unittest.mock import AsyncMock, MagicMock
    from orchestrator.telegram_orchestrator import safe_reply
    from telegram.error import BadRequest

    msg = MagicMock()
    # Simulate Telegram throwing BadRequest when parsing entities on first attempt
    async def mock_reply_text(text, parse_mode=None, **kwargs):
        if parse_mode == "Markdown":
            raise BadRequest("Can't parse entities: can't find end of the entity")
        return "SUCCESS_PLAIN"

    msg.reply_text = AsyncMock(side_effect=mock_reply_text)
    
    # Should catch BadRequest and fallback cleanly without crashing
    res = await safe_reply(msg, "Broken *Markdown_ test text")
    assert res == "SUCCESS_PLAIN"
    assert msg.reply_text.call_count == 2


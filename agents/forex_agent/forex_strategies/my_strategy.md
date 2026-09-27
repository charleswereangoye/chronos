# GOLD (XAUUSD) INTRADAY / DAY TRADING STRATEGY - Performance-Based SMC & Quantitative Execution

## 1. Core Institutional Mechanics (The Foundation)
- **Asset**: Strictly GOLD (XAUUSD).
- **Timeframe Analysis (Top-Down)**: Analyze structural trend on 4H, 1H, 30m, and 15m timeframes to identify institutional Order Blocks (OB) and Liquidity Zones (Session Highs/Lows).
- **Execution Timeframe**: All entries are executed strictly on the 5-minute (5m) timeframe.

## 2. Entry Triggers (5-minute timeframe)
1. Wait for price to sweep key liquidity or tap into the Higher Timeframe Order Block (aligned with the trend).
2. Wait for a **Change of Character (ChoCh) / Market Structure Shift (MSS)** on the 5m timeframe.
3. **Condition for valid ChoCh**: The structural break MUST be created by impulsive displacement (volume) that leaves behind a **Fair Value Gap (FVG)**.

## 3. The Dual-Entry Quantitative Model (Risk Division)
Rather than guessing if price will respect the shallow FVG or sweep into the extreme Order Block, apply **Risk Division**. Split the total risk budget evenly across two limit orders (e.g., $15 total risk = $7.50 on Entry 1, $7.50 on Entry 2).

### Entry 1: Aggressive FVG
- Set a limit order at the **50% equilibrium of the Fair Value Gap (FVG)** created by the displacement candle.
- Execution Behavior: If momentum is strong, you participate with half-risk without FOMO. If price sweeps deeper, this absorbs a minor controlled loss.

### Entry 2: Extreme Order Block
- Set a second limit order at the **50% mean threshold of the extreme 5-minute Order Block** that originated the ChoCh.
- Execution Behavior: Fills at optimal discount if market engineers a deeper sweep before the real move.

## 4. Structural Stop-Loss Placement
- **Invalidation Point**: Never size stops based on arbitrary pips. Place the stop loss strictly beyond the invalidation swing wick (the high/low that executed the initial liquidity sweep).
- **Buffer Rule**: Add **5 to 10 pips of clearance** past the structural wick on XAUUSD to account for broker spread widening.

## 5. Trade Management (Curing the 50% Reversal Trap)
Execute a mechanical two-target exit to prevent winning setups from collapsing:
- **Target 1 (Liquidity Extraction)**: Set Take Profit for Entry 1 at a **1:1 or 1:2 Risk-to-Reward** (typically 30-50 pips on Gold). This secures cash and eliminates anxiety.
- **The Break-Even Transition**: The exact moment Target 1 is hit, advance the stop loss of the remaining position (Entry 2) to entry (Break-Even).
- **Target 2 (Structural Expansion)**: Allow Entry 2 to run toward the opposing HTF liquidity pool or session extreme. Trail the stop behind confirmed 5-minute structural swings until an opposing ChoCh prints.

## 6. The Performance-Based Operational Rules
1. **Trade Batched Sample Sizes**: Evaluate performance in cohorts of 20-30 trades. A single trade carries no statistical significance.
2. **Eliminate Fixed Daily Dollar Demands**: Trade exclusively when structural parameters align (Pristine A+ setups only).
3. **Strict Session Killzones**: Limit execution strictly to institutional order-injection windows (London Open or New York Open).
4. **Two-Loss Circuit Breaker**: If two setups hit full stop loss in a single trading session, terminate trading for the day. Capital preservation takes precedence.

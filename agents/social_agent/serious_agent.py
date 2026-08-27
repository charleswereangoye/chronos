import random
from shared.logger import get_logger
from shared.llm import generate_json_with_failover

logger = get_logger("SeriousAgent")

class SeriousAgent:
    def __init__(self):
        pass

    def generate_serious_quote(self, research_data: dict = None) -> dict:
        logger.info("Generating professional, institutional-grade serious trading quote...")
        
        macro_news = ""
        if research_data and isinstance(research_data, dict):
            macro_news = research_data.get("macro_news", "")

        tactical_topics = [
            "Liquidity sweeps and why retail breakout entries get trapped before real expansion",
            "Asymmetric risk-to-reward (1:3+ R:R) versus high win-rate strategies with negative expectancy",
            "Spread widening and slippage during central bank rate releases and high-impact news",
            "The mathematical danger of moving stop losses or averaging down on losing trades",
            "Session timing: waiting for NY Open liquidity versus over-trading Asian session ranges",
            "Trade execution: why taking a planned small loss is a tactical victory, not a failure",
            "Protecting capital during choppy, low-volume consolidation cycles"
        ]
        chosen_topic = random.choice(tactical_topics)

        prompt = f"""
You are an elite veteran proprietary trader and risk manager with 15+ years managing 8-figure institutional capital in Gold (XAUUSD) and major Forex pairs.

YOUR TASK:
Write a high-conviction, professional trading insight. It must read like an authentic memo or post from a real veteran trader sharing actual mechanical edge.

FOCUS TOPIC FOR TODAY:
{chosen_topic}

CURRENT MARKET CONTEXT:
{macro_news if macro_news else "Markets are in normal volatility with traders positioning ahead of major macro catalysts."}

STRICT WRITING RULES:
1. ABSOLUTELY NO AI CLICHÉS OR MOTIVATIONAL FLUFF:
   - FORBIDDEN WORDS: tapestry, journey, beacon, profound, unwavering, navigate, embark, crucial, cornerstone, pivotal, realm, dance, symphony.
   - Do NOT write like a generic self-help guru or LinkedIn influencer.
2. WRITE WITH TECHNICAL SPECIFICITY:
   - Talk about concrete concepts: liquidity pools, stop runs, execution slippage, drawdowns, 1:2 / 1:3 risk-to-reward, capital preservation, invalidation levels.
3. TONE:
   - Calm, direct, authoritative, no-nonsense, grounded.

Output ONLY a JSON object with these 3 keys:
{{
    "image_quote": "A sharp, 1-2 sentence tactical trading principle. Max 35 words. Zero fluff, zero emojis, zero hashtags.",
    "x_post_text": "The exact image_quote followed by 3-4 professional hashtags (e.g. #Forex #XAUUSD #RiskManagement #TradingStrategy).",
    "meta_caption": "A 2-4 sentence detailed breakdown explaining the tactical mechanics behind the quote for LinkedIn/Instagram. Explain why amateur traders get trapped and how institutional risk management approaches it. Include 4-5 relevant hashtags."
}}
"""

        fallback = {
            "image_quote": "If your stop loss isn't placed where your trade idea is mathematically invalidated, you're not managing risk, you're just gambling with hope.",
            "x_post_text": "If your stop loss isn't placed where your trade idea is mathematically invalidated, you're not managing risk, you're just gambling with hope. #Trading #RiskManagement #Forex #XAUUSD",
            "meta_caption": "Amateur traders place stops based on how much money they can afford to lose on the trade. Professional traders place stops where the market structure proves their thesis wrong, then size the position accordingly. Protect your downside first; the upside will take care of itself. 📊📉 #ForexTrading #RiskManagement #XAUUSD #TradeManagement"
        }

        try:
            return generate_json_with_failover(
                prompt_text=prompt,
                max_attempts=3,
                default_fallback=fallback
            )
        except Exception as e:
            logger.error(f"Serious quote generation failed: {e}")
            return fallback

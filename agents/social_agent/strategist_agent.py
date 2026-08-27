import random
from shared.logger import get_logger
from shared.memory import MemoryManager
from shared.llm import generate_json_with_failover

logger = get_logger("StrategistAgent")

class StrategistAgent:
    def __init__(self):
        self.memory = MemoryManager()
        
    def generate_persona(self, research_data: dict = None, analytics_data: dict = None) -> dict:
        logger.info("Selecting dynamic comedic meme strategy for trader persona...")
        
        history = self.memory.load_history()
        last_filter = history.get("last_emotional_filter", "None")
        
        meme_archetypes = [
            "SARCASTIC_REALIST",    # Sharp, witty, roasting retail mistakes with comedy
            "EXHAUSTED_DAYTRADER",  # Sleep-deprived, coffee-fueled, staring at sideways candles
            "CHART_ADDICT",        # Drawing 40 Fibonacci lines and checking TradingView on dates
            "WICK_VICTIM",         # The tragic comedy of moving SL to breakeven and getting wicked
            "GOLD_DEGEN"           # The adrenaline and panic of trading XAUUSD 50-pip candles
        ]
        
        available = [a for a in meme_archetypes if a != last_filter]
        chosen_archetype = random.choice(available if available else meme_archetypes)
        
        meme_formats = [
            "POV_MEME",             # "POV: You finally closed your losing trade..."
            "INTERNAL_MONOLOGUE",   # "Me analyzing 4H timeframe vs Me entering on 15s chart"
            "RELATABLE_TRUTH",      # Short, hilarious observation every trader knows
            "DAILY_ROUTINE_ROAST"   # 3-step schedule of pain & coffee
        ]
        chosen_format = random.choice(meme_formats)

        prompt = f"""
You are the creative strategist for a viral, meme-first social media brand run by an authentic day trader.
Your goal is to pick today's comedic angle for a purely MEME-BASED trading post.

Selected Comedic Archetype: {chosen_archetype}
Selected Meme Format: {chosen_format}

Previous filter used: {last_filter}

Market Context (flavor only, do not make this a serious report):
{research_data.get('macro_news', 'Normal market volatility') if research_data else 'Normal market volatility'}

Generate a short JSON strategy blueprint with:
1. "emotional_filter": "{chosen_archetype}"
2. "post_format": "{chosen_format}"
3. "core_theme": "A specific hilarious trader scenario (e.g., getting wicked out by 0.5 pips, moving SL to breakeven too early, revenge trading at 3 PM, staring at flat Asian session)."
4. "narrative_angle": "The punchline or comic angle that makes traders immediately laugh and say 'that's so me'."

Output ONLY valid JSON.
"""
        fallback = {
            "emotional_filter": chosen_archetype,
            "post_format": chosen_format,
            "core_theme": "Moving stop loss to breakeven 30 seconds before a massive expansion",
            "narrative_angle": "The universal pain of watching your breakeven get tapped to the exact pip before price flies to TP."
        }

        try:
            return generate_json_with_failover(
                prompt_text=prompt,
                max_attempts=2,
                default_fallback=fallback
            )
        except Exception as e:
            logger.error(f"Failed to generate meme strategy: {e}")
            return fallback

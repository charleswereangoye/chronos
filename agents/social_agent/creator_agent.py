import json
import datetime
from shared.logger import get_logger
from shared.memory import MemoryManager
from shared.llm import generate_content_with_failover, extract_clean_json

logger = get_logger("CreatorAgent")

class CreatorAgent:
    def __init__(self):
        self.memory = MemoryManager()
        
    def generate_unique_quote(self, persona_profile: dict, critic_feedback: str = None) -> dict:
        emotional_filter = persona_profile.get('emotional_filter', 'SARCASTIC_REALIST')
        post_format = persona_profile.get('post_format', 'POV_MEME')
        core_theme = persona_profile.get('core_theme', 'Trading struggles')
        narrative_angle = persona_profile.get('narrative_angle', 'Relatable pain')
        
        logger.info(f"Generating viral MEME quote for archetype: {emotional_filter} ({post_format})")
        history = self.memory.load_history()
        past_quotes = set(history.get("quotes", []))
        last_caption_start = history.get("last_caption_start", "None")
        
        current_time_str = datetime.datetime.now().strftime("%A, %I:%M %p")

        feedback_section = ""
        if critic_feedback:
            feedback_section = f"\nCRITICAL FEEDBACK: {critic_feedback}\nYou MUST adjust your humor accordingly.\n"

        prompt = f"""
You are a witty, hilarious, full-time day trader running a viral meme page on X (Twitter) and Instagram.
Your followers love you because your posts are 100% RELATABLE TRADER MEMES that mock the daily struggle of trading.

DO NOT GIVE SERIOUS ADVICE. DO NOT BE A PREACHY GURU.
This post is strictly a COMEDIC MEME / RELATABLE HUMOR post.

COMEDIC STYLE: {emotional_filter}
FORMAT: {post_format}
THEME: {core_theme}
PUNCHLINE ANGLE: {narrative_angle}
{feedback_section}

MEME STYLE INSPIRATION EXAMPLES:
- POV Example: "POV: You stared at a 1-minute chart for 3 hours, took a 10-second bathroom break, and returned to a 100-pip candle leaving without you."
- Relatable Pain: "Closing a trade with +$4.50 profit because 'green is green', then watching it fly 250 pips straight to your original TP."
- Routine Roast: "My 3-step trading system: 1. Draw 14 trendlines. 2. Ignore all 14 trendlines. 3. Enter based on pure adrenaline."
- Market Reality: "Gold doesn't care about your support level, your Fibonacci retracement, or your rent due date."
- Monologue: "Me opening TradingView at 2 AM just to make sure the candles are sleeping peacefully."

STRICT RULES:
1. MUST BE HUMOROUS / MEME-FIRST: Focus on relatable retail trading comedy (moving SL to breakeven too early, revenge trading, coffee dependency, watching spread eat your profits, weekend withdrawal).
2. NO ADVICE / NO GURU FLUFF: Strictly banned phrases: 'discipline requires', 'embrace the journey', 'in the realm', 'tapestry', 'master your mind', 'the key to success'.
3. ACCURATE TIME: Current local time is {current_time_str}. If mentioning morning, afternoon, night, or day of the week, it must match this time.
4. VARIETY: Last caption started with "{last_caption_start}". Do NOT start this caption with those same words.

Generate a JSON object with these 3 keys:
{{
    "image_quote": "The meme text overlay (1-2 punchy sentences, max 30 words). NO emojis, NO hashtags.",
    "x_post_text": "The exact meme text followed by 3-4 funny/relevant hashtags (e.g. #trading #daytrader #forexmemes #xauusd).",
    "meta_caption": "A 1-2 sentence funny, conversational caption expanding on the joke for Instagram/TikTok like you're talking in a group chat. Include 1-2 emojis and 4-5 relevant hashtags."
}}
"""
        
        for attempt in range(1, 6):
            try:
                response = generate_content_with_failover(prompt)
                content = extract_clean_json(response.text)
                image_quote = content.get("image_quote", "").strip()
                
                if not image_quote:
                    continue
                    
                if image_quote not in past_quotes:
                    return content
                else:
                    logger.warning(f"Duplicate quote detected on attempt {attempt}. Regenerating...")
            except Exception as e:
                logger.error(f"Failed to generate quote on attempt {attempt}: {e}")
                
        fallback_quote = "POV: You moved your stop loss to breakeven, got wicked out by 0.2 pips, and watched price fly 200 pips to your target."
        return {
            "image_quote": fallback_quote,
            "x_post_text": f"{fallback_quote} #trading #forexmemes #daytrader #xauusd",
            "meta_caption": f"Every single time. The market saw my breakeven and took it personally. 💀☕ #daytrading #forex #tradinghumor #retailtrader"
        }

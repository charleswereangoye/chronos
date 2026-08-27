from shared.logger import get_logger
from shared.llm import generate_json_with_failover

logger = get_logger("CriticAgent")

class CriticAgent:
    def __init__(self):
        pass

    def evaluate_content(self, content: dict, persona_profile: dict) -> dict:
        """
        Evaluates the generated meme content against strict quality and humor criteria.
        Returns a dict: {"pass": True/False, "feedback": "string explaining why"}
        """
        logger.info("Evaluating meme content quality...")
        
        prompt = f"""
You are a viral Social Media Editor and Meme Critic for trader comedy accounts.
Your job is to review this generated trader meme post:

Quote: {content.get('image_quote')}
X Post: {content.get('x_post_text')}
Meta Caption: {content.get('meta_caption')}
Target Meme Archetype: {persona_profile.get('emotional_filter', 'MEME')}

CRITICAL EVALUATION CRITERIA:
1. IS IT ACTUALLY A MEME / HUMOROUS?
   - REJECT (FAIL) if it sounds like serious advice, guru preaching, or motivational quotes.
   - PASS if it's funny, sarcastic, a relatable POV, or mocks trading struggles.
2. ZERO AI CLICHÉS:
   - REJECT if it contains words like 'tapestry', 'navigate', 'profound', 'discipline requires', 'beacon'.
3. NATURAL HUMAN WRITING:
   - Does it sound like an authentic day trader texting in a chat or posting on X?

Output ONLY a JSON object:
{{
    "pass": true or false,
    "feedback": "Short specific feedback if failed (e.g., 'Too preachy, make it a funny POV meme instead')"
}}
"""
        
        try:
            result = generate_json_with_failover(
                prompt_text=prompt,
                max_attempts=2,
                default_fallback={"pass": True, "feedback": ""}
            )
            if result.get("pass"):
                logger.info("Critic Agent: Content PASSED (Valid meme format).")
            else:
                logger.warning(f"Critic Agent: Content FAILED. Feedback: {result.get('feedback')}")
            return result
        except Exception as e:
            logger.warning(f"Critic evaluation encountered exception: {e}, defaulting to PASS.")
            return {"pass": True, "feedback": ""}

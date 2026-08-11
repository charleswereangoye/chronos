import json
from shared.config import get_gemini_client_and_model
from shared.logger import get_logger
from shared.memory import MemoryManager

logger = get_logger("StrategistAgent")

def generate_content_with_failover(prompt_text):
    for attempt in [1, 2]:
        try:
            client, model_name = get_gemini_client_and_model(attempt)
            logger.info(f"Generating content using Attempt {attempt}: {model_name}")
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_text
            )
            return response
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed with error: {e}")
            if attempt == 2:
                logger.error("All Gemini model/key attempts exhausted.")
                raise e

class StrategistAgent:
    def __init__(self):
        self.memory = MemoryManager()
        
    def generate_persona(self, research_data: dict, analytics_data: dict) -> dict:
        logger.info("Generating dynamic persona based on research and analytics...")
        
        # Sort formats by score to determine weights
        format_scores = analytics_data.get('format_scores', {})
        best_format = analytics_data.get('best_performing_format', 'RELATABLE_MEME_TEXT')
        
        history = self.memory.load_history()
        last_filter = history.get("last_emotional_filter", "None")
        
        prompt = f"""
        Analyze today's market climate based on the following research:
        Macro News: {research_data['macro_news']}
        Retail Sentiment: {research_data['retail_sentiment']}
        
        And consider these historical analytics format scores: {format_scores}
        Currently, the best performing format is: {best_format}
        
        Dynamically generate a strategy that best responds to this climate and leverages the analytics.
        Instead of rigid corporate roles, select ONE Human Emotional Filter from the following 5 options:
        1. FRIENDLY_MENTOR: Warm, supportive, encouraging, written like a text to a friend.
        2. SARCASTIC_REALIST: Witty, sharp, calling out bad trading habits with humor.
        3. GROUNDED_PHILOSOPHER: Serious, deep, psychological, focused on discipline.
        4. EXHAUSTED_TRADER: Casual, tired, relatable, commenting on choppy or dead markets.
        5. HYPED_ANALYST: Energetic, focused on clean setups and momentum.
        
        CRITICAL VARIETY INSTRUCTION:
        The previously used emotional filter was: {last_filter}. 
        Unless the market climate strictly demands repeating the exact same filter, you MUST select a DIFFERENT emotional filter to maintain audience engagement. Do not fall into a loop of repeating the same filter.
        
        Also explicitly select a 'post_format' from the following:
        - RELATABLE_MEME_TEXT
        - SARCASM_HOT_TAKE
        - ENGAGEMENT_QUESTION
        - RAW_FRIEND_ADVICE
        
        Output ONLY a JSON object with the following keys, no markdown wrappers:
        - "emotional_filter"
        - "post_format"
        - "core_theme"
        - "narrative_angle"
        """
        
        try:
            response = generate_content_with_failover(prompt)
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            persona = json.loads(raw_text)
            return persona
        except Exception as e:
            logger.error(f"Failed to generate dynamic persona: {e}")
            return {
                "emotional_filter": "GROUNDED_PHILOSOPHER",
                "post_format": "RAW_FRIEND_ADVICE",
                "core_theme": "Avoiding retail liquidity traps during high inflation news",
                "narrative_angle": "Focus on capital preservation over quick profits"
            }

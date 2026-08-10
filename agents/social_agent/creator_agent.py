import json
from shared.config import get_gemini_client_and_model
from shared.logger import get_logger
from shared.memory import MemoryManager

logger = get_logger("CreatorAgent")

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

class CreatorAgent:
    def __init__(self):
        self.memory = MemoryManager()
        
    def generate_unique_quote(self, persona_profile: dict) -> dict:
        emotional_filter = persona_profile.get('emotional_filter', 'GROUNDED_PHILOSOPHER')
        logger.info(f"Creating content based on dynamic emotional filter: {emotional_filter}")
        history = self.memory.load_history()
        past_quotes = history.get("quotes", [])
        last_caption_start = history.get("last_caption_start", "None")
        
        post_format = persona_profile.get('post_format', 'RELATABLE_MEME_TEXT')
        prompt = f"""
        You are a highly authentic human trader posting on social media.
        Apply the following EMOTIONAL FILTER to your delivery style: {emotional_filter}
        - If mode is FRIENDLY_MENTOR, make it warm and encouraging.
        - If mode is SARCASTIC_REALIST, make it funny and sharp.
        - If mode is GROUNDED_PHILOSOPHER, make it reflective and deep.
        - If mode is EXHAUSTED_TRADER, make it casual, tired, and relatable.
        - If mode is HYPED_ANALYST, make it energetic and focused.
        
        Keep the core trading wisdom intelligent and valuable.
        
        Theme: {persona_profile.get('core_theme', 'Trading')}
        Angle: {persona_profile.get('narrative_angle', 'Discipline')}
        Selected Post Format: {post_format}
        
        Generate a JSON object with three keys: 'image_quote', 'x_post_text', and 'meta_caption'. Do not include markdown formatting like ```json.
        
        CRITICAL STANDARDS (Humanization):
        - STRICTLY BAN AI SLANG: Do NOT use words like tapestry, landscape, navigate, profound, discipline requires, institutional, realm, embark, pivotal, beacon.
        - ENFORCE NATURAL WRITING: Write in short, conversational sentences like an authentic trader texting on WhatsApp or posting on X. Allow lowercase text, casual phrasing, and trader slang.
        - DO NOT reference specific real-time market events or specific days of the week. Keep it TIMELESS.
        
        1. 'image_quote': A highly engaging, punchy quote based strictly on the emotional filter. Max 2 sentences. NO emojis and NO hashtags in the quote.
        2. 'x_post_text': The exact text of the 'image_quote', but with 3-4 relevant hashtags added at the end (e.g., "#trading #forex"). This is for Twitter traction.
        3. 'meta_caption': A 1-3 sentence engaging caption that perfectly matches the mood and expands on the quote for Instagram/Facebook. 
        - CRITICAL VARIETY RULE: The last time you posted, the caption started with the words: "{last_caption_start}". You MUST NOT start this new caption with those same words.
        - Use 1-2 relevant emojis naturally in the caption. Include 4-5 highly relevant hashtags at the end.
        """
        
        while True:
            response = generate_content_with_failover(prompt)
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                
            try:
                content = json.loads(raw_text)
                image_quote = content.get("image_quote", "")
                
                if image_quote not in past_quotes:
                    # Memory is saved later in the workflow by SocialAgentCoordinator
                    return content
                else:
                    logger.warning("Duplicate quote detected. Regenerating...")
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON. Regenerating...")

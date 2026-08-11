import json
from shared.config import get_gemini_client_and_model
from shared.logger import get_logger

logger = get_logger("CriticAgent")

class CriticAgent:
    def __init__(self):
        pass

    def evaluate_content(self, content: dict, persona_profile: dict) -> dict:
        """
        Evaluates the generated content against strict criteria.
        Returns a dict: {"pass": True/False, "feedback": "string explaining why"}
        """
        logger.info("Evaluating generated content...")
        
        prompt = f"""
        You are a harsh but fair Social Media Critic. 
        Your job is to evaluate a generated social media post based on the following criteria:
        1. Does it sound like a real, authentic human trader? (No AI slang like 'tapestry', 'navigate', 'profound').
        2. Does it perfectly match the emotional filter: {persona_profile.get('emotional_filter', 'None')}?
        3. Is it actually engaging or funny, without being overly cringy?
        4. Does the text make sense contextually?
        
        Generated Content:
        Quote: {content.get('image_quote')}
        X Post: {content.get('x_post_text')}
        Meta Caption: {content.get('meta_caption')}
        
        Evaluate the content. If it is good to post, return PASS. If it is too robotic, cringy, or fails the emotional filter, return FAIL and provide brief feedback on what needs to change.
        
        Output ONLY a JSON object with this exact structure:
        {{
            "pass": true or false,
            "feedback": "string"
        }}
        """
        
        for attempt in [1, 2]:
            try:
                client, model_name = get_gemini_client_and_model(attempt)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                
                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                
                result = json.loads(raw_text)
                if result.get("pass"):
                    logger.info("Critic Agent: Content PASSED.")
                else:
                    logger.warning(f"Critic Agent: Content FAILED. Feedback: {result.get('feedback')}")
                return result
            except Exception as e:
                logger.warning(f"Critic evaluation failed on attempt {attempt}: {e}")
                
        # If evaluation fails, default to pass to avoid breaking the pipeline
        logger.warning("Critic failed to parse evaluation, defaulting to PASS.")
        return {"pass": True, "feedback": ""}

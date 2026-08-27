import os
import json
import logging
import time
import random
from typing import Any, Optional, Dict, Tuple
import httpx
from google import genai
from google.genai import types
from shared.config import get_gemini_client_and_model

logger = logging.getLogger("LLMHelper")

class GenericLLMResponse:
    def __init__(self, text: str):
        self.text = text

def extract_clean_json(text: str) -> Dict[str, Any]:
    """Extracts and parses a JSON object or array from LLM response text."""
    clean = text.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()
    
    # Try direct parse
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Search for first { or [ and matching } or ]
        first_brace = clean.find("{")
        last_brace = clean.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            return json.loads(clean[first_brace:last_brace+1])
            
        first_bracket = clean.find("[")
        last_bracket = clean.rfind("]")
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            return json.loads(clean[first_bracket:last_bracket+1])
            
        raise

def query_groq_fallback(
    prompt_text: str,
    system_instruction: Optional[str] = None,
    temperature: Optional[float] = None
) -> Optional[GenericLLMResponse]:
    """Queries Groq Free Tier API (Llama 3.3 70B) if GROQ_API_KEY is configured."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return None
        
    try:
        logger.info("Failing over to Groq Free Tier (Llama 3.3 70B)...")
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt_text})
        
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": temperature if temperature is not None else 0.7
            },
            timeout=25.0
        )
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return GenericLLMResponse(text=content)
        else:
            logger.warning(f"Groq API returned status {response.status_code}: {response.text}")
    except Exception as e:
        logger.warning(f"Groq API fallback failed: {e}")
    return None

def generate_content_with_failover(
    prompt_text: str,
    system_instruction: Optional[str] = None,
    temperature: Optional[float] = None,
    max_attempts: int = 3
) -> Any:
    """
    Generates content using Gemini with automatic key and model failover,
    with secondary zero-cost failover to Groq Llama 3.3 70B if configured.
    """
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            client, model_name = get_gemini_client_and_model(attempt)
            logger.info(f"LLM Request (Attempt {attempt}/{max_attempts}) with model: {model_name}")
            
            config = types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
            if system_instruction:
                config.system_instruction = system_instruction
            if temperature is not None:
                config.temperature = temperature
                
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_text,
                config=config
            )
            return response
        except Exception as e:
            logger.warning(f"Gemini attempt {attempt} failed: {e}")
            last_error = e
            time.sleep(0.5 * attempt)
            
    # If Gemini attempts exhausted, attempt Groq Free Tier
    groq_resp = query_groq_fallback(prompt_text, system_instruction, temperature)
    if groq_resp:
        return groq_resp

    logger.error("All LLM providers and attempts exhausted.")
    raise last_error or RuntimeError("Failed to generate content after all attempts.")

def generate_json_with_failover(
    prompt_text: str,
    system_instruction: Optional[str] = None,
    temperature: Optional[float] = None,
    max_attempts: int = 3,
    default_fallback: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates structured JSON with automatic provider failover and JSON parsing resilience.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            response = generate_content_with_failover(
                prompt_text=prompt_text,
                system_instruction=system_instruction,
                temperature=temperature,
                max_attempts=1
            )
            return extract_clean_json(response.text)
        except Exception as e:
            logger.warning(f"JSON generation attempt {attempt} failed: {e}")
            if attempt == max_attempts:
                # Try Groq fallback before default
                groq_resp = query_groq_fallback(prompt_text, system_instruction, temperature)
                if groq_resp:
                    try:
                        return extract_clean_json(groq_resp.text)
                    except Exception:
                        pass
                        
                if default_fallback is not None:
                    logger.warning("Returning default JSON fallback after exhaustion.")
                    return default_fallback
                raise
            time.sleep(0.5 * attempt)
            
    if default_fallback is not None:
        return default_fallback
    raise RuntimeError("Failed to generate valid JSON.")

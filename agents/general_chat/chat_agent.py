import os
import json
import logging
import time
import re
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from shared.config import get_gemini_client_and_model

logger = logging.getLogger("ChatAgent")

class ChatAgent:
    """A general AI chatbot agent with conversational memory and multimodal (voice/image) support."""
    
    def __init__(self, memory_size: int = 15):
        self.memory_size = memory_size
        self.state_dir = os.path.join(os.path.dirname(__file__), "state")
        os.makedirs(self.state_dir, exist_ok=True)
        self.memory_file = os.path.join(self.state_dir, "chat_memory.json")
        self.memories: Dict[str, List[Dict[str, str]]] = self._load_memory()
        
        self.personas = {
            "Standard": (
                "You are Chronos, an advanced AI assistant created to help Charles Were Angoye build his tech and trading empire. "
                "Charles is a Software Engineering student in his 2nd year at The African Leadership University. "
                "He is a Full-Stack developer (Next.js, Node.js, TypeScript, PostgreSQL) currently working on 'Trajour', a comprehensive trading journal, "
                "and an engine for executing trade copying without MT5. "
                "He is also a Forex trader focusing on XAUUSD using Performance-Based Smart Money Concepts (SMC). "
                "You are concise, highly intelligent, practical, and you act as his right-hand partner."
            ),
            "Senior Dev": "You are a Senior Staff Software Engineer. Your goal is to mentor Charles. Focus on Python, React, and Node.js. Be strict but highly educational.",
            "Brainstorming": "You are a creative sounding board. Validate his ideas, suggest counter-arguments, and expand on the possibilities."
        }

    def _load_memory(self) -> Dict[str, List[Dict[str, str]]]:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load chat memory: {e}")
        return {}

    def _save_memory(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save chat memory: {e}")

    def clear_memory(self, user_id: str):
        """Wipes the conversation history for a specific user."""
        if str(user_id) in self.memories:
            self.memories[str(user_id)] = []
            self._save_memory()

    def _get_history(self, user_id: str) -> List[Dict[str, str]]:
        if user_id not in self.memories:
            self.memories[user_id] = []
        return self.memories[user_id]

    def _add_to_history(self, user_id: str, role: str, text: str):
        history = self._get_history(user_id)
        history.append({"role": role, "content": text})
        # Keep only the last N messages to prevent context overflow
        if len(history) > self.memory_size * 2:
            self.memories[user_id] = history[-(self.memory_size * 2):]
        self._save_memory()

    async def chat(
        self, 
        user_id: int, 
        message: Optional[str] = None, 
        media_path: Optional[str] = None, 
        persona: str = "Standard"
    ) -> str:
        """Processes a chat request, optionally with a voice note or image."""
        uid = str(user_id)
        system_instruction = self.personas.get(persona, self.personas["Standard"])
        history = self._get_history(uid)
        
        # Build contents array
        contents = []
        
        # 1. Add historical context
        if history:
            history_text = "Previous conversation context:\n"
            for msg in history:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_text += f"[{role}]: {msg['content']}\n"
            contents.append(history_text)
            
        # 2. Add media (Voice note, image, etc.)
        client, model_name = get_gemini_client_and_model()
        uploaded_file = None
        
        if media_path and os.path.exists(media_path):
            try:
                logger.info(f"Uploading media to Gemini: {media_path}")
                
                # Determine explicit mime type to prevent Google GenAI SDK errors
                mime_type = None
                if media_path.endswith(".ogg"):
                    mime_type = "audio/ogg"
                elif media_path.endswith(".mp3"):
                    mime_type = "audio/mp3"
                elif media_path.endswith(".wav"):
                    mime_type = "audio/wav"
                elif media_path.endswith(".m4a"):
                    mime_type = "audio/m4a"
                elif media_path.endswith(".jpg") or media_path.endswith(".jpeg"):
                    mime_type = "image/jpeg"
                elif media_path.endswith(".png"):
                    mime_type = "image/png"
                
                if mime_type:
                    uploaded_file = client.files.upload(file=media_path, config={'mime_type': mime_type})
                else:
                    uploaded_file = client.files.upload(file=media_path)
                
                # If it's audio, Gemini might need a few seconds to process it
                if media_path.endswith((".ogg", ".mp3", ".wav", ".m4a")):
                    time.sleep(2) # Give Gemini a moment to digest the audio
                    
                contents.append(uploaded_file)
            except Exception as e:
                logger.error(f"Failed to upload media to Gemini: {e}")
                return f"❌ Failed to process media file: {str(e)}"
        
        # 3. Add the current text message
        if message:
            contents.append(message)
        elif uploaded_file and media_path.endswith((".ogg", ".mp3", ".wav", ".m4a")):
            contents.append("Please transcribe this voice note and respond to it.")
        
        if not contents:
            return "No valid input provided."

        # Execute Gemini generation
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
            
            logger.info(f"Generating chat response using {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            
            raw_reply = response.text.strip()
            
            # Save interaction to memory (don't save the raw audio, just the text)
            if message:
                self._add_to_history(uid, "user", message)
            elif media_path:
                self._add_to_history(uid, "user", "[Sent an audio/media file]")
                
            self._add_to_history(uid, "assistant", raw_reply)
            
            # Format the output cleanly for Telegram HTML
            reply_text = self._format_for_telegram(raw_reply)
            
            # Cleanup uploaded file from Gemini server to save quota
            if uploaded_file:
                try:
                    client.files.delete(name=uploaded_file.name)
                except Exception as e:
                    logger.warning(f"Failed to delete uploaded file from Gemini: {e}")
                    
            return reply_text

        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            return f"❌ AI encountered an error: {str(e)}"

    def _format_for_telegram(self, text: str) -> str:
        """Converts Markdown to strict Telegram-compatible HTML."""
        # 1. Escape HTML characters to prevent Telegram parsing crashes
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # 2. Convert markdown headers (# Header) to Bold Uppercase
        def header_replacer(match):
            return f"<b>{match.group(1).upper()}</b>"
        text = re.sub(r'^#+\s+(.*)$', header_replacer, text, flags=re.MULTILINE)
        
        # 3. Convert **bold** to <b>bold</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # 4. Convert list items (* or -) to bullet points (•)
        text = re.sub(r'^\s*[\*\-]\s+', '• ', text, flags=re.MULTILINE)
        
        # 5. Convert remaining *italic* or _italic_ to <i>italic</i>
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
        
        # 6. Convert `code` to <code>code</code>
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        
        return text

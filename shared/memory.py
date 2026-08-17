import json
import os
from shared.config import HISTORY_FILE_PATH
from shared.logger import get_logger

logger = get_logger("MemoryManager")

class MemoryManager:
    def __init__(self):
        self.history_path = HISTORY_FILE_PATH
        
    def load_history(self) -> dict:
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return {"quotes": data, "last_caption_start": "None", "last_emotional_filter": "None", "used_video_templates": []}
                    if "last_emotional_filter" not in data:
                        data["last_emotional_filter"] = "None"
                    if "used_video_templates" not in data:
                        data["used_video_templates"] = []
                    return data
            except json.JSONDecodeError:
                logger.warning("history.json decode error, returning default.")
        
        return {"quotes": [], "last_caption_start": "None", "last_emotional_filter": "None", "used_video_templates": []}

    def save_history(self, history_data: dict):
        if "quotes" in history_data:
            history_data["quotes"] = history_data["quotes"][-50:]
        if "used_video_templates" in history_data:
            history_data["used_video_templates"] = history_data["used_video_templates"][-50:]
            
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=4)
        logger.info("History saved successfully.")

    def save_post(self, quote: str, caption: str, emotional_filter: str = "None"):
        history_data = self.load_history()
        history_data["quotes"].append(quote)
        
        words = caption.split()
        new_start = " ".join(words[:4]) if len(words) >= 4 else caption
        history_data["last_caption_start"] = new_start
        history_data["last_emotional_filter"] = emotional_filter
        
        self.save_history(history_data)

    def save_video_post(self, overlay_text: str, caption: str, emotion: str, video_template_name: str):
        history_data = self.load_history()
        history_data["used_video_templates"].append(video_template_name)
        history_data["quotes"].append(overlay_text)
        
        words = caption.split()
        new_start = " ".join(words[:4]) if len(words) >= 4 else caption
        history_data["last_caption_start"] = new_start
        history_data["last_emotional_filter"] = emotion
        
        self.save_history(history_data)

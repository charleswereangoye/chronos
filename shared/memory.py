import json
import os
import tempfile
from shared.config import HISTORY_FILE_PATH
from shared.logger import get_logger

logger = get_logger("MemoryManager")

class MemoryManager:
    def __init__(self):
        self.history_path = HISTORY_FILE_PATH
        
    def load_history(self) -> dict:
        default_state = {
            "quotes": [],
            "last_caption_start": "None",
            "last_emotional_filter": "None",
            "used_video_templates": []
        }
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return {**default_state, "quotes": data}
                    if not isinstance(data, dict):
                        return default_state
                    if "quotes" not in data:
                        data["quotes"] = []
                    if "last_caption_start" not in data:
                        data["last_caption_start"] = "None"
                    if "last_emotional_filter" not in data:
                        data["last_emotional_filter"] = "None"
                    if "used_video_templates" not in data:
                        data["used_video_templates"] = []
                    return data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"history.json load error ({e}), returning default state.")
        
        return default_state

    def save_history(self, history_data: dict):
        if "quotes" in history_data:
            history_data["quotes"] = history_data["quotes"][-50:]
        if "used_video_templates" in history_data:
            history_data["used_video_templates"] = history_data["used_video_templates"][-50:]
            
        target_dir = os.path.dirname(self.history_path)
        os.makedirs(target_dir, exist_ok=True)
        
        # Atomic write via tempfile in same directory
        temp_file = os.path.join(target_dir, f".tmp_history_{os.getpid()}.json")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=4)
            os.replace(temp_file, self.history_path)
            logger.info("History saved atomically.")
        except Exception as e:
            logger.error(f"Failed to save history atomically: {e}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

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

import json
import os
import tempfile
import threading
from typing import Dict, Any, List, Optional
from shared.config import HISTORY_FILE_PATH
from shared.logger import get_logger

logger = get_logger("MemoryManager")

class MemoryManager:
    """
    Thread-safe, atomic persistent memory manager for agent state, history buffers,
    and deduplication vectors.
    """
    _lock = threading.Lock()

    def __init__(self, history_path: Optional[str] = None):
        self.history_path = history_path or HISTORY_FILE_PATH

    def load_history(self) -> dict:
        default_state = {
            "quotes": [],
            "last_caption_start": "None",
            "last_emotional_filter": "None",
            "used_video_templates": [],
            "job_applications": [],
            "metadata": {}
        }
        with self._lock:
            if os.path.exists(self.history_path):
                try:
                    with open(self.history_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            return {**default_state, "quotes": data}
                        if not isinstance(data, dict):
                            return default_state
                        
                        # Ensure all default keys exist
                        for k, v in default_state.items():
                            if k not in data:
                                data[k] = v
                        return data
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"history.json load error ({e}), returning default state.")
            
            return default_state

    def save_history(self, history_data: dict):
        with self._lock:
            # Enforce circular buffer bounds
            if "quotes" in history_data:
                history_data["quotes"] = history_data["quotes"][-50:]
            if "used_video_templates" in history_data:
                history_data["used_video_templates"] = history_data["used_video_templates"][-50:]
            if "job_applications" in history_data:
                history_data["job_applications"] = history_data["job_applications"][-100:]
                
            target_dir = os.path.dirname(self.history_path)
            os.makedirs(target_dir, exist_ok=True)
            
            # Atomic write via tempfile in same directory
            temp_file = os.path.join(target_dir, f".tmp_history_{os.getpid()}_{threading.get_ident()}.json")
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

    def record_job_application(self, job_title: str, company: str, url: str):
        history_data = self.load_history()
        if "job_applications" not in history_data:
            history_data["job_applications"] = []
        history_data["job_applications"].append({
            "title": job_title,
            "company": company,
            "url": url
        })
        self.save_history(history_data)

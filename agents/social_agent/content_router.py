import random
from shared.logger import get_logger

logger = get_logger("ContentRouter")

class ContentRouter:
    def __init__(self):
        pass
        
    def decide_content_path(self, strategy_data: dict = None) -> str:
        """
        Decides whether to route the pipeline to a Static Graphic or a Video Meme.
        Uses a weighted random decision for 50/50 balance.
        """
        path = random.choices(["static", "video"], weights=[0.5, 0.5])[0]
        logger.info(f"Content Router selected path: {path.upper()}")
        return path

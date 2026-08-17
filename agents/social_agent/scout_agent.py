import os
import time
import glob
from yt_dlp import YoutubeDL
from playwright.async_api import async_playwright
from shared.logger import get_logger

logger = get_logger("ScoutAgent")

class ScoutAgent:
    def __init__(self):
        self.base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "video_templates")
        os.makedirs(self.base_dir, exist_ok=True)
        
    async def scrape_reddit_memes(self, limit=5):
        logger.info("Scraping r/MemeTemplatesOfficial for video templates...")
        search_urls = [
            "https://www.reddit.com/r/MemeTemplatesOfficial/search/?q=green+screen&restrict_sr=1&sort=top",
            "https://www.reddit.com/r/MemeTemplatesOfficial/search/?q=template+video&restrict_sr=1&sort=top"
        ]
        
        ydl_opts = {
            'outtmpl': os.path.join(self.base_dir, 'general', '%(id)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'match_filter': lambda info, *args, **kwargs: 'Duration is too long' if info.get('duration', 0) > 60 else None,
            'max_downloads': limit,
            'quiet': True,
            'noplaylist': True
        }
        
        os.makedirs(os.path.join(self.base_dir, 'general'), exist_ok=True)
        
        for url in search_urls:
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                logger.info(f"Successfully downloaded templates from {url}")
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")

    def download_youtube_meme(self, query: str, emotion: str):
        logger.info(f"Downloading YouTube meme for {emotion}: {query}")
        target_dir = os.path.join(self.base_dir, emotion)
        os.makedirs(target_dir, exist_ok=True)
        
        ydl_opts = {
            'outtmpl': os.path.join(target_dir, '%(id)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'match_filter': lambda info, *args, **kwargs: 'Duration is too long' if info.get('duration', 0) > 30 else None,
            'max_downloads': 1,
            'quiet': True,
            'default_search': 'ytsearch3'
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([query])
            logger.info("Successfully downloaded YouTube meme.")
        except Exception as e:
            logger.error(f"Failed to download YouTube meme: {e}")

    def cleanup_old_templates(self, max_days=30):
        logger.info(f"Cleaning up templates older than {max_days} days...")
        current_time = time.time()
        for root, _, files in os.walk(self.base_dir):
            for file in files:
                if file.endswith('.mp4'):
                    file_path = os.path.join(root, file)
                    creation_time = os.path.getctime(file_path)
                    if (current_time - creation_time) > (max_days * 86400):
                        os.remove(file_path)
                        logger.info(f"Deleted old template: {file_path}")

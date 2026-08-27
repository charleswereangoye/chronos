import os
import json
import random
import traceback
from moviepy import VideoFileClip, CompositeVideoClip, ColorClip, ImageClip
from shared.config import OUTPUT_DIR
from shared.logger import get_logger
from shared.llm import generate_json_with_failover

logger = get_logger("VideoMemeAgent")

class VideoMemeAgent:
    def __init__(self):
        self.base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "video_templates")
        
    def generate_meme_content(self, emotion_category: str) -> dict:
        logger.info(f"Generating meme content for emotion: {emotion_category}")
        prompt = f"""
        You are a highly authentic human day trader creating a viral short-form video meme.
        The current vibe/emotion of the meme is: {emotion_category}.
        
        Generate a JSON object with three keys:
        - "overlay_text": A punchy, sarcastic, relatable 1-2 sentence text overlay. Format it like a POV (e.g., "POV: You finally closed your losing trade just to watch the chart immediately moon without you").
        - "caption": A 1-2 sentence engaging caption expanding on the meme for TikTok/Reels.
        - "hashtags": A string of 5-8 algorithm-optimized hashtags (e.g. "#trading #forex #daytrader").
        
        Output ONLY the JSON object, no markdown wrappers.
        """
        fallback = {
            "overlay_text": "POV: When the market does exactly what you said it wouldn't do.",
            "caption": "It really do be like that sometimes.",
            "hashtags": "#trading #forex #xauusd"
        }
        try:
            return generate_json_with_failover(prompt_text=prompt, max_attempts=2, default_fallback=fallback)
        except Exception as e:
            logger.error(f"Failed to generate meme content: {e}")
            return fallback
            
    def generate_caption_for_meme(self, meme_text: str) -> dict:
        logger.info("Generating caption and hashtags for custom meme quote.")
        prompt = f"""
        You are a highly authentic human day trader creating a viral short-form video meme.
        The meme has the following text overlay: "{meme_text}".
        
        Generate a JSON object with two keys:
        - "caption": A 1-2 sentence engaging caption expanding on the meme for TikTok/Reels.
        - "hashtags": A string of 5-8 algorithm-optimized hashtags (e.g. "#trading #forex #daytrader").
        
        Output ONLY the JSON object, no markdown wrappers.
        """
        fallback = {
            "caption": "Just trading things",
            "hashtags": "#trading #forex #crypto"
        }
        try:
            return generate_json_with_failover(prompt_text=prompt, max_attempts=2, default_fallback=fallback)
        except Exception as e:
            logger.error(f"Failed to generate caption: {e}")
            return fallback

    def select_template(self, emotion_category: str = "general") -> str:
        emotion_dir = os.path.join(self.base_dir, emotion_category)
        if not os.path.exists(emotion_dir):
            emotion_dir = os.path.join(self.base_dir, "general")
            
        videos = []
        if os.path.exists(emotion_dir):
            videos = [f for f in os.listdir(emotion_dir) if f.endswith('.mp4')]
            
        if not videos:
            logger.warning("No video templates found in assets category. Checking base assets...")
            root_assets = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
            if os.path.exists(root_assets):
                videos = [f for f in os.listdir(root_assets) if f.endswith('.mp4')]
                if videos:
                    return os.path.join(root_assets, random.choice(videos))
            logger.error("No video templates found anywhere in assets!")
            return ""
            
        return os.path.join(emotion_dir, random.choice(videos))

    def render_video(self, header_image_path: str, template_video_path: str) -> str:
        logger.info(f"Rendering video meme using template: {template_video_path}")
        if not template_video_path or not os.path.exists(template_video_path):
            logger.error(f"Invalid template_video_path: {template_video_path}")
            return ""
            
        output_file = os.path.join(OUTPUT_DIR, f"daily_reel_{random.randint(1000, 9999)}.mp4")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        clip = None
        final_clip = None
        try:
            clip = VideoFileClip(template_video_path)
            
            # Target 1080x1920 (9:16)
            target_w, target_h = 1080, 1920
            
            bg_clip = ColorClip(size=(target_w, target_h), color=(15, 15, 15)).with_duration(clip.duration)
            
            # Load the Twitter-style header image
            header_clip = ImageClip(header_image_path)
            header_clip = header_clip.resized(width=target_w).with_duration(clip.duration)
            
            # The video covers exactly the remaining height
            remaining_h = target_h - header_clip.h
            
            aspect_ratio = clip.w / clip.h
            target_aspect_ratio = target_w / remaining_h
            
            if aspect_ratio > target_aspect_ratio:
                resized_clip = clip.resized(height=remaining_h)
                resized_clip = resized_clip.cropped(x_center=resized_clip.w/2, width=target_w)
            else:
                resized_clip = clip.resized(width=target_w)
                resized_clip = resized_clip.cropped(y_center=resized_clip.h/2, height=remaining_h)
            
            final_clip = CompositeVideoClip([
                bg_clip, 
                header_clip.with_position(('center', 0)), 
                resized_clip.with_position(('center', header_clip.h))
            ])
            
            logger.info("Writing final MP4 using MoviePy...")
            final_clip.write_videofile(
                output_file, 
                codec="libx264", 
                audio_codec="aac", 
                bitrate="8000k", 
                fps=30, 
                preset="medium", 
                threads=4, 
                logger=None
            )
            return output_file
        except Exception as e:
            logger.error(f"Failed to render video: {e}")
            traceback.print_exc()
            return ""
        finally:
            if clip is not None:
                try:
                    clip.close()
                except Exception:
                    pass
            if final_clip is not None:
                try:
                    final_clip.close()
                except Exception:
                    pass

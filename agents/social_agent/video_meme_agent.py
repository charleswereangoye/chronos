import os
import json
import random
import traceback
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip, ImageClip
from shared.config import get_gemini_client_and_model, OUTPUT_DIR
from shared.logger import get_logger

logger = get_logger("VideoMemeAgent")

def generate_content_with_failover(prompt_text):
    for attempt in [1, 2]:
        try:
            client, model_name = get_gemini_client_and_model(attempt)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_text
            )
            return response
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {e}")
            if attempt == 2:
                raise e

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
        response = generate_content_with_failover(prompt)
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
        try:
            return json.loads(raw_text)
        except Exception as e:
            logger.error(f"Failed to parse meme content: {e}")
            return {
                "overlay_text": "POV: When the market does exactly what you said it wouldn't do.",
                "caption": "It really do be like that sometimes.",
                "hashtags": "#trading #forex #xauusd"
            }
            
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
        response = generate_content_with_failover(prompt)
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
        try:
            return json.loads(raw_text)
        except Exception as e:
            logger.error(f"Failed to parse caption: {e}")
            return {
                "caption": "Just trading things",
                "hashtags": "#trading #forex #crypto"
            }

    def select_template(self, emotion_category: str = "general") -> str:
        emotion_dir = os.path.join(self.base_dir, emotion_category)
        if not os.path.exists(emotion_dir):
            emotion_dir = os.path.join(self.base_dir, "general")
            
        videos = []
        if os.path.exists(emotion_dir):
            videos = [f for f in os.listdir(emotion_dir) if f.endswith('.mp4')]
            
        if not videos:
            logger.error("No video templates found in assets! Please run ScoutAgent first.")
            return ""
            
        return os.path.join(emotion_dir, random.choice(videos))

    def render_video(self, header_image_path: str, template_video_path: str) -> str:
        logger.info(f"Rendering video meme using template: {template_video_path}")
        if not template_video_path or not os.path.exists(template_video_path):
            logger.error("Invalid template_video_path!")
            return ""
            
        output_file = os.path.join(OUTPUT_DIR, "daily_reel.mp4")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        try:
            clip = VideoFileClip(template_video_path)
            
            # No trimming, keep the original template duration

            
            # Target 1080x1920 (9:16)
            target_w, target_h = 1080, 1920
            
            bg_clip = ColorClip(size=(target_w, target_h), color=(15, 15, 15)).with_duration(clip.duration)
            
            # Load the Twitter-style header image
            header_clip = ImageClip(header_image_path)
            
            # Resize header to width 1080 (maintaining aspect ratio)
            header_clip = header_clip.resized(width=target_w).with_duration(clip.duration)
            
            # The video covers exactly the remaining height
            remaining_h = target_h - header_clip.h
            
            aspect_ratio = clip.w / clip.h
            target_aspect_ratio = target_w / remaining_h
            
            if aspect_ratio > target_aspect_ratio:
                # Video is wider. Match height, crop width.
                resized_clip = clip.resized(height=remaining_h)
                resized_clip = resized_clip.cropped(x_center=resized_clip.w/2, width=target_w)
            else:
                # Video is taller. Match width, crop height.
                resized_clip = clip.resized(width=target_w)
                resized_clip = resized_clip.cropped(y_center=resized_clip.h/2, height=remaining_h)
            
            # Assemble the final video
            final_clip = CompositeVideoClip([
                bg_clip, 
                header_clip.with_position(('center', 0)), 
                resized_clip.with_position(('center', header_clip.h))
            ])
            
            logger.info("Writing final MP4 using MoviePy...")
            final_clip.write_videofile(output_file, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", threads=4, logger=None)
            
            clip.close()
            final_clip.close()
            return output_file
        except Exception as e:
            logger.error(f"Failed to render video: {e}")
            traceback.print_exc()
            return ""

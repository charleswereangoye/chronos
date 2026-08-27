import os
import base64
import logging
import asyncio
import io
import PIL.Image
from shared.config import get_gemini_client_and_model
from shared.video_sync import get_video_duration

logger = logging.getLogger("VisionAgent")

class VisionAgent:
    def __init__(self):
        pass

    async def extract_keyframes(self, video_path: str, num_frames: int = 4) -> list:
        """Extracts multiple keyframes from the video and returns their base64 encodings."""
        duration = get_video_duration(video_path)
        if duration == 0:
            logger.warning(f"Could not determine duration for {video_path}")
            return []

        # Target timestamps (e.g. 20%, 40%, 60%, 80%)
        fractions = [i/(num_frames+1) for i in range(1, num_frames+1)]
        timestamps = [duration * f for f in fractions]
        
        base64_frames = []
        temp_dir = os.path.join(os.path.dirname(video_path), "temp_keyframes")
        os.makedirs(temp_dir, exist_ok=True)
        
        for i, ts in enumerate(timestamps):
            frame_path = os.path.join(temp_dir, f"frame_{i}.jpg")
            cmd = ["ffmpeg", "-y", "-ss", str(ts), "-i", video_path, "-vframes", "1", "-q:v", "2", frame_path]
            
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await process.wait()
            
            if os.path.exists(frame_path):
                with open(frame_path, "rb") as image_file:
                    base64_frames.append(base64.b64encode(image_file.read()).decode('utf-8'))
                os.remove(frame_path)
                
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
            
        return base64_frames

    async def identify_scene(self, video_path: str) -> str:
        """Identifies a scene using strictly Google Gemini AI."""
        logger.info(f"Extracting keyframes for {video_path}...")
        base64_frames = await self.extract_keyframes(video_path, num_frames=4)
        
        if not base64_frames:
            logger.error("Failed to extract keyframes.")
            return ""

        prompt = (
            "You are an expert in pop culture, movies, and internet memes. "
            "Look past any text overlays. Identify the exact original movie, TV show, or viral meme scene shown. "
            "Output ONLY a clean YouTube search query to find the blank, unedited version of this scene "
            "(e.g., 'Wolf of Wall street chest thump blank template')."
        )

        logger.info("Attempting primary vision engine: Google Gemini...")
        try:
            client, model = get_gemini_client_and_model()
            
            contents = [prompt]
            for b64 in base64_frames:
                image_data = base64.b64decode(b64)
                image = PIL.Image.open(io.BytesIO(image_data))
                contents.append(image)
                
            response = client.models.generate_content(
                model=model,
                contents=contents
            )
            
            search_query = response.text.strip().replace('"', '').replace("'", "")
            logger.info(f"Gemini identified scene: {search_query}")
            return search_query
        except Exception as e:
            logger.error(f"Gemini processing failed: {e}")
            return ""

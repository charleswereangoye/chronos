import os
import json
import time
import requests
import traceback
from datetime import datetime
from playwright.async_api import async_playwright
from twikit import Client

from shared.config import (
    TEMPLATES_DIR, OUTPUT_DIR, STATE_FILE_PATH,
    FB_PAGE_ID, IG_USER_ID, META_PAGE_ACCESS_TOKEN
)
from shared.logger import get_logger

logger = get_logger("PublisherAgent")

class PublisherAgent:
    def __init__(self):
        pass

    async def render_tweet_image(self, quote_text: str, filename: str = "daily_quote.png") -> str:
        logger.info(f"Rendering high-resolution asset to {filename}...")
        template_path = TEMPLATES_DIR / "tweet_template.html"
        output_image_path = OUTPUT_DIR / filename
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        raw_time = datetime.now().strftime("%I:%M %p · %b %d, %Y")
        current_time = raw_time.lstrip("0").replace(" 0", " ")
        
        rendered_html = html_content.replace("{{ quote }}", quote_text)
        rendered_html = rendered_html.replace("{{ timestamp }}", current_time)
        rendered_html = rendered_html.replace("8:00 AM · {{ date }}", current_time)
        
        import uuid
        temp_html_path = TEMPLATES_DIR / f"temp_render_{uuid.uuid4().hex}.html"
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)
            
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1080, "height": 1350})
            await page.goto(f"file://{os.path.abspath(temp_html_path)}")
            
            if "video" in filename:
                # Remove timestamp and format specifically for video header
                await page.evaluate("""
                    var ts = document.querySelector('.text-gray-500.text-\\\\[30px\\\\].pt-4');
                    if(ts) ts.style.display = 'none';
                    var card = document.getElementById('tweet-card');
                    card.style.backgroundColor = '#000000';
                    card.style.maxWidth = '1080px';
                    card.style.width = '1080px';
                    card.style.padding = '80px 80px 40px 80px';
                """)
                await page.locator('#tweet-card').screenshot(path=str(output_image_path))
            else:
                await page.screenshot(path=str(output_image_path))
                
            await browser.close()
            
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
            
        return str(output_image_path)

    async def render_tweet_with_custom_photo(self, quote_text: str, custom_photo_path: str, filename: str = "manual_photo_quote.png") -> str:
        logger.info(f"Rendering high-resolution custom photo asset to {filename}...")
        template_path = TEMPLATES_DIR / "tweet_image_template.html"
        output_image_path = OUTPUT_DIR / filename
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        raw_time = datetime.now().strftime("%I:%M %p · %b %d, %Y")
        current_time = raw_time.lstrip("0").replace(" 0", " ")
        
        # Absolute path for local image rendering in playwright
        abs_photo_path = f"file://{os.path.abspath(custom_photo_path)}"
        
        rendered_html = html_content.replace("{{ quote }}", quote_text)
        rendered_html = rendered_html.replace("{{ image_src }}", abs_photo_path)
        rendered_html = rendered_html.replace("{{ timestamp }}", current_time)
        
        import uuid
        temp_html_path = TEMPLATES_DIR / f"temp_custom_photo_{uuid.uuid4().hex}.html"
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)
            
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1080, "height": 1350})
            await page.goto(f"file://{os.path.abspath(temp_html_path)}")
            # Optional: wait for image to load
            try:
                await page.wait_for_selector("img", state="attached", timeout=3000)
            except:
                pass
            await page.screenshot(path=str(output_image_path))
            await browser.close()
            
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
            
        return str(output_image_path)

    async def render_news_image(self, news_content: str) -> str:
        logger.info("Rendering high-resolution news asset...")
        template_path = TEMPLATES_DIR / "news_template.html"
        output_image_path = OUTPUT_DIR / "daily_news.png"
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        raw_time = datetime.now().strftime("%I:%M %p · %b %d, %Y")
        current_time = raw_time.lstrip("0").replace(" 0", " ")
        
        rendered_html = html_content.replace("{{ news_content }}", news_content)
        rendered_html = rendered_html.replace("{{ timestamp }}", current_time)
        
        import uuid
        temp_html_path = TEMPLATES_DIR / f"temp_news_{uuid.uuid4().hex}.html"
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)
            
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1080, "height": 1350})
            await page.goto(f"file://{os.path.abspath(temp_html_path)}")
            await page.screenshot(path=str(output_image_path))
            await browser.close()
            
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
            
        return str(output_image_path)

    async def post_to_x_stealth(self, quote_text: str, image_path: str = None) -> bool:
        logger.info("Preparing to post to X...")
        twikit_client = Client('en-US', timeout=180.0)
        try:
            with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
                
            cookies_list = cookie_data.get("cookies", cookie_data) if isinstance(cookie_data, dict) else cookie_data
            cookies_dict = {c['name']: c['value'] for c in cookies_list}
            
            twikit_client.set_cookies(cookies_dict)
            
            media_ids = None
            if image_path and os.path.exists(image_path):
                logger.info(f"Uploading media to X: {image_path}")
                media_id = await twikit_client.upload_media(image_path)
                media_ids = [media_id]
                
            await twikit_client.create_tweet(text=quote_text, media_ids=media_ids)
            logger.info("Agent posted to X.")
            return True
        except Exception as e:
            logger.error(f"Failed to post on X: {e}")
            traceback.print_exc()
            return False

    def post_to_meta(self, caption: str, image_path: str):
        if not all([FB_PAGE_ID, IG_USER_ID, META_PAGE_ACCESS_TOKEN]):
            logger.error("Missing Meta API credentials in .env file.")
            return False
            
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at {image_path}")
            return False
            
        logger.info("--- STARTING META (FB & IG) PUBLISHING ---")
        fb_photo_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        
        try:
            with open(image_path, "rb") as image_file:
                fb_payload = {"caption": caption, "access_token": META_PAGE_ACCESS_TOKEN}
                fb_files = {"source": image_file}
                fb_response = requests.post(fb_photo_url, data=fb_payload, files=fb_files)
                fb_data = fb_response.json()
                
            if "id" not in fb_data:
                logger.error(f"Facebook Posting Failed: {fb_data}")
                return False
                
            photo_id = fb_data["id"]
            logger.info(f"Published to Facebook Page (Photo ID: {photo_id})")
            
            photo_info_url = f"https://graph.facebook.com/v19.0/{photo_id}?fields=images&access_token={META_PAGE_ACCESS_TOKEN}"
            photo_res = requests.get(photo_info_url).json()
            public_image_url = photo_res["images"][0]["source"]
            
            ig_container_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
            ig_container_payload = {
                "image_url": public_image_url,
                "caption": caption,
                "access_token": META_PAGE_ACCESS_TOKEN
            }
            container_res = requests.post(ig_container_url, data=ig_container_payload).json()
            
            if "id" not in container_res:
                logger.error(f"Instagram Container Creation Failed: {container_res}")
                return False
                
            container_id = container_res["id"]
            time.sleep(3)
            
            ig_publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
            ig_publish_payload = {
                "creation_id": container_id,
                "access_token": META_PAGE_ACCESS_TOKEN
            }
            publish_res = requests.post(ig_publish_url, data=ig_publish_payload).json()
            
            if "id" in publish_res:
                logger.info(f"Published to Instagram Feed (Post ID: {publish_res['id']})")
                return True
            else:
                logger.error(f"Instagram Publishing Failed: {publish_res}")
                return False
        except Exception as e:
            logger.error(f"Meta Pipeline Failed: {e}")
            return False

    async def post_video_to_x(self, caption: str, video_path: str) -> bool:
        logger.info("Preparing to post Video to X...")
        twikit_client = Client('en-US', timeout=180.0)
        try:
            with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
                
            cookies_list = cookie_data.get("cookies", cookie_data) if isinstance(cookie_data, dict) else cookie_data
            cookies_dict = {c['name']: c['value'] for c in cookies_list}
            twikit_client.set_cookies(cookies_dict)
            
            logger.info(f"Uploading video to X: {video_path}")
            media_id = await twikit_client.upload_media(video_path, media_category="tweet_video", wait_for_completion=True)
            await twikit_client.create_tweet(text=caption, media_ids=[media_id])
            logger.info("Agent posted video to X.")
            return True
        except Exception as e:
            logger.error(f"Failed to post video on X: {e}")
            traceback.print_exc()
            return False

    def post_reel_to_meta(self, caption: str, video_path: str) -> bool:
        if not all([FB_PAGE_ID, IG_USER_ID, META_PAGE_ACCESS_TOKEN]):
            logger.error("Missing Meta API credentials in .env file.")
            return False
            
        if not os.path.exists(video_path):
            logger.error(f"Video file not found at {video_path}")
            return False
            
        logger.info("--- STARTING META REELS PUBLISHING ---")
        overall_success = True
        
        # 1. FACEBOOK REELS (Local Chunked Upload)
        try:
            logger.info("Starting Facebook Reels local chunked upload...")
            fb_init_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/video_reels"
            init_res = requests.post(fb_init_url, data={"upload_phase": "start", "access_token": META_PAGE_ACCESS_TOKEN}).json()
            
            if "video_id" in init_res:
                video_id = init_res["video_id"]
                upload_url = init_res["upload_url"]
                
                with open(video_path, 'rb') as f:
                    video_data = f.read()
                    
                headers = {
                    "Authorization": f"OAuth {META_PAGE_ACCESS_TOKEN}",
                    "offset": "0",
                    "file_size": str(len(video_data))
                }
                upload_res = requests.post(upload_url, headers=headers, data=video_data)
                
                finish_res = requests.post(fb_init_url, data={
                    "upload_phase": "finish",
                    "video_id": video_id,
                    "video_state": "PUBLISHED",
                    "description": caption,
                    "access_token": META_PAGE_ACCESS_TOKEN
                }).json()
                
                if finish_res.get("success"):
                    logger.info(f"Successfully published to Facebook Reels (Video ID: {video_id})")
                else:
                    logger.error(f"Failed to finalize Facebook Reel: {finish_res}")
                    overall_success = False
            else:
                logger.error(f"Failed to initialize Facebook Reel upload: {init_res}")
                overall_success = False
        except Exception as e:
            logger.error(f"Facebook Reels Pipeline Failed: {e}")
            overall_success = False

        # 2. INSTAGRAM REELS (Requires Public URL)
        try:
            logger.info("Uploading video to temporary public host for IG API...")
            with open(video_path, 'rb') as f:
                catbox_res = requests.post("https://catbox.moe/user/api.php", data={"reqtype": "fileupload"}, files={"fileToUpload": f})
            
            public_video_url = catbox_res.text.strip()
            if public_video_url.startswith("http"):
                logger.info(f"Temporary public URL obtained: {public_video_url}")
                
                ig_container_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
                ig_payload = {
                    "media_type": "REELS",
                    "video_url": public_video_url,
                    "caption": caption,
                    "access_token": META_PAGE_ACCESS_TOKEN
                }
                ig_res = requests.post(ig_container_url, data=ig_payload).json()
                
                if "id" in ig_res:
                    container_id = ig_res["id"]
                    logger.info(f"IG Container created ({container_id}). Waiting for Instagram to download and process...")
                    
                    status_url = f"https://graph.facebook.com/v19.0/{container_id}"
                    for _ in range(12):
                        time.sleep(5)
                        status_res = requests.get(status_url, params={"fields": "status_code", "access_token": META_PAGE_ACCESS_TOKEN}).json()
                        if status_res.get("status_code") == "FINISHED":
                            break
                        elif status_res.get("status_code") == "ERROR":
                            logger.error(f"IG video processing error: {status_res}")
                            break
                    
                    ig_publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
                    ig_pub_res = requests.post(ig_publish_url, data={"creation_id": container_id, "access_token": META_PAGE_ACCESS_TOKEN}).json()
                    
                    if "id" in ig_pub_res:
                        logger.info(f"Successfully published to Instagram Reels (Post ID: {ig_pub_res['id']})")
                    else:
                        logger.error(f"IG Publish failed: {ig_pub_res}")
                        overall_success = False
                else:
                    logger.error(f"IG Container creation failed: {ig_res}")
                    overall_success = False
            else:
                logger.error(f"Failed to get public URL from catbox: {public_video_url}")
                overall_success = False
        except Exception as e:
            logger.error(f"Instagram Reels Pipeline Failed: {e}")
            overall_success = False
            
        return overall_success



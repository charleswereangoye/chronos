import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# Meta Credentials
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
IG_USER_ID = os.getenv("IG_USER_ID")
META_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")

def post_to_meta(caption: str, image_path: str):
    """
    Publishes a local graphic and caption to Facebook Page and Instagram Business Account.
    """
    if not all([FB_PAGE_ID, IG_USER_ID, META_ACCESS_TOKEN]):
        print("[ERROR] FAILED: Missing Meta API credentials in .env file.")
        return False

    if not os.path.exists(image_path):
        print(f"[ERROR] FAILED: Image file not found at {image_path}")
        return False

    print("\n--- STARTING META (FB & IG) PUBLISHING ---")

    # ---------------------------------------------------------
    # STEP 1: Upload Local Image Binary directly to Facebook Page
    # ---------------------------------------------------------
    print("[INFO] 1/4 Uploading graphic and posting to Facebook Page...")
    fb_photo_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    
    try:
        with open(image_path, "rb") as image_file:
            fb_payload = {
                "caption": caption,
                "access_token": META_ACCESS_TOKEN
            }
            fb_files = {"source": image_file}
            
            fb_response = requests.post(fb_photo_url, data=fb_payload, files=fb_files)
            fb_data = fb_response.json()

        if "id" not in fb_data:
            print(f"[ERROR] Facebook Posting Failed: {fb_data}")
            return False

        photo_id = fb_data["id"]
        print(f"[SUCCESS] Published to Facebook Page (Photo ID: {photo_id})")

        # ---------------------------------------------------------
        # STEP 2: Fetch Meta's Public CDN Image URL for Instagram
        # ---------------------------------------------------------
        print("[INFO] 2/4 Fetching public CDN URL for Instagram container...")
        photo_info_url = f"https://graph.facebook.com/v19.0/{photo_id}?fields=images&access_token={META_ACCESS_TOKEN}"
        photo_res = requests.get(photo_info_url).json()

        # Meta returns images in multiple sizes; index 0 is the highest resolution
        public_image_url = photo_res["images"][0]["source"]

        # ---------------------------------------------------------
        # STEP 3: Create Instagram Media Container
        # ---------------------------------------------------------
        print("[INFO] 3/4 Creating Instagram media container...")
        ig_container_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
        ig_container_payload = {
            "image_url": public_image_url,
            "caption": caption,
            "access_token": META_ACCESS_TOKEN
        }
        
        container_res = requests.post(ig_container_url, data=ig_container_payload).json()

        if "id" not in container_res:
            print(f"[ERROR] Instagram Container Creation Failed: {container_res}")
            return False

        container_id = container_res["id"]

        # ---------------------------------------------------------
        # STEP 4: Publish Instagram Media Container
        # ---------------------------------------------------------
        print("[INFO] 4/4 Publishing container to Instagram Business feed...")
        # Brief sleep to ensure Meta finishes processing the container image
        time.sleep(3)

        ig_publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
        ig_publish_payload = {
            "creation_id": container_id,
            "access_token": META_ACCESS_TOKEN
        }

        publish_res = requests.post(ig_publish_url, data=ig_publish_payload).json()

        if "id" in publish_res:
            print(f"[SUCCESS] Published to Instagram Feed (Post ID: {publish_res['id']})")
            print("--- META PUBLISHING COMPLETE ---\n")
            return True
        else:
            print(f"[ERROR] Instagram Publishing Failed: {publish_res}")
            return False

    except Exception as e:
        print(f"[ERROR] Meta Pipeline Failed with error: {e}")
        return False
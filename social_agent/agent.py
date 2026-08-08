import os
import asyncio
import json
from datetime import datetime
from google import genai
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from twikit import Client
from meta_poster import post_to_meta

# 1. Load Environment Variables
load_dotenv()
client = genai.Client()
base_dir = os.path.dirname(__file__)

# --- NEW: HISTORY LOGIC ---
def load_history():
    history_path = os.path.join(base_dir, "history.json")
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history_list):
    history_path = os.path.join(base_dir, "history.json")
    # Keep only the last 50 quotes to prevent the file from growing forever
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history_list[-50:], f, indent=4)

# --- UPDATED: GEMINI JSON BRAIN ---
def generate_trading_content():
    print("Agent is thinking of a quote and caption...")
    history = load_history()
    
    prompt = """
    You are an expert social media manager and a veteran, battle-scarred forex/gold day trader.
    Generate content for a daily post. You must return ONLY a raw JSON object. Do not include markdown formatting like ```json.
    
    The JSON must have exactly these two keys:
    1. "image_quote": A highly engaging, punchy, sarcastic but brutally honest motivational quote about trading psychology, discipline, or risk management. Maximum 2 sentences. No hashtags, no emojis.
    2. "meta_caption": A 3-4 sentence natural, engaging caption that expands on the quote, asks a question to drive engagement, and includes 3-5 relevant hashtags (e.g. #Forex #DayTrading).
    """
    
    while True: # Loop until we get a unique quote
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
        )
        raw_text = response.text.strip()
        
        # Clean up Markdown if Gemini accidentally includes it
        if raw_text.startswith("```"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
        try:
            # Parse the JSON
            content = json.loads(raw_text)
            image_quote = content.get("image_quote", "")
            
            # Anti-Repeat Check
            if image_quote not in history:
                history.append(image_quote)
                save_history(history)
                return content # Success! Unique quote found.
            else:
                print("Duplicate quote detected! Asking Gemini for a new one...")
                
        except json.JSONDecodeError:
            print("Failed to parse JSON. Asking Gemini to try again...")

# --- X POSTING (Unchanged except parameter name) ---
async def post_to_x_stealth(quote_text):
    print("Agent is posting to X using twifork and Cookies...")
    twikit_client = Client('en-US')
    
    try:
        state_path = os.path.join(base_dir, "state.json")
        with open(state_path, "r", encoding="utf-8") as f:
            cookie_data = json.load(f)
            
        cookies_list = cookie_data.get("cookies", cookie_data) if isinstance(cookie_data, dict) else cookie_data
        cookies_dict = {c['name']: c['value'] for c in cookies_list}
        
        twikit_client.set_cookies(cookies_dict)
        await twikit_client.create_tweet(text=quote_text)
        print("SUCCESS! Agent posted to X.")
        
    except Exception as e:
        print(f"FAILED to post on X: {e}")

# --- PLAYWRIGHT (Unchanged except parameter name) ---
async def render_tweet_image(quote_text):
    print("Agent is rendering the high-res Tweet graphic...")
    
    template_path = os.path.join(base_dir, "tweet_template.html")
    output_image_path = os.path.join(base_dir, "output", "daily_quote.png")
    
    # Ensure output directory exists
    os.makedirs(os.path.join(base_dir, "output"), exist_ok=True)
    
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    rendered_html = html_content.replace("{{ quote }}", quote_text)
    rendered_html = rendered_html.replace("{{ date }}", datetime.now().strftime("%b %-d, %Y"))
    
    temp_html_path = os.path.join(base_dir, "temp_render.html")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        await page.goto(f"file://{os.path.abspath(temp_html_path)}")
        await page.screenshot(path=output_image_path)
        await browser.close()
        
    if os.path.exists(temp_html_path):
        os.remove(temp_html_path)
        
    return output_image_path

# --- THE MAIN ORCHESTRATOR ---
async def main():
    # Step 1: Generate structured JSON content
    content = generate_trading_content()
    quote = content["image_quote"]
    caption = content["meta_caption"]
    
    print("\n-------------------------------------------")
    print(f"X QUOTE:\n{quote}\n")
    print(f"META CAPTION:\n{caption}")
    print("-------------------------------------------\n")
    
    # Step 2: Render Graphic via Playwright
    image_path = await render_tweet_image(quote)
    print(f"GRAPHIC GENERATED: {image_path}\n")
    
    # Step 3: Post to X using Twikit/Cookies
    await post_to_x_stealth(quote)
    
    # Step 4: Post to Meta (Facebook Page + Instagram Feed)
    post_to_meta(caption=caption, image_path=image_path)

if __name__ == "__main__":
    asyncio.run(main())
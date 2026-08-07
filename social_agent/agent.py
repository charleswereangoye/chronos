import os
import asyncio
import tweepy
from google import genai
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from twikit import Client

# 1. Load Environment Variables
load_dotenv()
client = genai.Client()

def generate_trading_quote():
    print("Agent is thinking of a quote...")
    prompt = """
    You are an expert social media manager for a forex and gold day trader.
    Write a highly engaging, punchy, and short motivational quote tailored for traders.
    Focus on psychology, discipline, or risk management.
    Keep it under 2 sentences. Do not use hashtags. Do not include emojis.
    """
    
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
    )
    return response.text.strip()

import json

async def post_to_x_stealth(quote_text):
    print("Agent is posting to X using Twikit and Cookies...")
    client = Client('en-US')
    
    try:
        # 1. Load Cookies from state.json to completely bypass login
        base_dir = os.path.dirname(__file__)
        state_path = os.path.join(base_dir, "state.json")
        
        with open(state_path, "r", encoding="utf-8") as f:
            cookie_data = json.load(f)
            
        # Parse the cookies into a dictionary for Twikit
        cookies_list = cookie_data.get("cookies", cookie_data) if isinstance(cookie_data, dict) else cookie_data
        cookies_dict = {c['name']: c['value'] for c in cookies_list}
        
        client.set_cookies(cookies_dict)
        
        # 2. Post the quote!
        await client.create_tweet(text=quote_text)
        print("SUCCESS! Agent posted to X.")
        
    except Exception as e:
        print(f"FAILED: {e}")

async def render_tweet_image(quote_text):
    print("Agent is rendering the high-res Tweet graphic...")
    
    # Paths setup
    base_dir = os.path.dirname(__file__)
    template_path = os.path.join(base_dir, "tweet_template.html")
    output_image_path = os.path.join(base_dir, "output", "daily_quote.png")
    
    # Read HTML Template
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    from datetime import datetime
    
    # Inject Quote Text and Date
    rendered_html = html_content.replace("{{ quote }}", quote_text)
    rendered_html = rendered_html.replace("{{ date }}", datetime.now().strftime("%b %-d, %Y"))
    
    # Save temporary injected HTML file
    temp_html_path = os.path.join(base_dir, "temp_render.html")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    
    # Launch Playwright Browser to take screenshot
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Change viewport width/height to 1080x1350 (4:5 Instagram ratio)
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})
        
        # Open local HTML file
        await page.goto(f"file://{os.path.abspath(temp_html_path)}")
        
        # Take a full 1080x1080 screenshot (Acts like your Canva background)
        await page.screenshot(path=output_image_path)
            
        await browser.close()
        
    # Clean up temporary HTML file
    if os.path.exists(temp_html_path):
        os.remove(temp_html_path)
        
    return output_image_path

async def main():
    # Step 1: Generate text
    quote = generate_trading_quote()
    
    print("\n-------------------------------------------")
    print(f"QUOTE GENERATED:\n{quote}")
    print("-------------------------------------------\n")
    
    # Step 2: Post the text using Twikit
    await post_to_x_stealth(quote)
    
    # Step 3: Generate graphic for Facebook / Instagram
    image_path = await render_tweet_image(quote)
    print(f"META (FB/IG) GRAPHIC GENERATED: {image_path}\n")

if __name__ == "__main__":
    asyncio.run(main())
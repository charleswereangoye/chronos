import json, asyncio, os
from twikit import Client
from shared.config import STATE_FILE_PATH, X_USERNAME

async def test():
    client = Client('en-US')
    with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
        cookie_data = json.load(f)
    cookies_list = cookie_data.get("cookies", cookie_data) if isinstance(cookie_data, dict) else cookie_data
    cookies_dict = {c['name']: c['value'] for c in cookies_list}
    client.set_cookies(cookies_dict)
    
    print("Testing search_tweet...")
    try:
        tweets = await client.search_tweet(f"from:{X_USERNAME}", "Latest", count=5)
        print("search_tweet successful!")
    except Exception as e:
        print(f"search_tweet failed: {e}")
        
    print("Testing get_user_tweets...")
    try:
        user = await client.get_user_by_screen_name(X_USERNAME)
        tweets = await user.get_tweets("Tweets", count=5)
        print("get_user_tweets successful!")
    except Exception as e:
        print(f"get_user_tweets failed: {e}")

asyncio.run(test())

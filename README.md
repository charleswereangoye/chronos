# Social Agent

An autonomous AI agent designed to generate highly engaging, punchy, and short motivational quotes tailored for forex and gold day traders. The agent automatically renders a beautifully generated high-resolution graphic and posts to X (Twitter), Facebook Pages, and Instagram Business feeds.

## Features

- **Automated Quote Generation:** Uses Google's `gemini-3.1-flash-lite` to generate engaging trader-focused quotes and captions formatted as structured JSON.
- **Anti-Repeat Logic:** Includes a `history.json` mechanism to ensure the agent never posts the same quote twice.
- **Stealth X Posting:** Uses `twifork` (Twikit) to securely bypass X's anti-bot detection and login walls via cookie injection.
- **Meta Integrations:** Automatically publishes to a Facebook Page and Instagram Business account via the Meta Graph API.
- **High-Res Graphics:** Uses Playwright to render a premium Canva-style 1080x1350 graphic based on an HTML/TailwindCSS template.

## Setup

1. **Clone the repository**
2. **Install dependencies:** 
   ```bash
   pip install google-genai python-dotenv playwright twifork requests
   ```
3. **Playwright setup:** Run `playwright install chromium`
4. **Environment Variables:** Create a `.env` file with the following:
   ```env
   # Gemini
   GEMINI_API_KEY=your_api_key

   # X / Twitter (Optional, credentials bypass handled by state.json)
   X_USERNAME=your_username
   X_PASSWORD=your_password

   # Meta (Facebook & Instagram)
   FB_PAGE_ID=your_fb_page_id
   IG_USER_ID=your_ig_user_id
   META_PAGE_ACCESS_TOKEN=your_meta_access_token
   ```
5. **X Cookie Setup:** Export your X session cookies (using a Chrome extension) and save them as a `state.json` file in the `social_agent` folder.

## Usage

Run the agent with:
```bash
python social_agent/agent.py
```

## Security

Sensitive files like `.env`, `state.json`, and `history.json` are excluded via `.gitignore` to prevent credentials from being exposed. Ensure you never commit your session cookies or API keys to a public repository!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

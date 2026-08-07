# Social Agent

An autonomous AI agent designed to generate highly engaging, punchy, and short motivational quotes tailored for forex and gold day traders, and automatically post them to X (Twitter) along with a beautifully generated high-resolution graphic.

## Features

- **Automated Quote Generation:** Uses Google's Gemini to generate engaging trader-focused quotes.
- **Stealth X Posting:** Uses `twifork` (Twikit) to securely bypass X's anti-bot detection and login walls via cookie injection.
- **High-Res Graphics:** Uses Playwright to render a premium Canva-style 1080x1350 graphic based on an HTML/TailwindCSS template.

## Setup

1. **Clone the repository**
2. **Install dependencies:** 
   ```bash
   pip install google-genai python-dotenv playwright twifork
   ```
3. **Playwright setup:** Run `playwright install chromium`
4. **Environment Variables:** Create a `.env` file with the following:
   ```env
   GEMINI_API_KEY=your_api_key
   X_USERNAME=your_username
   X_PASSWORD=your_password
   ```
5. **Cookie Setup:** Export your X session cookies (using a Chrome extension) and save them as a `state.json` file in the `social_agent` folder.

## Usage

Run the agent with:
```bash
python social_agent/agent.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

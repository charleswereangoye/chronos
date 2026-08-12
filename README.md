# Chronos (Enterprise AI Agentic System)

Chronos is a fully modular, enterprise-grade autonomous AI agent system designed to act as a highly authentic social media personality for forex, crypto, and day traders. It completely replaces monolithic scripts with a multi-agent orchestrated pipeline.

## System Architecture

The pipeline is managed by an interactive **Telegram Orchestrator** which delegates work to specialized sub-agents via the `SocialAgentCoordinator`:

1. **AnalyticsAgent**: Connects to X (via Twikit) to fetch live engagement metrics. It dynamically tracks which content formats are performing best.
2. **ResearchAgent**: Aggregates real-time market data by parsing live financial RSS feeds (Macro News) and querying X for retail trader sentiment.
3. **StrategistAgent (JSON Brain)**: Digests the research and analytics to generate a dynamic strategy, explicitly selecting a human **Emotional Filter**.
4. **CreatorAgent**: Uses Gemini API (with key rotation) to generate highly conversational, timeless, and relatable content.
5. **PublisherAgent (Stealth Posting)**: Renders premium high-resolution Canva-style graphics (1080x1350) using Playwright and an HTML/Tailwind template. It securely posts to X (bypassing bot detection via Twikit) and performs **Complete Meta Integration** to publish to Facebook and Instagram.

## Core Pipelines
- **News Alert Pipeline**: Automatically fetches breaking red-folder macro events and generates a Forex Factory-style graphical alert.
- **Serious Advice Pipeline**: Generates deep, analytical trading wisdom based on current market sentiment without memes or sarcasm.
- **Persona Quote Pipeline**: Generates relatable, emotional quotes reflecting the current mood of retail traders.
- **Custom Manual Post**: Allows the user to provide their own text or photos directly through Telegram. The system automatically brands the content via HTML templates and distributes it across all networks.

## Setup

1. **Install dependencies:** 
   ```bash
   pip install google-genai python-dotenv playwright twikit requests feedparser python-telegram-bot
   ```
2. **Playwright setup:** Run `playwright install chromium`
3. **Environment Variables:** Create a `.env` file with `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, `X_USERNAME`, `TELEGRAM_BOT_TOKEN` and your Meta Graph credentials (`FB_PAGE_ID`, `IG_USER_ID`, `META_PAGE_ACCESS_TOKEN`).
4. **Session Cookies:** Place your exported X cookies into `agents/social_agent/state/state.json`.

## Usage

Start the Telegram Orchestrator to control the system remotely:
```bash
python orchestrator/telegram_orchestrator.py
```
*(You can also use the terminal-based menu by running `python orchestrator/main_chronos.py`)*

# Chronos (Enterprise AI Agentic System)

Chronos is a fully modular, enterprise-grade autonomous AI agent system designed to act as a highly authentic social media personality for forex, crypto, and day traders. It completely replaces monolithic scripts with a multi-agent orchestrated pipeline.

## System Architecture

The pipeline is orchestrated by the `SocialAgentCoordinator` which delegates work to specialized sub-agents:

1. **AnalyticsAgent**: Connects to X (via Twikit) to fetch live engagement metrics (Likes, Retweets, Replies, Views). It dynamically tracks which content formats (e.g., relatable memes, sarcasm) are performing best.
2. **ResearchAgent**: Aggregates real-time market data by parsing live financial RSS feeds (Macro News) and querying X for retail trader sentiment.
3. **StrategistAgent (JSON Brain)**: Digests the research and analytics to generate a dynamic strategy. It explicitly selects one of five human **Emotional Filters** (Friendly Mentor, Sarcastic Realist, Grounded Philosopher, Exhausted Trader, Hyped Analyst) based on current market conditions.
4. **CreatorAgent**: Uses Gemini API (with key rotation and failover) to generate highly conversational, timeless, and relatable content matching the strategist's emotional filter. It outputs a clean quote for the image, a hashtagged post for X, and a full meta caption for Instagram/Facebook.
5. **PublisherAgent (Stealth Posting)**: Renders a premium high-resolution Canva-style graphic (1080x1350) using Playwright and an HTML/Tailwind template. It securely posts the graphic to X (stealthily bypassing bot detection via Twikit) and performs **Complete Meta Integration** to publish directly to Facebook and Instagram via the Meta Graph API.

## Features
- **Model & Key Failover Rotation**: Robust fallback execution layers across Gemini APIs to handle rate limits and quota exhaustion seamlessly.
- **Dynamic Humanization**: Strictly avoids AI slang, generating content that feels 100% human and relatable.
- **Beautiful Terminal Logs**: Fully formatted, color-coded CLI output via custom ANSI loggers and ASCII block summaries.

## Setup

1. **Install dependencies:** 
   ```bash
   pip install google-genai python-dotenv playwright twikit requests feedparser
   ```
2. **Playwright setup:** Run `playwright install chromium`
3. **Environment Variables:** Create a `.env` file with `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, `X_USERNAME`, and your Meta Graph credentials (`FB_PAGE_ID`, `IG_USER_ID`, `META_PAGE_ACCESS_TOKEN`).
4. **Session Cookies:** Place your exported X cookies into `agents/social_agent/state/state.json`.

## Usage

Run the master orchestrator to start the pipeline:
```bash
python orchestrator/main_chronos.py
```

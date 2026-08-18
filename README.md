# 🚀 Chronos (Enterprise AI Agentic System)

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg) ![Gemini](https://img.shields.io/badge/Gemini-Pro-orange.svg) ![Playwright](https://img.shields.io/badge/Playwright-Automated-brightgreen.svg) ![License](https://img.shields.io/badge/License-MIT-purple.svg)

Chronos is a fully modular, enterprise-grade, autonomous multi-agent operating system designed to run at absolutely **$0.00 overhead**. Operating as a highly authentic social media personality for forex, crypto, and day traders, Chronos completely replaces monolithic scheduling scripts with a dynamic, LLM-driven orchestration pipeline.

By combining Gemini's reasoning with headless stealth automation (Playwright/Twikit) and API integrations, Chronos manages everything from market analysis and content creation to video meme rendering and multi-platform publishing.

---

## 🧠 System Architecture & Multi-Agent Ecosystem

At the core of Chronos is a **Master Orchestrator** (accessible via an interactive Telegram Bot GUI) that delegates specialized tasks to a fleet of modular sub-agents. 

```text
                               +-------------------------+
                               |  Master Orchestrator    |
                               | (Telegram Bot / CLI)    |
                               +-----------+-------------+
                                           |
       +--------------------+--------------+------+--------------------+
       |                    |                     |                    |
+------v-------+    +-------v------+      +-------v------+     +-------v------+
| Social Agent |    | Forex Agent  |      | Job Seeking  |     |Daily Updates |
|  (Content)   |    |  (Trading)   |      |  (Careers)   |     |  (Briefing)  |
+--------------+    +--------------+      +--------------+     +--------------+
```

### Sub-Agent Hierarchy
1. 🧠 **Master Orchestrator:** The Telegram Bot GUI and dispatch engine that routes commands, monitors workflows, and enables manual intervention (e.g., custom posting, reviewing drafts).
2. 📱 **Social Media & Meme Engine:** Responsible for static graphics, short-form video reels generation, contextual memory tracking, and multi-platform stealth publishing.
3. 📈 **Forex Trading Agent:** (In Production) Market monitoring, sentiment analysis, and alert generation.
4. 💼 **Job Seeking & Productivity Agent:** (In Production) Automated email parsing, application pipelines, and productivity tracking.
5. 📅 **Daily Updates Agent:** (In Production) Automated morning/evening briefings and scheduled digests.

---

## 📱 In-Depth Sub-Agent Documentation

### 1. Static Quote Generator
The **Creator Agent** utilizes a highly specialized Gemini persona prompt to draft authentic trading quotes. The **Publisher Agent** takes this text and renders a premium, high-resolution (1080x1350) canvas using an HTML/Tailwind template via headless Playwright—giving it a clean, Canva-style aesthetic.

### 2. Video Meme & Reel Engine
Chronos features a built-in vertical video meme generator:
- **Zero-Cost Scout Pipeline:** Uses `yt-dlp` (integrated directly into the Telegram Orchestrator) to clip and download raw meme templates.
- **Rendering with MoviePy:** The `VideoMemeAgent` overlays a rendered Twitter-style HTML card onto a video template to create a highly viral 9:16 (vertical) short-form reel. 

### 3. Contextual Correlation & Memory
Chronos isn't just a random generator; it remembers what it did. The system uses a JSON-based memory engine (`memory.py` / `history.json`) to track the last 50 generated quotes and used video templates. 
It explicitly correlates generated text with emotional states (e.g., `panic`, `celebration`) to adapt its tone and algorithmically format viral hashtags (`#forex`, `#tradingmemes`, `#fyp`).

### 4. Multi-Platform Publishing Pipeline
Chronos is designed to bypass standard bot detection using stealth techniques:
- **X (Twitter):** Stealth cookie injection using `Twikit` to bypass standard API rate limits and authentication bans.
- **TikTok:** Headless stealth uploads via Playwright automation (using `tiktok_state.json` session cookies).
- **Meta (Instagram & Facebook):** Deep integration with the Meta Graph API for Instagram Reels, Instagram Feed, and Facebook Pages (utilizing chunked video uploads and Catbox as a temporary video host).

---

## 🛠 Tech Stack & Zero-Cost Infrastructure

Chronos is built on a stack designed to avoid recurring SAAS fees:

| Component | Technology Used | Purpose |
| --- | --- | --- |
| **Core Logic** | Python 3.12 | Primary application runtime. |
| **AI Brain** | Google GenAI SDK | Multi-attempt failover content generation. |
| **Browser Automation** | Playwright | High-res HTML-to-Image rendering & TikTok stealth posting. |
| **X Integration** | Twikit (Twifork) | Stealth API alternative for X (Twitter) via cookies. |
| **Video Rendering** | MoviePy (`2.2.1`) | Automated meme video compositing & overlaying. |
| **Media Sourcing** | `yt-dlp` | Zero-cost video clipping and downloading. |
| **Orchestration GUI**| `python-telegram-bot` | Master control panel and interactive Telegram interface. |
| **Meta API** | `requests` | Direct HTTP calls to Facebook & Instagram Graph APIs. |

---

## 📂 Repository Structure

```text
chronos/
│
├── agents/
│   ├── social_agent/            # Complete content generation & publishing engine
│   │   ├── templates/           # HTML/Tailwind templates for Playwright rendering
│   │   ├── state/               # Browser session cookies (state.json, tiktok_state.json)
│   │   ├── publisher_agent.py   # Multi-platform stealth publisher
│   │   ├── video_meme_agent.py  # MoviePy video compositor
│   │   └── social_coordinator.py# Pipeline router
│   ├── forex_agent/             # (WIP) Trading modules
│   └── job_seeking/             # (WIP) Career automation
│
├── assets/                      # Local video templates & clipped scenes
├── orchestrator/
│   └── telegram_orchestrator.py # Master Telegram Bot Controller
├── shared/
│   ├── config.py                # Global environment and paths
│   └── memory.py                # JSON memory & state tracker
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env                         # (Git-ignored) API keys & credentials
```

---

## ⚙️ Installation, Environment Variables & Configuration

### 1. Initial Setup
Clone the repository and set up a virtual environment:
```bash
git clone https://github.com/charleswereangoye/chronos.git
cd chronos
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Playwright Binaries
Chronos relies on Playwright for image rendering and TikTok automation.
```bash
playwright install chromium
```

### 3. Environment Variables
Create a `.env` file in the root directory using the following template:

```env
# Google Gemini (Supports key rotation)
GEMINI_API_KEY_1="your_gemini_api_key_here"
GEMINI_API_KEY_2="your_backup_gemini_api_key_here"

# X (Twitter) Fallback Login (Cookies preferred)
X_USERNAME="your_x_username"
X_PASSWORD="your_x_password"

# Meta Graph API Config
FB_PAGE_ID="your_facebook_page_id"
IG_USER_ID="your_instagram_user_id"
META_PAGE_ACCESS_TOKEN="your_long_lived_meta_access_token"

# Telegram Orchestrator
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
```

### 4. Authentication Cookie Setup (Stealth Mode)
For Twikit (X) and Playwright (TikTok) to work without triggering bot protections, you must export your authenticated browser cookies.

- **For X (Twitter):** Export cookies to `agents/social_agent/state/state.json`.
- **For TikTok:** Export cookies to `agents/social_agent/state/tiktok_state.json`.

---

## 🚀 Usage & Telegram Commands

### Running Locally
To launch the Master Orchestrator, simply run:
```bash
python orchestrator/telegram_orchestrator.py
```
*(A terminal-based CLI menu is also available via `python orchestrator/main_chronos.py`)*

### Running via Docker
Chronos is container-ready. 
```bash
docker-compose up -d --build
```

### Telegram Commands
Once the bot is running, interact with it on Telegram using the following commands:
- `/start` - Launch the Main Menu and access sub-agents.
- `/clip <video_url>` - Trigger `yt-dlp` to download or clip a specific timestamp from a video.

**From the Telegram GUI, you can:**
- Generate text quotes, serious advice, or breaking news alerts.
- Generate Video Reel Memes.
- Create Custom Manual Posts (Upload custom photos/videos directly to the bot for multi-platform distribution).
- Retry failed network uploads.
- Review, Edit, or Reject drafts before they are published.

---

## 🗺 Roadmap & Future Modules

**Completed Milestones:**
- [x] Master Telegram Orchestrator & CLI
- [x] Playwright HTML-to-Image Rendering Engine
- [x] Twikit Stealth X Integration
- [x] Meta Graph API (Reels & Feed) Integration
- [x] TikTok Headless Automation
- [x] Video Meme Generator (MoviePy compositing)
- [x] JSON Contextual Memory & Emotion Tracking

**Pending Modules:**
- [ ] **YouTube Shorts Automation:** Add Playwright/API support for stealth YouTube Shorts uploads.
- [ ] **Forex Agent Expansion:** Full implementation of sentiment analysis and MT4/MT5 webhook integration.
- [ ] **Job Seeking Agent:** IMAP email parsing and automated resume submission workflows.
- [ ] **Cloud VPS Daemon:** Optimize the Docker container for 24/7 autonomous heartbeat execution on low-tier cloud instances.

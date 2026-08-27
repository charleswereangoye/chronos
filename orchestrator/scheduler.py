import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from agents.job_seeking.job_scraper import JobScraper
from agents.social_agent.social_coordinator import SocialAgentCoordinator

logger = logging.getLogger("AutonomousScheduler")

STATE_FILE = os.path.join(os.path.dirname(__file__), "scheduler_state.json")

class AutonomousScheduler:
    def __init__(self, application):
        self.app = application
        self.coordinator = SocialAgentCoordinator()
        self.job_scraper = JobScraper()
        self.running = False
        self._load_state()

    def _load_state(self):
        self.target_chat_id = None
        self.last_job_radar_time = None
        self.last_social_draft_time = None
        
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.target_chat_id = data.get("target_chat_id")
                    if data.get("last_job_radar_time"):
                        self.last_job_radar_time = datetime.fromisoformat(data["last_job_radar_time"])
                    if data.get("last_social_draft_time"):
                        self.last_social_draft_time = datetime.fromisoformat(data["last_social_draft_time"])
            except Exception as e:
                logger.warning(f"Failed to load scheduler state: {e}")

    def _save_state(self):
        try:
            data = {
                "target_chat_id": self.target_chat_id,
                "last_job_radar_time": self.last_job_radar_time.isoformat() if self.last_job_radar_time else None,
                "last_social_draft_time": self.last_social_draft_time.isoformat() if self.last_social_draft_time else None
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scheduler state: {e}")

    def set_target_chat_id(self, chat_id: int):
        if self.target_chat_id != chat_id:
            self.target_chat_id = chat_id
            self._save_state()
            logger.info(f"Target chat ID set to: {chat_id}")

    async def run_autonomous_job_radar(self, force: bool = False):
        if not self.target_chat_id:
            logger.info("Scheduler: No active Telegram chat ID registered yet.")
            return

        now = datetime.now()
        if not force and self.last_job_radar_time:
            if now - self.last_job_radar_time < timedelta(hours=6):
                logger.info("Job radar already ran recently. Skipping.")
                return

        logger.info("Executing Autonomous Job Radar scan...")
        try:
            matches_text = await self.job_scraper.find_matches()
            
            # Send notification
            header = "📡 <b>CHRONOS JOB RADAR: DAILY MATCHES</b>\n\n"
            msg = header + matches_text
            
            # Telegram character limit safety
            chunk_size = 4000
            if len(msg) > chunk_size:
                chunks = [msg[i:i+chunk_size] for i in range(0, len(msg), chunk_size)]
                for chunk in chunks:
                    await self.app.bot.send_message(
                        chat_id=self.target_chat_id,
                        text=chunk,
                        parse_mode=None
                    )
            else:
                await self.app.bot.send_message(
                    chat_id=self.target_chat_id,
                    text=msg,
                    parse_mode=None
                )
                
            self.last_job_radar_time = now
            self._save_state()
            logger.info("Autonomous Job Radar scan delivered to Telegram.")
        except Exception as e:
            logger.error(f"Autonomous Job Radar failed: {e}")

    async def run_autonomous_social_draft(self, force: bool = False):
        if not self.target_chat_id:
            return

        now = datetime.now()
        if not force and self.last_social_draft_time:
            if now - self.last_social_draft_time < timedelta(hours=8):
                logger.info("Social draft already generated recently. Skipping.")
                return

        logger.info("Generating Autonomous Daily Trading Meme Draft...")
        try:
            draft = await self.coordinator.generate_persona_draft()
            if not draft:
                return

            keyboard = [
                [
                    InlineKeyboardButton("🚀 1-Tap Publish to X & Meta", callback_data="auto_publish_social"),
                    InlineKeyboardButton("🔄 Regenerate", callback_data="auto_regen_social")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            msg = (
                "🎭 <b>CHRONOS DAILY MEME DRAFT READY</b>\n\n"
                f"<b>Meme Quote:</b>\n{draft['quote']}\n\n"
                f"<b>X Post:</b>\n{draft['x_post_text']}\n\n"
                f"<b>Meta Caption:</b>\n{draft['caption']}"
            )

            # Store draft in bot data for inline action
            self.app.bot_data["last_auto_draft"] = draft

            await self.app.bot.send_message(
                chat_id=self.target_chat_id,
                text=msg,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            self.last_social_draft_time = now
            self._save_state()
            logger.info("Autonomous Social Draft delivered to Telegram.")
        except Exception as e:
            logger.error(f"Autonomous Social Draft failed: {e}")

    async def start_loop(self):
        """Main autonomous background loop running inside Podman."""
        self.running = True
        logger.info("Autonomous scheduler started in background.")
        
        # Initial catch-up after container boot
        await asyncio.sleep(5)
        if self.target_chat_id:
            logger.info("Performing startup catch-up scan...")
            await self.run_autonomous_job_radar(force=False)
            await self.run_autonomous_social_draft(force=False)

        while self.running:
            try:
                await asyncio.sleep(1800)  # Check every 30 minutes
                now = datetime.now()
                
                # Check for Job Radar (e.g. at 09:00 and 17:00)
                if now.hour in [9, 17] and (not self.last_job_radar_time or now - self.last_job_radar_time > timedelta(hours=4)):
                    await self.run_autonomous_job_radar()
                    
                # Check for Social Meme Draft (e.g. at 11:00)
                if now.hour == 11 and (not self.last_social_draft_time or now - self.last_social_draft_time > timedelta(hours=4)):
                    await self.run_autonomous_social_draft()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)

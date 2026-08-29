import asyncio
import os
import sys
import math
import logging
import uuid
import httpx
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# Ensure the root chronos directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import TELEGRAM_BOT_TOKEN
from agents.social_agent.social_coordinator import SocialAgentCoordinator
from orchestrator.scheduler import AutonomousScheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

coordinator = SocialAgentCoordinator()
scheduler = None

async def safe_reply(message_target, text, reply_markup=None, parse_mode="Markdown", **kwargs):
    target = message_target.message if hasattr(message_target, "message") and message_target.message else message_target
    if not text:
        return None
        
    chunk_size = 4000
    if len(text) > chunk_size:
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        for i, chunk in enumerate(chunks):
            m_markup = reply_markup if i == len(chunks) - 1 else None
            try:
                await target.reply_text(chunk, parse_mode=parse_mode, reply_markup=m_markup, **kwargs)
            except Exception as err:
                logger.warning(f"Failed to send chunk with parse_mode={parse_mode}: {err}. Retrying without markdown.")
                await target.reply_text(chunk, parse_mode=None, reply_markup=m_markup, **kwargs)
        return None

    try:
        return await target.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    except Exception as err:
        logger.warning(f"Failed to send markdown reply: {err}. Falling back to plain text.")
        return await target.reply_text(text, parse_mode=None, reply_markup=reply_markup, **kwargs)

async def safe_reply_photo(message_target, photo, caption=None, reply_markup=None, parse_mode="Markdown", **kwargs):
    target = message_target.message if hasattr(message_target, "message") and message_target.message else message_target
    try:
        return await target.reply_photo(photo=photo, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    except Exception as err:
        logger.warning(f"Failed to send photo with markdown: {err}. Falling back to plain caption.")
        return await target.reply_photo(photo=photo, caption=caption, parse_mode=None, reply_markup=reply_markup, **kwargs)

async def safe_reply_video(message_target, video, caption=None, reply_markup=None, parse_mode="Markdown", **kwargs):
    target = message_target.message if hasattr(message_target, "message") and message_target.message else message_target
    try:
        return await target.reply_video(video=video, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    except Exception as err:
        logger.warning(f"Failed to send video with markdown: {err}. Falling back to plain caption.")
        return await target.reply_video(video=video, caption=caption, parse_mode=None, reply_markup=reply_markup, **kwargs)

# Define conversation states
MAIN_MENU = 1
SOCIAL_MENU = 2
MANUAL_TYPE = 3
TEXT_QUOTE = 4
TEXT_CAPTION = 5
PHOTO_FILE = 6
PHOTO_CAPTION = 7
SETTINGS_MENU = 8
REVIEW_POST = 9
EDIT_QUOTE = 10
EDIT_X_POST = 11
EDIT_CAPTION = 12
VIDEO_FILE = 13
VIDEO_QUOTE = 14
VIDEO_CAPTION = 15
CLIP_URL = 16
CLIP_TYPE = 17
CLIP_START = 18
CLIP_END = 19
JOB_SEEKING_MENU = 20
TAILOR_CV_URL = 21
COVER_LETTER_URL = 22
JOB_SCRAPE_PROMPT = 23
INTERVIEW_PREP_URL = 24
TEXT_HASHTAGS = 25
PHOTO_HASHTAGS = 26
VIDEO_HASHTAGS = 27
TAILOR_CV_TEXT = 28

# Keyboards
main_menu_keyboard = [
    ["1. 🌐 Social Agent"],
    ["2. 💼 Job Seeking Agent"],
    ["3. 💱 Forex Agent"],
    ["4. 📅 Daily Updates Agent"],
    ["0. ❌ Exit"],
]

job_seeking_menu_keyboard = [
    ["1. 🎨 Tailor CV & Cover Letter (from URL)"],
    ["2. 📝 Tailor CV & Cover Letter (from Raw Text)"],
    ["3. 🔍 Job Posting Scraper"],
    ["4. 🤖 Interview Prep Bot"],
    ["0. 🔙 Back to Main Menu"],
]

social_menu_keyboard = [
    ["1. 🚨 Update people about red folder news"],
    ["2. 📉 Post a serious trading advice"],
    ["3. 🎭 Post a persona-based quote"],
    ["4. ⚡ Check for breaking news"],
    ["5. 🚀 Run all standard pipelines"],
    ["6. ✍️ Create a custom manual post"],
    ["7. 🎬 Generate Video Reel Meme"],
    ["8. 🔁 Retry Failed Network Uploads"],
    ["9. ✂️ Download or Clip a Video"],
    ["0. 🔙 Back to Main Menu"],
]

manual_type_keyboard = [
    ["1. 📝 Text Quote Only"],
    ["2. 📸 Photo + Caption"],
    ["3. 🎬 Custom Video/Quote"],
    ["0. 🚫 Cancel"],
]

review_keyboard = [
    ["✅ Approve & Post"],
    ["✏️ Edit Image Quote / News Text"],
    ["✏️ Edit X Post Text"],
    ["✏️ Edit Meta Caption"],
    ["🔄 Reject & Regenerate"],
    ["🚫 Cancel"],
]

import subprocess


async def clip_command_start(update, context):
    if context.args:
        context.user_data["clip_url"] = context.args[0]
        return await ask_clip_type(update, context)
    else:
        await update.message.reply_text(
            "🔗 Please send the URL of the video you want to download or clip:"
        )
        return CLIP_URL


async def receive_clip_url(update, context):
    context.user_data["clip_url"] = update.message.text.strip()
    return await ask_clip_type(update, context)


async def ask_clip_type(update, context):
    reply_markup = ReplyKeyboardMarkup(
        [
            ["1. ⬇️ Download Whole Video"],
            ["2. ✂️ Clip a Specific Scene"],
            ["3. 🔍 Find Original Source (AI Search)"],
            ["0. 🚫 Cancel"],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "Do you want to download the whole video, clip a specific scene, or find the original source?",
        reply_markup=reply_markup,
    )
    return CLIP_TYPE


async def handle_clip_type(update, context):
    text = update.message.text.strip()
    if text.startswith("1"):
        return await execute_clip_download(update, context, is_clip=False)
    elif text.startswith("2"):
        await update.message.reply_text(
            "⏱️ What is the START time? (Format: HH:MM:SS or MM:SS)",
            reply_markup=ReplyKeyboardRemove(),
        )
        return CLIP_START
    elif text.startswith("3"):
        return await execute_original_source_search(update, context)
    else:
        await update.message.reply_text(
            "🚫 Canceled clip download.",
            reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True),
        )
        return MAIN_MENU


async def receive_clip_start(update, context):
    context.user_data["clip_start"] = update.message.text.strip()
    await update.message.reply_text(
        "⏱️ What is the END time? (Format: HH:MM:SS or MM:SS)"
    )
    return CLIP_END


async def receive_clip_end(update, context):
    context.user_data["clip_end"] = update.message.text.strip()
    return await execute_clip_download(update, context, is_clip=True)


async def download_video_robust(url, output_path):
    # Try TikTok API first for TikTok URLs since yt-dlp is broken
    if "tiktok.com" in url:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://www.tikwm.com/api/?url={url}", timeout=15)
                data = resp.json()
                if data.get("code") == 0 and "play" in data.get("data", {}):
                    video_url = data["data"]["play"]
                    cmd = ["curl", "-s", "-o", output_path, video_url]
                    process = await asyncio.create_subprocess_exec(*cmd)
                    await process.wait()
                    if process.returncode == 0:
                        return True, "", True # True, err, is_fallback
        except Exception as e:
            pass
            
    # Fallback to yt-dlp
    cmd = [
        os.path.join(os.path.dirname(sys.executable), "yt-dlp"),
        "--merge-output-format", "mp4",
        "-o", output_path,
        url,
    ]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate()
    return process.returncode == 0, stderr.decode(), False


async def execute_clip_download(update, context, is_clip):
    url = context.user_data.get("clip_url")
    start_time = context.user_data.get("clip_start") if is_clip else None
    end_time = context.user_data.get("clip_end") if is_clip else None

    if is_clip:
        await update.message.reply_text(
            f"⏳ Clipping from {start_time} to {end_time}... Please wait.",
            reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True),
        )
    else:
        await update.message.reply_text(
            f"⏳ Downloading full video... Please wait.",
            reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True),
        )

    target_dir = os.path.join(os.getcwd(), "agents", "social_agent", "state", "output")
    os.makedirs(target_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())[:8]
    output_path = os.path.join(target_dir, f"clip_{file_id}.mp4")

    # If trimming is requested
    if start_time and end_time:
        success, stderr, is_fallback = await download_video_robust(url, output_path)
        if success and is_fallback:
            # We used tikwm (downloaded whole video), so we must trim it with ffmpeg now
            temp_out = os.path.join(target_dir, f"temp_{file_id}.mp4")
            os.rename(output_path, temp_out)
            cmd_trim = ["ffmpeg", "-y", "-i", temp_out, "-ss", start_time, "-to", end_time, "-c:v", "libx264", "-c:a", "aac", output_path]
            await (await asyncio.create_subprocess_exec(*cmd_trim, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)).wait()
            if os.path.exists(temp_out):
                os.remove(temp_out)
        elif not success and not is_fallback:
            # Maybe yt-dlp needs download sections natively
            cmd = [
                os.path.join(os.path.dirname(sys.executable), "yt-dlp"),
                "--merge-output-format", "mp4",
                "--download-sections", f"*{start_time}-{end_time}",
                "-o", output_path,
                url,
            ]
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, err = await process.communicate()
            success = process.returncode == 0
            stderr = err.decode()
    else:
        success, stderr, is_fallback = await download_video_robust(url, output_path)

    if success:
        await update.message.reply_text(
            f"✅ Successfully clipped/downloaded video!"
        )
        try:
            with open(output_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id, 
                    video=video_file,
                    read_timeout=180,
                    write_timeout=180,
                    connect_timeout=180
                )
        except Exception as e:
            logger.error(f"Failed to send video: {e}")
    else:
        logger.error(f"Download error: {stderr}")
        await update.message.reply_text(
            "❌ Failed to clip/download video. Ensure the URL/timestamps are valid."
        )

    # Aggressive cleanup of standard clip downloads
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except:
            pass

    return MAIN_MENU


async def execute_original_source_search(update, context):
    async def safe_reply(msg, reply_markup=None):
        for attempt in range(3):
            try:
                if reply_markup:
                    await update.message.reply_text(msg, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(msg)
                return
            except Exception as e:
                logger.warning(f"Telegram reply failed (attempt {attempt+1}): {e}")
                await asyncio.sleep(1)
                
    url = context.user_data.get("clip_url")
    await safe_reply(
        "⏳ Downloading video to analyze original source... Please wait.",
        reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True),
    )

    target_dir = os.path.join(os.getcwd(), "agents", "social_agent", "state", "output")
    os.makedirs(target_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())[:8]
    temp_video_path = os.path.join(target_dir, f"temp_{file_id}.mp4")
    temp_original_path = None
    final_output_path = None
    
    # 1. Download video
    success, stderr, _ = await download_video_robust(url, temp_video_path)
    
    try:
        if not success:
            logger.error(f"yt-dlp/fallback error: {stderr}")
            await safe_reply("❌ Failed to download video for analysis.")
            return MAIN_MENU
            
        # 2. Analyze with VisionAgent
        await safe_reply("🤖 Analyzing frames with VisionAgent...")
        
        search_query = await coordinator.vision.identify_scene(temp_video_path)
        if not search_query:
            await safe_reply("❌ Failed to identify scene.")
            return MAIN_MENU
            
        await safe_reply(f"🔍 Identified as: '{search_query}'. Downloading original...")
        
        # 3. Download original via ytsearch
        # Append filters to search query to avoid YouTube Shorts and edited compilations
        refined_query = f"{search_query} original scene 1080p -shorts"
        
        temp_original_path = os.path.join(target_dir, f"temp_original_{file_id}.mp4")
        cmd_ytsearch = [
            os.path.join(os.path.dirname(sys.executable), "yt-dlp"),
            "--merge-output-format", "mp4",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--match-filter", "duration >= 60 & duration <= 900",
            "--extractor-args", "youtube:player-client=ios,tv",
            "-i", "--max-downloads", "1",
            "-o", temp_original_path,
            f"ytsearch10:{refined_query}",
        ]
        
        process_search = await asyncio.create_subprocess_exec(
            *cmd_ytsearch, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        s_stdout, s_stderr = await process_search.communicate()
        
        if os.path.exists(temp_original_path):
            await safe_reply("✂️ Auto-syncing timestamps to perfectly match your clip...")
            from shared.video_sync import find_clip_timestamps
            
            # 5. Find exact timestamps (run in thread to prevent blocking event loop)
            start_sec, end_sec = await asyncio.to_thread(
                find_clip_timestamps, temp_video_path, temp_original_path, target_dir
            )
            
            if start_sec == -1:
                await safe_reply("❌ The downloaded YouTube video didn't match the TikTok scene (Confidence threshold failed). Aborting.")
                return MAIN_MENU
            
            # Format seconds to HH:MM:SS
            def fmt_time(seconds):
                h = math.floor(seconds / 3600)
                m = math.floor((seconds % 3600) / 60)
                s = seconds % 60
                return f"{h:02d}:{m:02d}:{s:05.2f}"
                
            final_output_path = os.path.join(target_dir, f"original_clip_{file_id}.mp4")
            cmd_clip = [
                "ffmpeg", "-y", 
                "-ss", fmt_time(start_sec), "-to", fmt_time(end_sec),
                "-i", temp_original_path,
                "-i", temp_video_path,
                "-map", "0:v:0", "-map", "1:a:0?",
                "-c:v", "libx264", "-c:a", "aac", 
                "-shortest",
                final_output_path
            ]
            
            await (await asyncio.create_subprocess_exec(*cmd_clip, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)).wait()
            
            # Automatically build the agent's brain by saving to templates directory
            import re
            import shutil
            from shared.config import TEMPLATES_DIR
            
            os.makedirs(TEMPLATES_DIR, exist_ok=True)
            slugified_name = re.sub(r'[^a-z0-9_]', '', search_query.lower().replace(' ', '_'))[:30]
            template_path = os.path.join(TEMPLATES_DIR, f"{slugified_name}_{file_id}.mp4")
            shutil.copy2(final_output_path, template_path)
            
            await safe_reply(f"✅ Successfully downloaded and perfectly synced!\n\n🧠 Saved to Agent Memory as: `{os.path.basename(template_path)}`")
            
            try:
                with open(final_output_path, 'rb') as video_file:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id, 
                        video=video_file,
                        read_timeout=180,
                        write_timeout=180,
                        connect_timeout=180
                    )
            except Exception as e:
                logger.error(f"Failed to send video: {e}")
        else:
            logger.error(f"yt-dlp search error: {s_stderr.decode()}")
            await safe_reply("❌ Failed to download original source from YouTube.")
            
    except Exception as e:
        logger.error(f"AI Search command failed: {type(e).__name__}: {e}")
        try:
            await update.message.reply_text("❌ Failed to run AI source search.")
        except:
            pass
    finally:
        # Aggressive cleanup of all temp and output files to prevent storage leaks
        for f in [temp_video_path, temp_original_path, final_output_path]:
            if 'f' in locals() and f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        
    return MAIN_MENU


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global scheduler
    if scheduler and update.effective_chat:
        scheduler.set_target_chat_id(update.effective_chat.id)
    reply_markup = ReplyKeyboardMarkup(
        main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await update.message.reply_text(
        "=== Welcome to Chronos Master Orchestrator ===\nWhich agent do you want to use?",
        reply_markup=reply_markup,
    )
    return MAIN_MENU


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global scheduler
    if scheduler and update.effective_chat:
        scheduler.set_target_chat_id(update.effective_chat.id)
    text = update.message.text

    if text.startswith("0"):
        await update.message.reply_text(
            "Exiting Chronos Master Orchestrator. Goodbye!",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
    elif text.startswith("1"):
        reply_markup = ReplyKeyboardMarkup(
            social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "--- Social Agent Menu ---\nWhat do you want to do for today?",
            reply_markup=reply_markup,
        )
        return SOCIAL_MENU
    elif text.startswith("2"):
        reply_markup = ReplyKeyboardMarkup(
            job_seeking_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "--- Job Seeking Agent Menu ---\nWhat do you want to do?",
            reply_markup=reply_markup,
        )
        return JOB_SEEKING_MENU
    elif text.startswith("3") or text.startswith("4"):
        await update.message.reply_text(
            "This agent is still in production.\nChoose another agent or exit."
        )
        return MAIN_MENU
    else:
        await update.message.reply_text(
            "Invalid choice. Please choose from the keyboard."
        )
        return MAIN_MENU


async def social_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text.startswith("0"):
        reply_markup = ReplyKeyboardMarkup(
            main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "=== Welcome to Chronos Master Orchestrator ===\nWhich agent do you want to use?",
            reply_markup=reply_markup,
        )
        return MAIN_MENU

    elif text.startswith("1"):
        await update.message.reply_text(
            "⏳ Generating News draft. This might take a minute...",
            reply_markup=ReplyKeyboardRemove(),
        )
        try:
            draft = await coordinator.generate_news_draft()
            context.user_data["draft"] = draft
            msg = f"📝 *NEWS DRAFT GENERATED*\n\n*News Text:*\n{draft['news_text']}\n\n*X Post:*\n{draft['x_post_text']}\n\n*Meta Caption:*\n{draft['caption']}"
            reply_markup = ReplyKeyboardMarkup(
                review_keyboard, resize_keyboard=True, one_time_keyboard=False
            )
            await safe_reply(
                update.message, msg, reply_markup=reply_markup
            )
            return REVIEW_POST
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    elif text.startswith("2"):
        await update.message.reply_text(
            "⏳ Generating Serious Advice draft...", reply_markup=ReplyKeyboardRemove()
        )
        try:
            draft = await coordinator.generate_serious_draft()
            context.user_data["draft"] = draft
            msg = f"📝 *SERIOUS DRAFT GENERATED*\n\n*Image Quote:*\n{draft['quote']}\n\n*X Post:*\n{draft['x_post_text']}\n\n*Meta Caption:*\n{draft['caption']}"
            reply_markup = ReplyKeyboardMarkup(
                review_keyboard, resize_keyboard=True, one_time_keyboard=False
            )
            await safe_reply(
                update.message, msg, reply_markup=reply_markup
            )
            return REVIEW_POST
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    elif text.startswith("3"):
        await update.message.reply_text(
            "⏳ Generating Persona Quote draft...", reply_markup=ReplyKeyboardRemove()
        )
        try:
            draft = await coordinator.generate_persona_draft()
            context.user_data["draft"] = draft
            msg = f"📝 *PERSONA DRAFT GENERATED*\n\n*Image Quote:*\n{draft['quote']}\n\n*X Post:*\n{draft['x_post_text']}\n\n*Meta Caption:*\n{draft['caption']}"
            reply_markup = ReplyKeyboardMarkup(
                review_keyboard, resize_keyboard=True, one_time_keyboard=False
            )
            await safe_reply(
                update.message, msg, reply_markup=reply_markup
            )
            return REVIEW_POST
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    elif text.startswith("4"):
        await update.message.reply_text(
            "⏳ Checking for breaking news...", reply_markup=ReplyKeyboardRemove()
        )
        try:
            draft = await coordinator.generate_persona_draft(check_events=True)
            if draft:
                context.user_data["draft"] = draft
                msg = f"🚨 *BREAKING NEWS DRAFT GENERATED!*\n\n*Image Quote:*\n{draft['quote']}\n\n*X Post:*\n{draft['x_post_text']}\n\n*Meta Caption:*\n{draft['caption']}"
                reply_markup = ReplyKeyboardMarkup(
                    review_keyboard, resize_keyboard=True, one_time_keyboard=False
                )
                await safe_reply(
                    update.message, msg, reply_markup=reply_markup
                )
                return REVIEW_POST
            else:
                await update.message.reply_text("ℹ️ No breaking news found.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    elif text.startswith("5"):
        await update.message.reply_text(
            "⚠️ 'Run all pipelines' is currently disabled in manual review mode. Please run pipelines individually.",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif text.startswith("6"):
        reply_markup = ReplyKeyboardMarkup(
            manual_type_keyboard, resize_keyboard=True, one_time_keyboard=True
        )
        await update.message.reply_text(
            "--- Manual Custom Post ---\nChoose post type:", reply_markup=reply_markup
        )
        return MANUAL_TYPE

    elif text.startswith("7"):
        await update.message.reply_text(
            "⏳ Generating Video Reel Meme draft...", reply_markup=ReplyKeyboardRemove()
        )
        try:
            draft = await coordinator.generate_video_draft()
            context.user_data["draft"] = draft
            msg = f"📝 *VIDEO DRAFT GENERATED*\n\n*Overlay Text:*\n{draft['overlay_text']}\n\n*Caption:*\n{draft['caption']}\n\n*Hashtags:*\n{draft['hashtags']}"
            reply_markup = ReplyKeyboardMarkup(
                review_keyboard, resize_keyboard=True, one_time_keyboard=False
            )
            if "template_video" in draft and os.path.exists(draft["template_video"]):
                with open(draft["template_video"], "rb") as vfile:
                    await safe_reply_video(
                        update.message,
                        video=vfile,
                        caption=msg,
                        read_timeout=180,
                        write_timeout=180,
                        connect_timeout=180,
                        reply_markup=reply_markup,
                    )
            else:
                await safe_reply(
                    update.message, msg, reply_markup=reply_markup
                )
            return REVIEW_POST
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    elif text.startswith("8"):
        failed_uploads = context.user_data.get("failed_uploads")
        if not failed_uploads:
            await update.message.reply_text("ℹ️ There are no failed uploads to retry!")
            return SOCIAL_MENU

        await update.message.reply_text(
            "⏳ Retrying failed network uploads...", reply_markup=ReplyKeyboardRemove()
        )

        caption = failed_uploads.get("caption", "")
        media_path = failed_uploads.get("media_path", "")
        networks = failed_uploads.get("networks", {})
        x_post_text = failed_uploads.get("x_post_text", caption)

        try:
            x_success = not networks.get("x", False)
            meta_success = not networks.get("meta", False)

            if networks.get("x"):
                if media_path and media_path.endswith(".mp4"):
                    x_success = await coordinator.publisher.post_video_to_x(
                        x_post_text, media_path
                    )
                else:
                    x_success = await coordinator.publisher.post_to_x_stealth(
                        x_post_text, image_path=media_path
                    )

            if networks.get("meta"):
                if media_path and media_path.endswith(".mp4"):
                    meta_success = coordinator.publisher.post_reel_to_meta(
                        caption, media_path
                    )
                else:
                    meta_success = coordinator.publisher.post_to_meta(
                        caption, image_path=media_path
                    )

            x_icon = "✅" if x_success else "❌ FAILED"
            m_icon = "✅" if meta_success else "❌ FAILED"

            msg = f"✅ *Retry Complete!*\n\n*X Post ({x_icon})*\n*Meta ({m_icon})*"
            await update.message.reply_text(msg, parse_mode="Markdown")

            if x_success and meta_success:
                context.user_data["failed_uploads"] = None
            else:
                context.user_data["failed_uploads"]["networks"] = {
                    "x": not x_success,
                    "meta": not meta_success,
                }
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    elif text.startswith("9"):
        await update.message.reply_text(
            "🔗 Please send the URL of the video you want to download or clip:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return CLIP_URL

    else:
        await update.message.reply_text(
            "Invalid choice. Please choose from the keyboard."
        )
        return SOCIAL_MENU

    # Return to social menu on non-halting actions
    reply_markup = ReplyKeyboardMarkup(
        social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await update.message.reply_text(
        "--- Social Agent Menu ---\nWhat do you want to do next?",
        reply_markup=reply_markup,
    )
    return SOCIAL_MENU


# --- DRAFT REVIEW LOGIC ---
async def review_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    draft = context.user_data.get("draft")

    if not draft:
        reply_markup = ReplyKeyboardMarkup(
            social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "No draft found. Back to menu.", reply_markup=reply_markup
        )
        return SOCIAL_MENU

    if text.startswith("✅"):
        await update.message.reply_text(
            "⏳ Rendering media and publishing approved post...",
            reply_markup=ReplyKeyboardRemove(),
        )
        try:
            result = await coordinator.publish_approved_post(draft)
            x_success = result.get("x_success", True)
            meta_success = result.get("meta_success", True)

            x_icon = "✅" if x_success else "❌ FAILED"
            m_icon = "✅" if meta_success else "❌ FAILED"

            if draft["type"] == "video":
                msg = f"✅ *Pipeline Complete!*\n\n*X Post ({x_icon})*\n*Meta ({m_icon})*\n\n*Caption:*\n{result.get('meta_caption', '')}"
            else:
                msg = f"✅ *Pipeline Complete!*\n\n*X Post ({x_icon}):*\n{result.get('x_post_text', '')}\n\n*Meta Caption ({m_icon}):*\n{result.get('meta_caption', '')}"

            if not x_success or not meta_success:
                context.user_data["failed_uploads"] = {
                    "caption": result.get("meta_caption", ""),
                    "x_post_text": result.get("x_post_text", ""),
                    "media_path": result.get("image_path", ""),
                    "networks": {"x": not x_success, "meta": not meta_success},
                }
            else:
                context.user_data["failed_uploads"] = None
            media_path = result.get("image_path")
            if media_path:
                with open(media_path, "rb") as media:
                    if media_path.endswith(".mp4"):
                        await update.message.reply_video(
                            video=media,
                            caption=msg,
                            parse_mode="Markdown",
                            read_timeout=180,
                            write_timeout=180,
                            connect_timeout=180,
                        )
                    else:
                        await update.message.reply_photo(
                            photo=media,
                            caption=msg,
                            parse_mode="Markdown",
                            read_timeout=180,
                            write_timeout=180,
                            connect_timeout=180,
                        )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

        reply_markup = ReplyKeyboardMarkup(
            social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "--- Social Agent Menu ---\nWhat do you want to do next?",
            reply_markup=reply_markup,
        )
        return SOCIAL_MENU

    elif "Edit Image Quote" in text or "Edit News Text" in text:
        val = draft.get("quote") or draft.get("news_text") or draft.get("overlay_text")
        await update.message.reply_text(
            f"Current text: {val}\n\nPlease reply with the new text:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return EDIT_QUOTE

    elif "Edit X Post Text" in text:
        await update.message.reply_text(
            f"Current text: {draft.get('x_post_text', '')}\n\nPlease reply with the new text:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return EDIT_X_POST

    elif "Edit Meta Caption" in text:
        await update.message.reply_text(
            f"Current text: {draft.get('caption', '')}\n\nPlease reply with the new text:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return EDIT_CAPTION

    elif text.startswith("🔄"):
        await update.message.reply_text(
            "⏳ Regenerating draft...", reply_markup=ReplyKeyboardRemove()
        )
        try:
            if draft["type"] == "persona":
                new_draft = await coordinator.generate_persona_draft()
            elif draft["type"] == "news":
                new_draft = await coordinator.generate_news_draft()
            elif draft["type"] == "serious":
                new_draft = await coordinator.generate_serious_draft()
            elif draft["type"] == "video":
                new_draft = await coordinator.generate_video_draft()

            context.user_data["draft"] = new_draft
            val = (
                new_draft.get("quote")
                or new_draft.get("news_text")
                or new_draft.get("overlay_text")
            )
            msg = f"📝 *NEW DRAFT GENERATED*\n\n*Image/News/Overlay Text:*\n{val}\n\n*X Post:*\n{new_draft.get('x_post_text', '')}\n\n*Meta Caption:*\n{new_draft.get('caption', '')}"
            reply_markup = ReplyKeyboardMarkup(
                review_keyboard, resize_keyboard=True, one_time_keyboard=False
            )
            await safe_reply(
                update.message, msg, reply_markup=reply_markup
            )
            return REVIEW_POST
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            reply_markup = ReplyKeyboardMarkup(
                social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
            )
            await update.message.reply_text(
                "--- Social Agent Menu ---\nWhat do you want to do next?",
                reply_markup=reply_markup,
            )
            return SOCIAL_MENU

    elif text.startswith("🚫"):
        reply_markup = ReplyKeyboardMarkup(
            social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "Canceled. Back to Social Agent Menu.", reply_markup=reply_markup
        )
        return SOCIAL_MENU

    else:
        await update.message.reply_text(
            "Invalid choice. Please select from the keyboard."
        )
        return REVIEW_POST


# --- EDIT HANDLERS ---
async def edit_quote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data["draft"]
    if "quote" in draft:
        draft["quote"] = update.message.text
    elif "news_text" in draft:
        draft["news_text"] = update.message.text
    elif "overlay_text" in draft:
        draft["overlay_text"] = update.message.text

    val = draft.get("quote") or draft.get("news_text") or draft.get("overlay_text")
    msg = f"📝 *DRAFT UPDATED*\n\n*Image/News/Overlay Text:*\n{val}\n\n*X Post:*\n{draft.get('x_post_text', '')}\n\n*Meta Caption:*\n{draft.get('caption', '')}"
    reply_markup = ReplyKeyboardMarkup(
        review_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await safe_reply(
        update.message, msg, reply_markup=reply_markup
    )
    return REVIEW_POST


async def edit_x_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data["draft"]
    draft["x_post_text"] = update.message.text

    val = draft.get("quote") or draft.get("news_text") or draft.get("overlay_text")
    msg = f"📝 *DRAFT UPDATED*\n\n*Image/News/Overlay Text:*\n{val}\n\n*X Post:*\n{draft['x_post_text']}\n\n*Meta Caption:*\n{draft.get('caption', '')}"
    reply_markup = ReplyKeyboardMarkup(
        review_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await safe_reply(
        update.message, msg, reply_markup=reply_markup
    )
    return REVIEW_POST


async def edit_caption_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data["draft"]
    draft["caption"] = update.message.text

    val = draft.get("quote") or draft.get("news_text") or draft.get("overlay_text")
    msg = f"📝 *DRAFT UPDATED*\n\n*Image/News/Overlay Text:*\n{val}\n\n*X Post:*\n{draft.get('x_post_text', '')}\n\n*Meta Caption:*\n{draft['caption']}"
    reply_markup = ReplyKeyboardMarkup(
        review_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await safe_reply(
        update.message, msg, reply_markup=reply_markup
    )
    return REVIEW_POST


async def manual_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith("0"):
        reply_markup = ReplyKeyboardMarkup(
            social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "Canceled. Back to Social Agent Menu.", reply_markup=reply_markup
        )
        return SOCIAL_MENU
    elif text.startswith("1"):
        await update.message.reply_text(
            "✏️ Please send the wording for the quote (this goes on the image and X):",
            reply_markup=ReplyKeyboardRemove(),
        )
        return TEXT_QUOTE
    elif text.startswith("2"):
        await update.message.reply_text(
            "📸 Please send the photo you want to post (Make sure to send it as a Photo, not as a File).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return PHOTO_FILE
    elif text.startswith("3"):
        await update.message.reply_text(
            "🎬 Please send the raw video template (.mp4) you want to post.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return VIDEO_FILE
    else:
        await update.message.reply_text("Invalid choice.")
        return MANUAL_TYPE


# --- MANUAL TEXT LOGIC ---
async def receive_text_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["quote"] = update.message.text
    await update.message.reply_text(
        "📝 Great! Now send the caption for Instagram and Facebook:"
    )
    return TEXT_CAPTION


async def receive_text_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["caption"] = update.message.text
    await update.message.reply_text(
        "#️⃣ Finally, send the hashtags for this post (e.g., #trading #crypto):"
    )
    return TEXT_HASHTAGS


async def complete_manual_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hashtags = update.message.text
    caption = context.user_data["caption"]
    quote = context.user_data["quote"]

    full_x_post = f"{quote}\n\n{hashtags}".strip()
    full_meta_caption = f"{caption}\n\n{hashtags}".strip()

    await update.message.reply_text("⏳ Rendering image and posting...")
    try:
        image_path = await coordinator.publisher.render_tweet_image(
            quote, filename="manual_quote.png"
        )
        await coordinator.publisher.post_to_x_stealth(full_x_post)
        coordinator.publisher.post_to_meta(caption=full_meta_caption, image_path=image_path)

        msg = f"✅ *Manual Text Post Complete!*\n\n*X Post:*\n{full_x_post}\n\n*Meta Caption:*\n{full_meta_caption}"
        with open(image_path, "rb") as photo:
            await safe_reply_photo(
                update.message, photo=photo, caption=msg
            )

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

    reply_markup = ReplyKeyboardMarkup(
        social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await update.message.reply_text(
        "--- Social Agent Menu ---\nWhat do you want to do next?",
        reply_markup=reply_markup,
    )
    return SOCIAL_MENU


# --- MANUAL PHOTO LOGIC ---
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(
            "That doesn't look like a photo. Try again or type /cancel."
        )
        return PHOTO_FILE

    photo_file = await update.message.photo[-1].get_file()
    download_path = os.path.join(os.path.dirname(__file__), "temp_telegram_photo.jpg")
    await photo_file.download_to_drive(download_path)
    context.user_data["photo_path"] = download_path

    await update.message.reply_text(
        "📝 Photo received! Now send the text/caption for this post (goes on X and Meta):"
    )
    return PHOTO_CAPTION


async def receive_photo_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["caption"] = update.message.text
    await update.message.reply_text(
        "#️⃣ Finally, send the hashtags for this post (e.g., #trading #crypto):"
    )
    return PHOTO_HASHTAGS


async def complete_manual_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hashtags = update.message.text
    caption = context.user_data["caption"]
    photo_path = context.user_data["photo_path"]

    full_caption = f"{caption}\n\n{hashtags}".strip()

    await update.message.reply_text("⏳ Rendering Meta template and posting...")
    try:
        rendered_image_path = (
            await coordinator.publisher.render_tweet_with_custom_photo(
                quote_text=caption,
                custom_photo_path=photo_path,
                filename="manual_photo_quote.png",
            )
        )
        await coordinator.publisher.post_to_x_stealth(full_caption, image_path=photo_path)
        coordinator.publisher.post_to_meta(
            caption=full_caption, image_path=rendered_image_path
        )

        msg = f"✅ *Manual Photo Post Complete!*\n\n*X Post & Meta Caption:*\n{full_caption}"
        with open(rendered_image_path, "rb") as photo:
            await safe_reply_photo(
                update.message, photo=photo, caption=msg
            )

        if os.path.exists(photo_path):
            os.remove(photo_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

    reply_markup = ReplyKeyboardMarkup(
        social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await update.message.reply_text(
        "--- Social Agent Menu ---\nWhat do you want to do next?",
        reply_markup=reply_markup,
    )
    return SOCIAL_MENU


# --- MANUAL VIDEO LOGIC ---
async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video and not update.message.document:
        await update.message.reply_text(
            "That doesn't look like a video. Try again or type /cancel."
        )
        return VIDEO_FILE

    video_file_obj = update.message.video or update.message.document
    video_file = await video_file_obj.get_file()
    download_path = os.path.join(os.path.dirname(__file__), "temp_telegram_video.mp4")
    await video_file.download_to_drive(download_path)
    context.user_data["video_path"] = download_path

    await update.message.reply_text(
        "📝 Video received! Now send the meme quote (overlay text). If you don't want any text on the video, send 'NONE'."
    )
    return VIDEO_QUOTE


async def receive_video_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["video_quote"] = None if text.upper() == "NONE" else text

    await update.message.reply_text(
        "📝 Now send the caption for this video (goes on X and Meta):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return VIDEO_CAPTION


async def receive_video_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["caption"] = update.message.text
    await update.message.reply_text(
        "#️⃣ Finally, send the hashtags for your video (e.g., #trading #crypto):"
    )
    return VIDEO_HASHTAGS


async def complete_manual_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_hashtags = update.message.text.strip()
    quote = context.user_data["video_quote"]
    caption = context.user_data["caption"]

    await update.message.reply_text(
        "⏳ Rendering your video draft...",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        full_caption = f"{caption}\n\n{user_hashtags}".strip()

        draft = {
            "type": "video",
            "overlay_text": quote or "",
            "caption": caption,
            "hashtags": user_hashtags,
            "template_video": context.user_data["video_path"],
            "is_manual": True,
        }
        context.user_data["draft"] = draft

        msg = f"📝 *CUSTOM VIDEO DRAFT GENERATED*\n\n*Overlay Text:*\n{quote or 'NONE'}\n\n*Meta Caption:*\n{full_caption}"
        reply_markup = ReplyKeyboardMarkup(
            review_keyboard, resize_keyboard=True, one_time_keyboard=False
        )

        with open(draft["template_video"], "rb") as vfile:
            await safe_reply_video(
                update.message,
                video=vfile,
                caption=msg,
                read_timeout=180,
                write_timeout=180,
                connect_timeout=180,
                reply_markup=reply_markup,
            )

        return REVIEW_POST

    except Exception as e:
        logger.error(f"Failed to generate video draft: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        reply_markup = ReplyKeyboardMarkup(
            social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "--- Social Agent Menu ---\nWhat do you want to do next?",
            reply_markup=reply_markup,
        )
        return SOCIAL_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(
        main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await update.message.reply_text(
        "🚫 Canceled manual post.", reply_markup=reply_markup
    )
    return MAIN_MENU


async def _process_tailor_cv(update: Update, url_or_text: str):
    is_url = url_or_text.startswith("http://") or url_or_text.startswith("https://")
    label = url_or_text if is_url else "your submitted job description"
    await safe_reply(update.message, f"⏳ Tailoring CV and Cover Letter for {label}...\nThis might take a minute.")

    try:
        from agents.job_seeking.tailor_engine import TailorEngine
        from agents.job_seeking.cover_letter_generator import CoverLetterGenerator
        import uuid
        import os

        # 1. Scrape and generate Cover Letter text
        cover_gen = CoverLetterGenerator()
        letter_text, candidate_data = await cover_gen.generate_text(url_or_text)

        # 2. Get Brand Color
        engine = TailorEngine()
        color_hex = await engine.get_brand_color(url_or_text) if is_url else "#0F52BA"

        # 3. Generate Cover Letter PDF
        cl_pdf_path = await cover_gen.generate_pdf(letter_text, candidate_data, color_hex=color_hex)
        with open(cl_pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                caption=f"✅ Here is your tailored Cover Letter PDF for {label}.",
            )

        # 4. Generate CV PDF using the exact same candidate_data and brand color
        html_content = engine.render_html_cv(color_hex, candidate_data)
        
        company_name = candidate_data.get('target_company', '').strip()
        safe_company_name = "".join([c for c in company_name if c.isalnum() or c.isspace()]).replace(" ", "_").lower()
        if not safe_company_name:
            safe_company_name = f"company_{uuid.uuid4().hex[:8]}"

        cv_pdf_filename = f"{safe_company_name}_cv.pdf"
        cv_output_path = os.path.join(engine.output_dir, cv_pdf_filename)

        await engine.generate_pdf(html_content, cv_output_path)

        with open(cv_output_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                caption=f"✅ Here is the tailored CV for {label} (Brand Color: {color_hex}).",
            )

    except Exception as e:
        logger.error(f"Failed to tailor CV and Cover Letter: {e}")
        await safe_reply(update.message, f"❌ Failed to tailor CV and Cover Letter: {e}")

async def tailor_cv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await safe_reply(update.message, "🔗 Please provide a URL. Usage: /tailor_cv <url>")
        return

    url = context.args[0]
    await _process_tailor_cv(update, url)

    reply_markup = ReplyKeyboardMarkup(
        job_seeking_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await safe_reply(update.message, "--- Job Seeking Agent Menu ---\nWhat do you want to do next?", reply_markup=reply_markup)
    return JOB_SEEKING_MENU


async def job_seeking_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text.startswith("0"):
        reply_markup = ReplyKeyboardMarkup(
            main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "=== Welcome to Chronos Master Orchestrator ===\nWhich agent do you want to use?",
            reply_markup=reply_markup,
        )
        return MAIN_MENU

    elif text.startswith("1"):
        await update.message.reply_text(
            "🔗 Please send the job posting URL you want to tailor your CV and Cover Letter to:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return TAILOR_CV_URL

    elif text.startswith("2"):
        await update.message.reply_text(
            "📝 Please paste the raw text / description of the job posting to tailor your CV and Cover Letter:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return TAILOR_CV_TEXT

    elif text.startswith("3"):
        await update.message.reply_text(
            "⏳ Scanning remote job boards and matching against your profile...",
            reply_markup=ReplyKeyboardRemove(),
        )
        try:
            from agents.job_seeking.job_scraper import JobScraper
            scraper = JobScraper()
            matches = await scraper.find_matches(force_refresh_profile=True)
            await safe_reply(update.message, matches)
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to fetch jobs: {e}")
            
        reply_markup = ReplyKeyboardMarkup(
            job_seeking_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
        )
        await update.message.reply_text(
            "--- Job Seeking Agent Menu ---\nWhat do you want to do next?",
            reply_markup=reply_markup,
        )
        return JOB_SEEKING_MENU

    elif text.startswith("4"):
        await update.message.reply_text(
            "🔗 Please send the job posting URL or paste the job description to generate interview prep:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return INTERVIEW_PREP_URL

    else:
        await update.message.reply_text(
            "Invalid choice. Please select from the keyboard."
        )
        return JOB_SEEKING_MENU


async def receive_cover_letter_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text(
        f"⏳ Generating cover letter based on {url}...\nThis might take a minute."
    )
    try:
        from agents.job_seeking.cover_letter_generator import CoverLetterGenerator
        from agents.job_seeking.tailor_engine import TailorEngine

        generator = CoverLetterGenerator()
        cover_letter_text, candidate_data = await generator.generate_text(url)

        # Render and send professional PDF letterhead
        engine = TailorEngine()
        color_hex = await engine.get_brand_color(url) if url.startswith("http") else "#0F52BA"
        pdf_path = await generator.generate_pdf(cover_letter_text, candidate_data, color_hex=color_hex)

        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                caption=f"✅ Here is your tailored Cover Letter PDF for {url}.",
            )
    except Exception as e:
        logger.error(f"Failed to generate cover letter: {e}")
        await update.message.reply_text(f"❌ Failed to generate cover letter: {e}")

    reply_markup = ReplyKeyboardMarkup(
        job_seeking_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await update.message.reply_text(
        "--- Job Seeking Agent Menu ---\nWhat do you want to do next?",
        reply_markup=reply_markup,
    )
    return JOB_SEEKING_MENU


async def receive_interview_prep_url(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    url = update.message.text.strip()
    await update.message.reply_text(
        f"⏳ Generating interview prep based on {url}...\nThis might take a minute."
    )
    try:
        from agents.job_seeking.interview_prep import InterviewPrepBot

        bot = InterviewPrepBot()
        prep_guide = await bot.generate_prep_guide(url)
        await safe_reply(update.message, prep_guide)
    except Exception as e:
        logger.error(f"Failed to generate interview prep: {e}")
        await update.message.reply_text(f"❌ Failed to generate interview prep: {e}")

    reply_markup = ReplyKeyboardMarkup(
        job_seeking_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await update.message.reply_text(
        "--- Job Seeking Agent Menu ---\nWhat do you want to do next?",
        reply_markup=reply_markup,
    )
    return JOB_SEEKING_MENU


async def receive_cv_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await _process_tailor_cv(update, url)

    reply_markup = ReplyKeyboardMarkup(
        job_seeking_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await safe_reply(update.message, "--- Job Seeking Agent Menu ---\nWhat do you want to do next?", reply_markup=reply_markup)
    return JOB_SEEKING_MENU


async def receive_cv_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text.strip()
    await _process_tailor_cv(update, raw_text)

    reply_markup = ReplyKeyboardMarkup(
        job_seeking_menu_keyboard, resize_keyboard=True, one_time_keyboard=False
    )
    await safe_reply(update.message, "--- Job Seeking Agent Menu ---\nWhat do you want to do next?", reply_markup=reply_markup)
    return JOB_SEEKING_MENU


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "auto_publish_social":
        draft = context.bot_data.get("last_auto_draft")
        if not draft:
            await query.edit_message_text("⚠️ Draft expired or not found. Please generate a new one from the menu.")
            return
            
        await query.edit_message_text("⏳ Rendering graphic and publishing to X and Meta...")
        try:
            image_path = await coordinator.publisher.render_tweet_image(
                draft["quote"], filename="auto_daily_quote.png"
            )
            x_res = await coordinator.publisher.post_to_x_stealth(
                draft["x_post_text"], image_path=image_path
            )
            meta_res = coordinator.publisher.post_to_meta(
                caption=draft["caption"], image_path=image_path
            )
            await query.edit_message_text(
                f"✅ <b>Published Successfully!</b>\n\n"
                f"• X (Twitter): {'✅ Live' if x_res else '⚠️ Check logs'}\n"
                f"• Meta (IG/FB): {'✅ Live' if meta_res else '⚠️ Check logs'}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to auto-publish draft: {e}")
            await query.edit_message_text(f"❌ Failed to publish: {e}")
            
    elif data == "auto_regen_social":
        await query.edit_message_text("⏳ Regenerating daily meme draft...")
        try:
            new_draft = await coordinator.generate_persona_draft()
            if not new_draft:
                await query.edit_message_text("❌ Failed to generate new draft.")
                return
                
            context.bot_data["last_auto_draft"] = new_draft
            keyboard = [
                [
                    InlineKeyboardButton("🚀 1-Tap Publish to X & Meta", callback_data="auto_publish_social"),
                    InlineKeyboardButton("🔄 Regenerate", callback_data="auto_regen_social")
                ]
            ]
            msg = (
                "🎭 <b>CHRONOS DAILY MEME DRAFT READY</b>\n\n"
                f"<b>Meme Quote:</b>\n{new_draft['quote']}\n\n"
                f"<b>X Post:</b>\n{new_draft['x_post_text']}\n\n"
                f"<b>Meta Caption:</b>\n{new_draft['caption']}"
            )
            await query.edit_message_text(
                msg,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Failed to regenerate: {e}")


def main():
    global scheduler
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN is not set in .env!")
        return

    async def post_init(application):
        global scheduler
        scheduler = AutonomousScheduler(application)
        asyncio.create_task(scheduler.start_loop())

    # Set long timeouts so image rendering and posting doesn't time out the bot
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(300)
        .write_timeout(300)
        .connect_timeout(300)
        .pool_timeout(300)
        .post_init(post_init)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("clip", clip_command_start),
            CommandHandler("tailor_cv", tailor_cv_command),
        ],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)
            ],
            SOCIAL_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, social_menu_handler)
            ],
            MANUAL_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, manual_type_handler)
            ],
            REVIEW_POST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, review_post_handler)
            ],
            EDIT_QUOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_quote_handler)
            ],
            EDIT_X_POST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_x_post_handler)
            ],
            EDIT_CAPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_caption_handler)
            ],
            TEXT_QUOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text_quote)
            ],
            TEXT_CAPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text_caption)
            ],
            TEXT_HASHTAGS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, complete_manual_text)
            ],
            PHOTO_FILE: [MessageHandler(filters.PHOTO, receive_photo)],
            PHOTO_CAPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_photo_caption)
            ],
            PHOTO_HASHTAGS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, complete_manual_photo)
            ],
            VIDEO_FILE: [
                MessageHandler(filters.VIDEO | filters.Document.VIDEO, receive_video)
            ],
            VIDEO_QUOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_video_quote)
            ],
            VIDEO_CAPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_video_caption)
            ],
            VIDEO_HASHTAGS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, complete_manual_video)
            ],
            CLIP_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clip_url)
            ],
            CLIP_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_clip_type)
            ],
            CLIP_START: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clip_start)
            ],
            CLIP_END: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clip_end)
            ],
            JOB_SEEKING_MENU: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, job_seeking_menu_handler
                )
            ],
            TAILOR_CV_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_cv_url)
            ],
            TAILOR_CV_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_cv_text)
            ],
            INTERVIEW_PREP_URL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, receive_interview_prep_url
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            CommandHandler("tailor_cv", tailor_cv_command),
        ],
        allow_reentry=True,
    )

    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(conv_handler)

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Exception while handling an update: {context.error}")

    application.add_error_handler(error_handler)
    print("🤖 Telegram Orchestrator is running...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

import asyncio
import os
import sys
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ConversationHandler

# Ensure the root chronos directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import TELEGRAM_BOT_TOKEN
from agents.social_agent.social_coordinator import SocialAgentCoordinator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

coordinator = SocialAgentCoordinator()

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


# Keyboards
main_menu_keyboard = [
    ["1. 🌐 Social Agent"],
    ["2. 💼 Job Seeking Agent"],
    ["3. 💱 Forex Agent"],
    ["4. 📅 Daily Updates Agent"],
    ["0. ❌ Exit"]
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
    ["0. 🔙 Back to Main Menu"]
]

manual_type_keyboard = [
    ["1. 📝 Text Quote Only"],
    ["2. 📸 Photo + Caption"],
    ["3. 🎬 Custom Video/Quote"],
    ["0. 🚫 Cancel"]
]

review_keyboard = [
    ["✅ Approve & Post"],
    ["✏️ Edit Image Quote / News Text"],
    ["✏️ Edit X Post Text"],
    ["✏️ Edit Meta Caption"],
    ["🔄 Reject & Regenerate"],
    ["🚫 Cancel"]
]

import subprocess
from uuid import uuid4


async def clip_command_start(update, context):
    if context.args:
        context.user_data['clip_url'] = context.args[0]
        return await ask_clip_type(update, context)
    else:
        await update.message.reply_text("🔗 Please send the URL of the video you want to download or clip:")
        return CLIP_URL

async def receive_clip_url(update, context):
    context.user_data['clip_url'] = update.message.text.strip()
    return await ask_clip_type(update, context)

async def ask_clip_type(update, context):
    reply_markup = ReplyKeyboardMarkup([["1. ⬇️ Download Whole Video"], ["2. ✂️ Clip a Specific Scene"], ["0. 🚫 Cancel"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Do you want to download the whole video or clip a specific scene?", reply_markup=reply_markup)
    return CLIP_TYPE

async def handle_clip_type(update, context):
    text = update.message.text.strip()
    if text.startswith("1"):
        return await execute_clip_download(update, context, is_clip=False)
    elif text.startswith("2"):
        await update.message.reply_text("⏱️ What is the START time? (Format: HH:MM:SS or MM:SS)", reply_markup=ReplyKeyboardRemove())
        return CLIP_START
    else:
        await update.message.reply_text("🚫 Canceled clip download.", reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True))
        return MAIN_MENU

async def receive_clip_start(update, context):
    context.user_data['clip_start'] = update.message.text.strip()
    await update.message.reply_text("⏱️ What is the END time? (Format: HH:MM:SS or MM:SS)")
    return CLIP_END

async def receive_clip_end(update, context):
    context.user_data['clip_end'] = update.message.text.strip()
    return await execute_clip_download(update, context, is_clip=True)

async def execute_clip_download(update, context, is_clip):
    url = context.user_data.get('clip_url')
    
    if is_clip:
        start_time = context.user_data.get('clip_start')
        end_time = context.user_data.get('clip_end')
        # Simple validation/formatting
        start_time = ''.join(c for c in start_time if c.isdigit() or c in '.:')
        end_time = ''.join(c for c in end_time if c.isdigit() or c in '.:')
        if start_time.count(":") == 1: start_time = "00:" + start_time
        if end_time.count(":") == 1: end_time = "00:" + end_time
        
        await update.message.reply_text(f"⏳ Clipping from {start_time} to {end_time}... Please wait.", reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text(f"⏳ Downloading full video... Please wait.", reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True))
    
    target_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "video_templates", "general")
    os.makedirs(target_dir, exist_ok=True)
    
    file_id = str(uuid4())[:8]
    output_path = os.path.join(target_dir, f"clip_{file_id}.%(ext)s")
    
    cmd = [
        os.path.join(os.path.dirname(sys.executable), "yt-dlp"),
        "-f", "best[ext=mp4]/best",
        "-o", output_path,
        url
    ]
    
    if is_clip:
        cmd.insert(1, "--download-sections")
        cmd.insert(2, f"*{start_time}-{end_time}")
        
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            await update.message.reply_text(f"✅ Successfully saved to templates folder as clip_{file_id}.mp4!")
        else:
            logger.error(f"yt-dlp error: {stderr.decode()}")
            await update.message.reply_text("❌ Failed to clip/download video. Ensure the URL/timestamps are valid.")
    except Exception as e:
        logger.error(f"Clip command failed: {e}")
        await update.message.reply_text("❌ Failed to run clipping tool.")
        
    return MAIN_MENU

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        "=== Welcome to Chronos Master Orchestrator ===\nWhich agent do you want to use?",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text.startswith("0"):
        await update.message.reply_text("Exiting Chronos Master Orchestrator. Goodbye!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    elif text.startswith("1"):
        reply_markup = ReplyKeyboardMarkup(social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(
            "--- Social Agent Menu ---\nWhat do you want to do for today?",
            reply_markup=reply_markup
        )
        return SOCIAL_MENU
    elif text.startswith("2") or text.startswith("3") or text.startswith("4"):
        await update.message.reply_text("This agent is still in production.\nChoose another agent or exit.")
        return MAIN_MENU
    else:
        await update.message.reply_text("Invalid choice. Please choose from the keyboard.")
        return MAIN_MENU

async def social_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text.startswith("0"):
        reply_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text("=== Welcome to Chronos Master Orchestrator ===\nWhich agent do you want to use?", reply_markup=reply_markup)
        return MAIN_MENU
        
    elif text.startswith("1"):
        await update.message.reply_text("⏳ Generating News draft. This might take a minute...", reply_markup=ReplyKeyboardRemove())
        try:
            draft = await coordinator.generate_news_draft()
            context.user_data['draft'] = draft
            msg = f"📝 *NEWS DRAFT GENERATED*\n\n*News Text:*\n{draft['news_text']}\n\n*X Post:*\n{draft['x_post_text']}\n\n*Meta Caption:*\n{draft['caption']}"
            reply_markup = ReplyKeyboardMarkup(review_keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
            return REVIEW_POST
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            
    elif text.startswith("2"):
        await update.message.reply_text("⏳ Generating Serious Advice draft...", reply_markup=ReplyKeyboardRemove())
        try:
            draft = await coordinator.generate_serious_draft()
            context.user_data['draft'] = draft
            msg = f"📝 *SERIOUS DRAFT GENERATED*\n\n*Image Quote:*\n{draft['quote']}\n\n*X Post:*\n{draft['x_post_text']}\n\n*Meta Caption:*\n{draft['caption']}"
            reply_markup = ReplyKeyboardMarkup(review_keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
            return REVIEW_POST
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            
    elif text.startswith("3"):
        await update.message.reply_text("⏳ Generating Persona Quote draft...", reply_markup=ReplyKeyboardRemove())
        try:
            draft = await coordinator.generate_persona_draft()
            context.user_data['draft'] = draft
            msg = f"📝 *PERSONA DRAFT GENERATED*\n\n*Image Quote:*\n{draft['quote']}\n\n*X Post:*\n{draft['x_post_text']}\n\n*Meta Caption:*\n{draft['caption']}"
            reply_markup = ReplyKeyboardMarkup(review_keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
            return REVIEW_POST
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            
    elif text.startswith("4"):
        await update.message.reply_text("⏳ Checking for breaking news...", reply_markup=ReplyKeyboardRemove())
        try:
            draft = await coordinator.generate_persona_draft(check_events=True)
            if draft:
                context.user_data['draft'] = draft
                msg = f"🚨 *BREAKING NEWS DRAFT GENERATED!*\n\n*Image Quote:*\n{draft['quote']}\n\n*X Post:*\n{draft['x_post_text']}\n\n*Meta Caption:*\n{draft['caption']}"
                reply_markup = ReplyKeyboardMarkup(review_keyboard, resize_keyboard=True, one_time_keyboard=False)
                await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
                return REVIEW_POST
            else:
                await update.message.reply_text("ℹ️ No breaking news found.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            
    elif text.startswith("5"):
        await update.message.reply_text("⚠️ 'Run all pipelines' is currently disabled in manual review mode. Please run pipelines individually.", reply_markup=ReplyKeyboardRemove())
            
    elif text.startswith("6"):
        reply_markup = ReplyKeyboardMarkup(manual_type_keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("--- Manual Custom Post ---\nChoose post type:", reply_markup=reply_markup)
        return MANUAL_TYPE
        
    elif text.startswith("7"):
        await update.message.reply_text("⏳ Generating Video Reel Meme draft...", reply_markup=ReplyKeyboardRemove())
        try:
            draft = await coordinator.generate_video_draft()
            context.user_data['draft'] = draft
            msg = f"📝 *VIDEO DRAFT GENERATED*\n\n*Overlay Text:*\n{draft['overlay_text']}\n\n*Caption:*\n{draft['caption']}\n\n*Hashtags:*\n{draft['hashtags']}"
            reply_markup = ReplyKeyboardMarkup(review_keyboard, resize_keyboard=True, one_time_keyboard=False)
            if 'template_video' in draft and os.path.exists(draft['template_video']):
                with open(draft['template_video'], 'rb') as vfile:
                    await update.message.reply_video(video=vfile, caption=msg, parse_mode="Markdown", read_timeout=180, write_timeout=180, connect_timeout=180, reply_markup=reply_markup)
            else:
                await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
            return REVIEW_POST
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    elif text.startswith("8"):
        failed_uploads = context.user_data.get('failed_uploads')
        if not failed_uploads:
            await update.message.reply_text("ℹ️ There are no failed uploads to retry!")
            return SOCIAL_MENU
            
        await update.message.reply_text("⏳ Retrying failed network uploads...", reply_markup=ReplyKeyboardRemove())
        
        caption = failed_uploads.get('caption', '')
        media_path = failed_uploads.get('media_path', '')
        networks = failed_uploads.get('networks', {})
        x_post_text = failed_uploads.get('x_post_text', caption)
        
        try:
            x_success = not networks.get('x', False)
            meta_success = not networks.get('meta', False)
            
            if networks.get('x'):
                if media_path and media_path.endswith('.mp4'):
                    x_success = await coordinator.publisher.post_video_to_x(x_post_text, media_path)
                else:
                    x_success = await coordinator.publisher.post_to_x_stealth(x_post_text, image_path=media_path)
                    
            if networks.get('meta'):
                if media_path and media_path.endswith('.mp4'):
                    meta_success = coordinator.publisher.post_reel_to_meta(caption, media_path)
                else:
                    meta_success = coordinator.publisher.post_to_meta(caption, image_path=media_path)
                    
            x_icon = "✅" if x_success else "❌ FAILED"
            m_icon = "✅" if meta_success else "❌ FAILED"
            
            msg = f"✅ *Retry Complete!*\n\n*X Post ({x_icon})*\n*Meta ({m_icon})*"
            await update.message.reply_text(msg, parse_mode="Markdown")
            
            if x_success and meta_success:
                context.user_data['failed_uploads'] = None
            else:
                context.user_data['failed_uploads']['networks'] = {
                    'x': not x_success,
                    'meta': not meta_success
                }
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            
    elif text.startswith("9"):
        await update.message.reply_text("🔗 Please send the URL of the video you want to download or clip:", reply_markup=ReplyKeyboardRemove())
        return CLIP_URL
            
    else:
        await update.message.reply_text("Invalid choice. Please choose from the keyboard.")
        return SOCIAL_MENU

    # Return to social menu on non-halting actions
    reply_markup = ReplyKeyboardMarkup(social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text("--- Social Agent Menu ---\nWhat do you want to do next?", reply_markup=reply_markup)
    return SOCIAL_MENU

# --- DRAFT REVIEW LOGIC ---
async def review_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    draft = context.user_data.get('draft')
    
    if not draft:
        reply_markup = ReplyKeyboardMarkup(social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text("No draft found. Back to menu.", reply_markup=reply_markup)
        return SOCIAL_MENU

    if text.startswith("✅"):
        await update.message.reply_text("⏳ Rendering media and publishing approved post...", reply_markup=ReplyKeyboardRemove())
        try:
            result = await coordinator.publish_approved_post(draft)
            x_success = result.get('x_success', True)
            meta_success = result.get('meta_success', True)
            
            x_icon = "✅" if x_success else "❌ FAILED"
            m_icon = "✅" if meta_success else "❌ FAILED"
            
            if draft['type'] == 'video':
                msg = f"✅ *Pipeline Complete!*\n\n*X Post ({x_icon})*\n*Meta ({m_icon})*\n\n*Caption:*\n{result.get('meta_caption', '')}"
            else:
                msg = f"✅ *Pipeline Complete!*\n\n*X Post ({x_icon}):*\n{result.get('x_post_text', '')}\n\n*Meta Caption ({m_icon}):*\n{result.get('meta_caption', '')}"
            
            if not x_success or not meta_success:
                context.user_data['failed_uploads'] = {
                    'caption': result.get('meta_caption', ''),
                    'x_post_text': result.get('x_post_text', ''),
                    'media_path': result.get('image_path', ''),
                    'networks': {
                        'x': not x_success,
                        'meta': not meta_success
                    }
                }
            else:
                context.user_data['failed_uploads'] = None
            media_path = result.get("image_path")
            if media_path:
                with open(media_path, 'rb') as media:
                    if media_path.endswith('.mp4'):
                        await update.message.reply_video(video=media, caption=msg, parse_mode="Markdown", read_timeout=180, write_timeout=180, connect_timeout=180)
                    else:
                        await update.message.reply_photo(photo=media, caption=msg, parse_mode="Markdown", read_timeout=180, write_timeout=180, connect_timeout=180)
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            
        reply_markup = ReplyKeyboardMarkup(social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text("--- Social Agent Menu ---\nWhat do you want to do next?", reply_markup=reply_markup)
        return SOCIAL_MENU
        
    elif "Edit Image Quote" in text or "Edit News Text" in text:
        val = draft.get('quote') or draft.get('news_text') or draft.get('overlay_text')
        await update.message.reply_text(f"Current text: {val}\n\nPlease reply with the new text:", reply_markup=ReplyKeyboardRemove())
        return EDIT_QUOTE
        
    elif "Edit X Post Text" in text:
        await update.message.reply_text(f"Current text: {draft.get('x_post_text', '')}\n\nPlease reply with the new text:", reply_markup=ReplyKeyboardRemove())
        return EDIT_X_POST
        
    elif "Edit Meta Caption" in text:
        await update.message.reply_text(f"Current text: {draft.get('caption', '')}\n\nPlease reply with the new text:", reply_markup=ReplyKeyboardRemove())
        return EDIT_CAPTION
        
    elif text.startswith("🔄"):
        await update.message.reply_text("⏳ Regenerating draft...", reply_markup=ReplyKeyboardRemove())
        try:
            if draft['type'] == 'persona':
                new_draft = await coordinator.generate_persona_draft()
            elif draft['type'] == 'news':
                new_draft = await coordinator.generate_news_draft()
            elif draft['type'] == 'serious':
                new_draft = await coordinator.generate_serious_draft()
            elif draft['type'] == 'video':
                new_draft = await coordinator.generate_video_draft()
                
            context.user_data['draft'] = new_draft
            val = new_draft.get('quote') or new_draft.get('news_text') or new_draft.get('overlay_text')
            msg = f"📝 *NEW DRAFT GENERATED*\n\n*Image/News/Overlay Text:*\n{val}\n\n*X Post:*\n{new_draft.get('x_post_text', '')}\n\n*Meta Caption:*\n{new_draft.get('caption', '')}"
            reply_markup = ReplyKeyboardMarkup(review_keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
            return REVIEW_POST
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
            reply_markup = ReplyKeyboardMarkup(social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text("--- Social Agent Menu ---\nWhat do you want to do next?", reply_markup=reply_markup)
            return SOCIAL_MENU
            
    elif text.startswith("🚫"):
        reply_markup = ReplyKeyboardMarkup(social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text("Canceled. Back to Social Agent Menu.", reply_markup=reply_markup)
        return SOCIAL_MENU
        
    else:
        await update.message.reply_text("Invalid choice. Please select from the keyboard.")
        return REVIEW_POST

# --- EDIT HANDLERS ---
async def edit_quote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data['draft']
    if 'quote' in draft:
        draft['quote'] = update.message.text
    elif 'news_text' in draft:
        draft['news_text'] = update.message.text
    elif 'overlay_text' in draft:
        draft['overlay_text'] = update.message.text
    
    val = draft.get('quote') or draft.get('news_text') or draft.get('overlay_text')
    msg = f"📝 *DRAFT UPDATED*\n\n*Image/News/Overlay Text:*\n{val}\n\n*X Post:*\n{draft.get('x_post_text', '')}\n\n*Meta Caption:*\n{draft.get('caption', '')}"
    reply_markup = ReplyKeyboardMarkup(review_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    return REVIEW_POST

async def edit_x_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data['draft']
    draft['x_post_text'] = update.message.text
    
    val = draft.get('quote') or draft.get('news_text') or draft.get('overlay_text')
    msg = f"📝 *DRAFT UPDATED*\n\n*Image/News/Overlay Text:*\n{val}\n\n*X Post:*\n{draft['x_post_text']}\n\n*Meta Caption:*\n{draft.get('caption', '')}"
    reply_markup = ReplyKeyboardMarkup(review_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    return REVIEW_POST

async def edit_caption_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data['draft']
    draft['caption'] = update.message.text
    
    val = draft.get('quote') or draft.get('news_text') or draft.get('overlay_text')
    msg = f"📝 *DRAFT UPDATED*\n\n*Image/News/Overlay Text:*\n{val}\n\n*X Post:*\n{draft.get('x_post_text', '')}\n\n*Meta Caption:*\n{draft['caption']}"
    reply_markup = ReplyKeyboardMarkup(review_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
    return REVIEW_POST

async def manual_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith("0"):
        reply_markup = ReplyKeyboardMarkup(social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text("Canceled. Back to Social Agent Menu.", reply_markup=reply_markup)
        return SOCIAL_MENU
    elif text.startswith("1"):
        await update.message.reply_text("✏️ Please send the wording for the quote (this goes on the image and X):", reply_markup=ReplyKeyboardRemove())
        return TEXT_QUOTE
    elif text.startswith("2"):
        await update.message.reply_text("📸 Please send the photo you want to post (Make sure to send it as a Photo, not as a File).", reply_markup=ReplyKeyboardRemove())
        return PHOTO_FILE
    elif text.startswith("3"):
        await update.message.reply_text("🎬 Please send the raw video template (.mp4) you want to post.", reply_markup=ReplyKeyboardRemove())
        return VIDEO_FILE
    else:
        await update.message.reply_text("Invalid choice.")
        return MANUAL_TYPE

# --- MANUAL TEXT LOGIC ---
async def receive_text_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['quote'] = update.message.text
    await update.message.reply_text("📝 Great! Now send the caption for Instagram and Facebook:")
    return TEXT_CAPTION

async def complete_manual_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text
    quote = context.user_data['quote']
    
    await update.message.reply_text("⏳ Rendering image and posting...")
    try:
        image_path = await coordinator.publisher.render_tweet_image(quote, filename="manual_quote.png")
        await coordinator.publisher.post_to_x_stealth(quote)
        coordinator.publisher.post_to_meta(caption=caption, image_path=image_path)
        
        msg = f"✅ *Manual Text Post Complete!*\n\n*X Post:*\n{quote}\n\n*Meta Caption:*\n{caption}"
        with open(image_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=msg, parse_mode="Markdown")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    
    reply_markup = ReplyKeyboardMarkup(social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text("--- Social Agent Menu ---\nWhat do you want to do next?", reply_markup=reply_markup)
    return SOCIAL_MENU

# --- MANUAL PHOTO LOGIC ---
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("That doesn't look like a photo. Try again or type /cancel.")
        return PHOTO_FILE
    
    photo_file = await update.message.photo[-1].get_file()
    download_path = os.path.join(os.path.dirname(__file__), "temp_telegram_photo.jpg")
    await photo_file.download_to_drive(download_path)
    context.user_data['photo_path'] = download_path
    
    await update.message.reply_text("📝 Photo received! Now send the text/caption for this post (goes on X and Meta):")
    return PHOTO_CAPTION

async def complete_manual_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.text
    photo_path = context.user_data['photo_path']
    
    await update.message.reply_text("⏳ Rendering Meta template and posting...")
    try:
        rendered_image_path = await coordinator.publisher.render_tweet_with_custom_photo(
            quote_text=caption, 
            custom_photo_path=photo_path,
            filename="manual_photo_quote.png"
        )
        await coordinator.publisher.post_to_x_stealth(caption, image_path=photo_path)
        coordinator.publisher.post_to_meta(caption=caption, image_path=rendered_image_path)
        
        msg = f"✅ *Manual Photo Post Complete!*\n\n*X Post & Meta Caption:*\n{caption}"
        with open(rendered_image_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=msg, parse_mode="Markdown")
            
        if os.path.exists(photo_path):
            os.remove(photo_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    
    reply_markup = ReplyKeyboardMarkup(social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text("--- Social Agent Menu ---\nWhat do you want to do next?", reply_markup=reply_markup)
    return SOCIAL_MENU

# --- MANUAL VIDEO LOGIC ---
async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video and not update.message.document:
        await update.message.reply_text("That doesn't look like a video. Try again or type /cancel.")
        return VIDEO_FILE
    
    video_file_obj = update.message.video or update.message.document
    video_file = await video_file_obj.get_file()
    download_path = os.path.join(os.path.dirname(__file__), "temp_telegram_video.mp4")
    await video_file.download_to_drive(download_path)
    context.user_data['video_path'] = download_path
    
    await update.message.reply_text("📝 Video received! Now send the meme quote (overlay text). If you don't want any text on the video, send 'NONE'.")
    return VIDEO_QUOTE

async def receive_video_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    quote = None if text.upper() == "NONE" else text
    
    await update.message.reply_text("⏳ Generating meta caption and hashtags for your video...", reply_markup=ReplyKeyboardRemove())
    
    try:
        if quote:
            generated = coordinator.video_agent.generate_caption_for_meme(quote)
            caption = generated.get('caption', '')
            hashtags = generated.get('hashtags', '')
        else:
            caption = "Just trading things"
            hashtags = "#trading #forex #crypto"
            
        full_caption = f"{caption} {hashtags}".strip()
        
        draft = {
            "type": "video",
            "overlay_text": quote or "",
            "caption": caption,
            "hashtags": hashtags,
            "template_video": context.user_data['video_path'],
            "is_manual": True
        }
        context.user_data['draft'] = draft
        
        msg = f"📝 *CUSTOM VIDEO DRAFT GENERATED*\n\n*Overlay Text:*\n{quote or 'NONE'}\n\n*Meta Caption:*\n{full_caption}"
        reply_markup = ReplyKeyboardMarkup(review_keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        with open(draft['template_video'], 'rb') as vfile:
            await update.message.reply_video(video=vfile, caption=msg, parse_mode="Markdown", read_timeout=180, write_timeout=180, connect_timeout=180, reply_markup=reply_markup)
            
        return REVIEW_POST
        
    except Exception as e:
        logger.error(f"Failed to generate video draft: {e}")
        await update.message.reply_text(f"❌ Error: {e}")
        reply_markup = ReplyKeyboardMarkup(social_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text("--- Social Agent Menu ---\nWhat do you want to do next?", reply_markup=reply_markup)
        return SOCIAL_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text("🚫 Canceled manual post.", reply_markup=reply_markup)
    return MAIN_MENU

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN is not set in .env!")
        return

    # Set long timeouts so image rendering and posting doesn't time out the bot
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(300)
        .write_timeout(300)
        .connect_timeout(300)
        .pool_timeout(300)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("clip", clip_command_start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],
            SOCIAL_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, social_menu_handler)],
            MANUAL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_type_handler)],
            REVIEW_POST: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_post_handler)],
            EDIT_QUOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_quote_handler)],
            EDIT_X_POST: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_x_post_handler)],
            EDIT_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_caption_handler)],
            
            TEXT_QUOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text_quote)],
            TEXT_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, complete_manual_text)],
            
            PHOTO_FILE: [MessageHandler(filters.PHOTO, receive_photo)],
            PHOTO_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, complete_manual_photo)],
            
            VIDEO_FILE: [MessageHandler(filters.VIDEO | filters.Document.VIDEO, receive_video)],
            VIDEO_QUOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_video_quote)],
            
            CLIP_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clip_url)],
            CLIP_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_clip_type)],
            CLIP_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clip_start)],
            CLIP_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clip_end)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Exception while handling an update: {context.error}")
        
    application.add_error_handler(error_handler)
    print("🤖 Telegram Orchestrator is running...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()

import re

with open("orchestrator/telegram_orchestrator.py", "r") as f:
    content = f.read()

# Add states
states_add = """VIDEO_CAPTION = 15
CLIP_URL = 16
CLIP_TYPE = 17
CLIP_START = 18
CLIP_END = 19
"""
content = content.replace("VIDEO_CAPTION = 15", states_add)

# Add clip handlers
clip_handlers = """
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

async def start"""

# Remove old clip_command logic and replace with new interactive logic
content = re.sub(r"async def clip_command\(update: Update, context: ContextTypes.DEFAULT_TYPE\):.*?async def start", clip_handlers, content, flags=re.DOTALL)

# Add states to ConversationHandler
states_update = """            VIDEO_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, complete_manual_video)],
            
            CLIP_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clip_url)],
            CLIP_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_clip_type)],
            CLIP_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clip_start)],
            CLIP_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_clip_end)],"""
content = content.replace("            VIDEO_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, complete_manual_video)],", states_update)

# Update the entry point for /clip
content = content.replace('CommandHandler("clip", clip_command)', 'CommandHandler("clip", clip_command_start)')
# But clip is currently outside the conv handler. Let's add it to entry_points of conv handler!
content = content.replace('entry_points=[CommandHandler("start", start)],', 'entry_points=[CommandHandler("start", start), CommandHandler("clip", clip_command_start)],')

# Remove the standalone application.add_handler(CommandHandler("clip", ...))
content = content.replace('application.add_handler(CommandHandler("clip", clip_command))\n', '')
content = content.replace('application.add_handler(CommandHandler("clip", clip_command_start))\n', '')

with open("orchestrator/telegram_orchestrator.py", "w") as f:
    f.write(content)

import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from shared.config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"RECEIVED MESSAGE: {update.message.text}")
    await update.message.reply_text(f"ECHO: {update.message.text}")

app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.ALL, echo))
app.run_polling()

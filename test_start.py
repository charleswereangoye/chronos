import asyncio
from telegram import Update, Message, Chat, User
from orchestrator.telegram_orchestrator import start, MAIN_MENU
from unittest.mock import AsyncMock

async def main():
    update = Update(update_id=1)
    message = Message(message_id=1, date=None, chat=Chat(id=1, type="private"), text="/start")
    message.reply_text = AsyncMock()
    update.message = message
    
    context = AsyncMock()
    res = await start(update, context)
    print("Start returned:", res)
    print("Reply called with:", message.reply_text.call_args)

asyncio.run(main())

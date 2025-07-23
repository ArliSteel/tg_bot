# reset_webhook.py
import asyncio
import os
from telegram import Bot

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def reset():
    bot = Bot(token=BOT_TOKEN)

    print("Удаляю старый webhook...")
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Удалено.")

    print(f"Устанавливаю новый webhook: {WEBHOOK_URL}")
    await bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Новый webhook установлен.")

if __name__ == "__main__":
    asyncio.run(reset())

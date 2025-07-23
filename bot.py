import os
from aiohttp import web
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler
import logging

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # URL Render

# Включаем логирование
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я нейроассистент.")

async def handle(request):
    data = await request.json()
    logging.info(f"Получен апдейт: {data}")  # Логируем входящий апдейт
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

async def main():
    global application  # чтобы использовать application в handle
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    await application.initialize()  # важный вызов

    # Устанавливаем webhook
    await application.bot.set_webhook(url=WEBHOOK_URL)

    app = web.Application()
    app.router.add_post("/", handle)
    return app

if __name__ == "__main__":
    web.run_app(main(), port=10000)

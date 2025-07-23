import os
from aiohttp import web
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
import logging

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # URL Render

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я нейроассистент.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.reply_text(f"Вы написали: {user_text}")

async def handle(request):
    data = await request.json()
    logging.info(f"Получен апдейт: {data}")
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

async def main():
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)

    app = web.Application()
    app.router.add_post("/", handle)
    return app

if __name__ == "__main__":
    web.run_app(main(), port=10000)

import os
import logging
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Проверка переменных окружения
if not BOT_TOKEN or not WEBHOOK_URL:
    logger.critical("TELEGRAM_TOKEN или WEBHOOK_URL не установлены")
    exit(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start от {update.effective_user.id}")
    await update.message.reply_text("Бот работает! Отправьте ваш вопрос.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Сообщение от {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text("Тестовый ответ от бота")

async def handle_webhook(request):
    data = await request.json()
    logger.info(f"Получен апдейт: {data.get('update_id')}")
    bot_app = request.app['bot_app']
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return web.Response()

async def init_app():
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Инициализация и установка вебхука
    await bot_app.initialize()
    logger.info(f"Установка вебхука: {WEBHOOK_URL}")
    await bot_app.bot.set_webhook(WEBHOOK_URL)

    # Создание aiohttp-приложения
    app = web.Application()
    app['bot_app'] = bot_app
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    return app

if __name__ == "__main__":
    app = asyncio.run(init_app())
    web.run_app(app, host="0.0.0.0", port=10000)

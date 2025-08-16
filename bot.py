import os
import json
import httpx
import logging
import asyncio
from aiohttp import web
from telegram import Update, Bot
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка переменных окружения
REQUIRED_ENV = ["TELEGRAM_TOKEN", "WEBHOOK_URL", "YANDEX_API_KEY", "YANDEX_FOLDER_ID"]
missing = [var for var in REQUIRED_ENV if not os.getenv(var)]
if missing:
    logger.critical(f"Отсутствуют переменные окружения: {missing}")
    exit(1)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

# Конфигурация бота
CONFIG = {
    "name": "Right.style89",
    "admin_chat_id": 370635558  # Ваш chat_id для ошибок
}

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=True)
    if CONFIG["admin_chat_id"]:
        await context.bot.send_message(
            chat_id=CONFIG["admin_chat_id"],
            text=f"⚠️ Ошибка: {context.error}"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛠️ Бот работает! Отправьте ваш вопрос.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info(f"Получено сообщение: {update.message.text}")
        await update.message.reply_text("🔍 Обрабатываю ваш запрос...")
        
        # Здесь будет вызов YandexGPT
        await update.message.reply_text("✅ Тестовый ответ от бота")
        
    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка")

async def handle_webhook(request):
    try:
        data = await request.json()
        logger.info(f"Получен апдейт: {data.get('update_id')}")
        
        app = request.app['bot_app']
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response()
    except Exception as e:
        logger.critical(f"Webhook error: {e}")
        return web.Response(status=500)

async def setup_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    return app

async def init_app():
    bot_app = await setup_bot()
    
    # Проверка вебхука
    async with bot_app:
        webhook_info = await bot_app.bot.get_webhook_info()
        logger.info(f"Текущий вебхук: {webhook_info.url}")
        
        if webhook_info.url != WEBHOOK_URL:
            logger.info("Устанавливаю новый вебхук...")
            await bot_app.bot.set_webhook(WEBHOOK_URL)
    
    app = web.Application()
    app['bot_app'] = bot_app
    app.router.add_post("/webhook", handle_webhook)

    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    return app

if __name__ == "__main__":
    logger.info("🚀 Запуск бота...")
    try:
        app = asyncio.run(init_app())
        web.run_app(app, host="0.0.0.0", port=10000)
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        exit(1)

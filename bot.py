import os
import json
import logging
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Логи
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN or not WEBHOOK_URL:
    logger.critical("Не заданы TELEGRAM_TOKEN или WEBHOOK_URL")
    exit(1)

# Обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает! Отправьте сообщение.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    logger.info(f"Получено сообщение: {text}")
    await update.message.reply_text(f"🔍 Вы написали: {text}")

# Вебхук - обработка POST запросов от Telegram
async def handle_webhook(request):
    try:
        data = await request.json()
        logger.info(f"Вебхук получен: {data.get('update_id')}")
        
        update = Update.de_json(data, request.app['bot_app'].bot)
        await request.app['bot_app'].process_update(update)
        return web.Response(text="OK")
    except Exception as e:
        logger.error(f"Ошибка webhook: {e}")
        return web.Response(status=500, text="Error")

# Универсальный обработчик для GET/HEAD запросов
async def handle_health_check(request):
    logger.info(f"Health check: {request.method} {request.path}")
    return web.Response(text="Bot is alive")

# Настройка бота
async def setup_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    return app

# Инициализация aiohttp
async def init_app():
    bot_app = await setup_bot()

    # Установка вебхука
    async with bot_app:
        webhook_info = await bot_app.bot.get_webhook_info()
        logger.info(f"Текущий вебхук: {webhook_info.url}")
        
        if webhook_info.url != WEBHOOK_URL:
            logger.info(f"Устанавливаю вебхук: {WEBHOOK_URL}")
            await bot_app.bot.set_webhook(
                WEBHOOK_URL,
                allowed_updates=["message", "callback_query"]
            )

    app = web.Application()
    app['bot_app'] = bot_app
    
    # КРИТИЧЕСКИЕ ИЗМЕНЕНИЯ:
    app.router.add_post("/", handle_webhook)  # POST - от Telegram
    app.router.add_route("*", "/", handle_health_check)  # Все методы для корня
    app.router.add_get("/health", handle_health_check)
    
    return app

# Запуск
if __name__ == "__main__":
    logger.info("🚀 Запуск бота...")
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    web.run_app(app, host="0.0.0.0", port=10000)
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
        # Логируем сырые данные для отладки
        data = await request.json()
        logger.info(f"Received webhook data: {json.dumps(data, indent=2)}")
        
        # Создаем Update объект
        update = Update.de_json(data, request.app['bot_app'].bot)
        
        # Обрабатываем апдейт
        await request.app['bot_app'].process_update(update)
        
        return web.Response(text="OK", status=200)
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return web.Response(text=f"Error: {str(e)}", status=500)

# Универсальный обработчик для GET/HEAD запросов
async def handle_health_check(request):
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
    app = web.Application()
    app['bot_app'] = bot_app
    
    # Маршруты
    app.router.add_post("/", handle_webhook)
    app.router.add_route("*", "/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    
    return app

# Запуск
if __name__ == "__main__":
    logger.info("🚀 Запуск бота...")
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    web.run_app(app, host="0.0.0.0", port=10000)
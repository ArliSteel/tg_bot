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

# Простой обработчик
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Эхо: {update.message.text}")

# Упрощенный вебхук
async def handle_webhook(request):
    try:
        data = await request.json()
        logger.info(f"Received data: {json.dumps(data)}")
        
        # Минимальная валидация
        if 'message' not in data or 'text' not in data.get('message', {}):
            return web.Response(text="Invalid data", status=400)
        
        # Создаем простой update
        update = Update(de_json=data)
        
        # Обрабатываем текст
        text = data['message']['text']
        if text.startswith('/'):
            await start(update, None)
        else:
            await echo(update, None)
            
        return web.Response(text="OK")
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return web.Response(text=f"Error: {str(e)}", status=500)

async def handle_health_check(request):
    return web.Response(text="Bot is alive")

async def init_app():
    app = web.Application()
    
    # Только базовые маршруты
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/health", handle_health_check)
    app.router.add_get("/", handle_health_check)
    
    return app

if __name__ == "__main__":
    logger.info("🚀 Запуск упрощенного бота...")
    try:
        app = asyncio.run(init_app())
        web.run_app(app, host="0.0.0.0", port=10000)
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
import asyncio
import os
import json
import logging
from aiohttp import web

from config import load_config
from telegram import Update
from telegram.ext import Application
from handlers.base import register_base_handlers
from handlers.faq import register_faq_handlers
from handlers.messages import register_message_handlers
from services.state_manager import user_state
from services.security import security
from utils.logging import setup_logging

# Настройка логирования
setup_logging(environment=os.getenv('ENVIRONMENT', 'staging'))
logger = logging.getLogger(__name__)

# Глобальная переменная для бота
bot_app = None

async def handle_webhook(request):
    """Обработчик вебхука от Telegram с проверкой секретного токена"""
    try:
        config = load_config()
        
        # Проверка секретного токена
        expected_token = config.WEBHOOK_SECRET
        received_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        
        if expected_token != received_token:
            logger.warning(f"Invalid webhook secret token: {received_token}")
            return web.Response(text="Invalid token", status=403)
        
        data = await request.json()
        update_id = data.get('update_id', 'unknown')
        logger.info(f"Получен вебхук #{update_id}")
        
        # Проверка безопасности на уровне вебхука
        if not security.check_global_limit(max_requests=config.MAX_REQUESTS_PER_MINUTE, period=60):
            return web.Response(text="Rate limit exceeded", status=429)
        
        if bot_app is None:
            logger.error("Бот не инициализирован при обработке вебхука")
            return web.Response(text="Bot not initialized", status=500)
        
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        
        return web.Response(text="OK")
        
    except json.JSONDecodeError:
        logger.error("Неверный JSON в вебхуке")
        return web.Response(text="Invalid JSON", status=400)
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return web.Response(text="OK")  # Всегда возвращаем OK для Telegram

async def handle_health(request):
    """Проверка здоровья сервиса"""
    return web.Response(text="✅ Bot is alive and healthy")

async def initialize_bot():
    """Инициализация бота один раз при старте"""
    global bot_app
    
    try:
        config = load_config()
        logger.info("Инициализация бота...")
        
        bot_app = Application.builder().token(config.BOT_TOKEN).build()
        
        # Регистрация обработчиков
        register_base_handlers(bot_app)
        register_faq_handlers(bot_app)
        register_message_handlers(bot_app)
        
        # Запускаем очистку очередей
        asyncio.create_task(user_state.cleanup_queues())
        
        # Инициализация и установка вебхука с секретным токеном
        await bot_app.initialize()
        await bot_app.bot.set_webhook(
            config.WEBHOOK_URL,
            allowed_updates=["message", "callback_query"],
            secret_token=config.WEBHOOK_SECRET
        )
        
        logger.info(f"Вебхук установлен: {config.WEBHOOK_URL}")
        logger.info("Бот успешно инициализирован")
        
    except Exception as e:
        logger.critical(f"Ошибка инициализации бота: {e}")
        raise

async def init_app():
    """Инициализация aiohttp приложения"""
    await initialize_bot()
    
    app = web.Application()
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/", handle_health)
    
    return app

def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск бота с YandexGPT...")
    
    try:
        # Настройка event loop для совместимости
        if os.name == 'nt':  # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        app = loop.run_until_complete(init_app())
        web.run_app(app, host="0.0.0.0", port=10000)
        
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
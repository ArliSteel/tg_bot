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
# from services.database import init_database  # 🔥 ЗАКОММЕНТИРОВАЛИ - временно отключаем БД
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
        expected_token = config.webhook_secret
        received_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        
        if expected_token != received_token:
            logger.warning(f"Invalid webhook secret token: {received_token}")
            return web.Response(text="Invalid token", status=403)
        
        data = await request.json()
        update_id = data.get('update_id', 'unknown')
        logger.info(f"Получен вебхук #{update_id}")
        
        # Проверка безопасности на уровне вебхука
        if not security.check_global_limit(max_requests=config.max_requests_per_minute, period=60):
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

async def handle_debug(request):
    """Endpoint для отладки переменных окружения"""
    import os
    debug_info = {
        "TELEGRAM_TOKEN_set": bool(os.getenv("TELEGRAM_TOKEN")),
        "YANDEX_API_KEY_set": bool(os.getenv("YANDEX_API_KEY")),
        "YANDEX_FOLDER_ID_set": bool(os.getenv("YANDEX_FOLDER_ID")),
        "DATABASE_URL_set": bool(os.getenv("DATABASE_URL")),
        "WEBHOOK_URL": os.getenv("WEBHOOK_URL"),
        "WEBHOOK_SECRET_set": bool(os.getenv("WEBHOOK_SECRET")),
        "database_initialized": False,  # 🔥 ОТКЛЮЧЕНО
        "status": "healthy"
    }
    return web.json_response(debug_info)

async def initialize_bot():
    """Инициализация бота один раз при старте"""
    global bot_app
    
    try:
        config = load_config()
        logger.info("Инициализация бота...")
        
        # Исправляем регистр атрибутов
        bot_app = Application.builder().token(config.bot_token).build()
        
        # Регистрация обработчиков
        register_base_handlers(bot_app)
        register_faq_handlers(bot_app)
        register_message_handlers(bot_app)
        
        # 🔥 ВРЕМЕННО ОТКЛЮЧЕНО: Инициализация базы данных
        # logger.info("Инициализация базы данных...")
        # await init_database()
        # logger.info("✅ База данных успешно инициализирована")
        logger.info("⚠️ База данных временно отключена")
        
        # Запускаем очистку очередей
        asyncio.create_task(user_state.cleanup_queues())
        
        # Инициализация и установка вебхука с секретным токеном
        await bot_app.initialize()
        await bot_app.bot.set_webhook(
            config.webhook_url,
            allowed_updates=["message", "callback_query"],
            secret_token=config.webhook_secret
        )
        
        logger.info(f"Вебхук установлен: {config.webhook_url}")
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
    app.router.add_get("/debug", handle_debug)
    app.router.add_get("/", handle_health)
    
    return app

def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск бота с YandexGPT (база данных временно отключена)...")
    
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
import asyncio  # Добавьте эту строку в самый верх файла
import os
import json
import httpx
import logging
import tempfile
import subprocess
from aiohttp import web
from pydub import AudioSegment
from telegram import Update, Bot, File, Voice
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

# Проверка переменных
if not all([BOT_TOKEN, WEBHOOK_URL, YANDEX_API_KEY, YANDEX_FOLDER_ID]):
    logger.error("Отсутствуют необходимые переменные окружения!")
    exit(1)

# Конфигурация салона
SALON_INFO = {
    "name": "Right.style89 | Студия восстановления автомобилей",
    "address": "г. Салехард, территория Площадка № 13, с 26",
    "contacts": "https://vk.com/right.style89",
    "working_hours": "10:00-22:00 (без выходных)",
    "services": {
        "Удаление вмятин": "от 2500₽",
        "Ремонт царапин": "от 1800₽",
        "Ремонт сколов": "от 5000₽"
    }
}

SYSTEM_PROMPT = f"""..."""  # Ваш промпт без изменений

class YandexGPTClient:
    @staticmethod
    async def generate_response(user_message: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                    headers={
                        "Authorization": f"Bearer {YANDEX_API_KEY}",
                        "x-folder-id": YANDEX_FOLDER_ID
                    },
                    json={
                        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt",
                        "messages": [
                            {"role": "system", "text": SYSTEM_PROMPT},
                            {"role": "user", "text": user_message}
                        ]
                    }
                )
                response.raise_for_status()
                return response.json()['result']['alternatives'][0]['message']['text'].strip()
        except Exception as e:
            logger.error(f"YandexGPT error: {str(e)}")
            return "⚠️ Произошла ошибка. Попробуйте позже."

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        logger.info(f"Вопрос: {text}")
        reply = await YandexGPTClient.generate_response(text)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Text handler error: {e}")
        await update.message.reply_text("🔧 Техническая ошибка. Мы уже работаем над исправлением.")

async def health_check(request):
    """Для мониторинга работы"""
    return web.Response(text="Bot is alive")

async def setup_application():
    """Инициализация бота с обработкой ошибок"""
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Регистрация обработчиков
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Проверка вебхука
        bot = Bot(token=BOT_TOKEN)
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Current webhook: {webhook_info.url}")
        
        if webhook_info.url != WEBHOOK_URL:
            logger.info("Updating webhook...")
            await bot.set_webhook(WEBHOOK_URL)
        
        return app
    except Exception as e:
        logger.critical(f"Failed to setup application: {e}")
        raise

async def main():
    """Точка входа с обработкой ошибок"""
    try:
        app = web.Application()
        app.router.add_post("/", handle_webhook)
        app.router.add_get("/health", health_check)
        
        global application
        application = await setup_application()
        
        return app
    except Exception as e:
        logger.critical(f"Failed to start: {e}")
        exit(1)

if __name__ == "__main__":
    # Усиленное логирование при старте
    logger.info("Starting bot with config:")
    logger.info(f"Bot token: {BOT_TOKEN[:5]}...{BOT_TOKEN[-5:]}")
    logger.info(f"Webhook URL: {WEBHOOK_URL}")
    
    try:
        # Создаем event loop вручную
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаем приложение
        app = loop.run_until_complete(main())
        web.run_app(app, port=10000, access_log=logger)
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        exit(1)

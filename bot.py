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

# Загрузка переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

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

SYSTEM_PROMPT = f"""
Ты ассистент салона по детейлингу автомобилей "{SALON_INFO['name']}".
Контакт: {SALON_INFO['contacts']}
Адрес: {SALON_INFO['address']}
Работаем: {SALON_INFO['working_hours']}

Правила:
1. Отвечай только по теме детейлинга
2. Цены указывай как ориентировочные
3. На вопросы не по теме говори: "Уточните у администратора"
"""

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Добро пожаловать в {SALON_INFO['name']}!\n"
        f"Контакты: {SALON_INFO['contacts']}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        logger.info(f"Вопрос: {text}")
        reply = await YandexGPTClient.generate_response(text)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("🔧 Техническая ошибка.")

async def handle_webhook(request):
    data = await request.json()
    logger.info(f"Incoming update: {data.get('update_id')}")
    
    application = request.app['bot_app']
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

async def setup_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Проверка вебхука
    bot = Bot(token=BOT_TOKEN)
    webhook_info = await bot.get_webhook_info()
    logger.info(f"Current webhook: {webhook_info.url}")
    
    if webhook_info.url != WEBHOOK_URL:
        logger.info("Setting new webhook...")
        await bot.set_webhook(WEBHOOK_URL)
    
    return app

async def init_app():
    """Инициализация приложения"""
    bot_app = await setup_bot()
    
    app = web.Application()
    app['bot_app'] = bot_app
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    
    return app

if __name__ == "__main__":
    logger.info("Starting bot...")
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    web.run_app(app, host="0.0.0.0", port=10000)

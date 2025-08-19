import os
import json
import httpx
import logging
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка конфигов
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

# Проверка переменных
if not all([BOT_TOKEN, WEBHOOK_URL, YANDEX_API_KEY, YANDEX_FOLDER_ID]):
    logger.critical("Отсутствуют необходимые переменные окружения!")
    exit(1)

# Конфигурация салона
SALON_INFO = {
    "name": "Lumiere",
    "address": "Москва, ул. Тверская, 18",
    "contacts": "+7 (495) 123-45-67",
    "working_hours": "10:00-22:00 (без выходных)",
    "services": {
        "Женские стрижки": "от 2500₽",
        "Мужские стрижки": "от 1800₽",
        "Окрашивание волос": "от 5000₽",
        "Маникюр": "от 2000₽",
        "Педикюр": "от 2500₽",
        "Детилинг (базовый)": "от 5000₽",
        "Детилинг (премиум)": "от 15000₽"
    }
}

# Системный промпт
SYSTEM_PROMPT = f"""
Ты ассистент салона красоты и детейлинга "{SALON_INFO['name']}".

**Контактная информация:**
- Адрес: {SALON_INFO['address']}
- Телефон: {SALON_INFO['contacts']}
- Режим работы: {SALON_INFO['working_hours']}

**Основные услуги и цены:**
{json.dumps(SALON_INFO['services'], indent=2, ensure_ascii=False)}

**Правила общения:**
1. Вежливый и профессиональный тон
2. Не давать медицинских рекомендаций
3. На вопросы не по теме отвечать: "Этот вопрос лучше уточнить у администратора"
4. На агрессию реагировать спокойно
5. Все цены указывать как ориентировочные

**Важно:**
- Если вопрос про акции - отвечай "Актуальные акции уточняйте по телефону"
- Не придумывай несуществующие услуги
- На запрос записи предлагай позвонить по телефону салона
"""

# Настройки YandexGPT
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
MODEL_CONFIG = {
    "temperature": 0.3,
    "max_tokens": 300
}

class YandexGPTClient:
    @staticmethod
    async def generate_response(user_message: str) -> str:
        """Генерация ответа через YandexGPT API"""
        headers = {
            "Authorization": f"Bearer {YANDEX_API_KEY}",
            "x-folder-id": YANDEX_FOLDER_ID,
            "Content-Type": "application/json"
        }
        
        payload = {
            "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": MODEL_CONFIG["temperature"],
                "maxTokens": MODEL_CONFIG["max_tokens"]
            },
            "messages": [
                {
                    "role": "system",
                    "text": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "text": user_message
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(YANDEX_GPT_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data['result']['alternatives'][0]['message']['text'].strip()
                
        except Exception as e:
            logger.error(f"YandexGPT error: {str(e)}")
            return "Извините, произошла техническая ошибка. Пожалуйста, попробуйте позже."

# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_msg = (
        f"Добро пожаловать в {SALON_INFO['name']}!\n\n"
        f"Я помогу вам с информацией о наших услугах.\n"
        f"Телефон для записи: {SALON_INFO['contacts']}"
    )
    await update.message.reply_text(welcome_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_text = update.message.text
    logger.info(f"Received message: {user_text}")
    
    reply = await YandexGPTClient.generate_response(user_text)
    
    # Фильтрация нежелательных фраз
    banned_phrases = ["лечебн", "медицинск", "гарантируем", "100%"]
    if any(phrase in reply.lower() for phrase in banned_phrases):
        reply = "Этот вопрос требует консультации специалиста."
    
    await update.message.reply_text(reply)

# Webhook Handler
async def handle_webhook(request):
    """Обработчик вебхука"""
    try:
        data = await request.json()
        logger.info(f"Webhook received: {data.get('update_id')}")
        
        # Получаем bot_app из контекста приложения
        bot_app = request.app['bot_app']
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        
        return web.Response(text="OK")
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(text="OK")  # Всегда возвращаем OK для Telegram

# Health check
async def handle_health(request):
    return web.Response(text="Bot is alive")

# Настройка бота
async def setup_bot():
    """Инициализация бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return app

# Инициализация приложения
async def init_app():
    """Инициализация aiohttp приложения"""
    bot_app = await setup_bot()
    
    # Установка вебхука
    async with bot_app:
        await bot_app.initialize()
        await bot_app.bot.set_webhook(
            WEBHOOK_URL,
            allowed_updates=["message", "callback_query"]
        )
        logger.info(f"Webhook set to: {WEBHOOK_URL}")
    
    app = web.Application()
    app['bot_app'] = bot_app
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/", handle_health)
    
    return app

# Запуск
if __name__ == "__main__":
    logger.info("🚀 Запуск бота с YandexGPT...")
    try:
        loop = asyncio.get_event_loop()
        app = loop.run_until_complete(init_app())
        web.run_app(app, host="0.0.0.0", port=10000)
    except Exception as e:
        logger.critical(f"Failed to start: {e}")
        exit(1)
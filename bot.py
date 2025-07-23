import os
import json
import httpx
import logging
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

# Конфигурация салона (можно вынести в отдельный JSON)
SALON_INFO = {
    "name": "Right.style89 | Студия восстановления специализирующееся на лакокрасочном покрытии автомобиля",
    "address": "г. Салехард, территория Площадка № 13, с 26",
    "contacts": "https://vk.com/right.style89",
    "working_hours": "10:00-22:00 (без выходных)",
    "services": {
        "Удаление вмятин по технологии PDR": "от 2500₽",
        "Ремонт-реставрация царапин до металла": "от 1800₽",
        "Ремонт-реставрация сколов до металла": "от 5000₽",
        "Ремонт-реставрация кантов": "от 2000₽",
        "Ремонт-реставрация порогов": "от 2500₽",
        "Анти-хром и окрас шильдиков": "от 5000₽",
        "Полировка автомобиля": "от 15000₽"
    }
}

# Системный промпт
SYSTEM_PROMPT = f"""
Ты ассистент салона по детейлингу автомобилей и ты можешь легко проконсультировать клиента по любому вопросу связанному с деятельностью салона или ньюансами детейлинга авто "{SALON_INFO['name']}".

**Контактная информация:**
- Адрес: {SALON_INFO['address']}
- Телефон: {SALON_INFO['contacts']}
- Режим работы: {SALON_INFO['working_hours']}

**Основные услуги и цены:**
{json.dumps(SALON_INFO['services'], indent=2, ensure_ascii=False)}

**Правила общения:**
1. Вежливый и профессиональный тон
2. Не давать не связанных с детейлинг деятельностью советов
3. На вопросы не по теме отвечать: "Этот вопрос лучше уточнить у администратора"
4. На агрессию реагировать спокойно
5. Все цены указывать как ориентировочные
6. Если у пользователя вопрос связанный с детейлингом и схожими темами касающиеся тематике салона, отвечай ему коротко и ясно.

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
        f"Контакты для записи: {SALON_INFO['contacts']}"
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
    data = await request.json()
    logger.debug(f"Webhook data: {data}")
    
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

# Инициализация и запуск
async def setup_application():
    """Настройка приложения"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Настройка вебхука
    await app.initialize()
    await app.bot.set_webhook(
        url=WEBHOOK_URL,
        allowed_updates=["message", "callback_query"]
    )
    
    return app

async def main():
    """Точка входа"""
    global application
    application = await setup_application()
    
    # Настройка aiohttp приложения
    app = web.Application()
    app.router.add_post("/", handle_webhook)
    
    return app

if __name__ == "__main__":
    import asyncio
    app = asyncio.run(main())  # сначала вызываем main()
    web.run_app(app, port=10000)  # потом передаём app в run_app()

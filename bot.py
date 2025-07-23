import os
import httpx
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Переменные окружения
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

# URL для YandexGPT
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

# Функция для запроса к YandexGPT
async def ask_yandex_gpt(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",  # или yandexgpt
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 150
        },
        "messages": [
            {"role": "system", "text": "Ты полезный ассистент для клиентов бьюти-салона или детейлинг-центра."},
            {"role": "user", "text": prompt}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(YANDEX_GPT_URL, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        return data['result']['alternatives'][0]['message']['text'].strip()
    else:
        logging.error(f"YandexGPT error: {response.status_code} - {response.text}")
        return "Произошла ошибка при обращении к нейросети."

# Хендлер /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я нейроассистент бьюти-салона и детейлинг-центра.")

# Хендлер сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logging.info(f"Вопрос: {user_text}")
    reply = await ask_yandex_gpt(user_text)
    logging.info(f"Ответ: {reply}")
    await update.message.reply_text(reply)

# Webhook обработка
async def handle(request):
    data = await request.json()
    logging.info(f"Получен апдейт: {data}")
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

# Основной запуск
async def main():
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)

    app = web.Application()
    app.router.add_post("/", handle)
    return app

if __name__ == "__main__":
    import asyncio
    asyncio.run(web.run_app(main(), port=10000))

import os
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
from yandexgpt import YandexGPT, CompletionRequest

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Переменные окружения
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

# Инициализация клиента YandexGPT
gpt = YandexGPT(api_key=YANDEX_API_KEY)

# Хендлер /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я нейроассистент бьюти-салона и детейлинг-центра.")

# Хендлер обычных сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logging.info(f"Пользователь: {user_text}")

    try:
        request = CompletionRequest(
            model="yandexgpt-lite",  # или "yandexgpt"
            folder_id=YANDEX_FOLDER_ID,
            messages=[
                {"role": "system", "text": "Ты полезный ассистент для клиентов бьюти-салона или детейлинг-центра."},
                {"role": "user", "text": user_text}
            ],
            temperature=0.7,
            max_tokens=150
        )
        response = await gpt.complete(request)
        reply_text = response.choices[0].message.text.strip()
        logging.info(f"Ответ YandexGPT: {reply_text}")

    except Exception as e:
        logging.exception("Ошибка при обращении к YandexGPT")
        reply_text = "Произошла ошибка при обращении к нейросети."

    await update.message.reply_text(reply_text)

# Webhook обработчик
async def handle(request):
    data = await request.json()
    logging.info(f"Получен апдейт: {data}")
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

# Запуск приложения
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

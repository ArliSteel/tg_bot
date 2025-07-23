import os
import openai
from aiohttp import web
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
import logging

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я нейроассистент.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logging.info(f"Запрос к OpenAI: {user_text}")

    # Вызов OpenAI Chat Completion (gpt-3.5-turbo)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Ты полезный ассистент для клиентов бьюти-салона или детейлинг-центра."},
            {"role": "user", "content": user_text}
        ],
        max_tokens=150,
        temperature=0.7,
    )

    answer = response.choices[0].message.content.strip()
    logging.info(f"Ответ OpenAI: {answer}")

    await update.message.reply_text(answer)

async def handle(request):
    data = await request.json()
    logging.info(f"Получен апдейт: {data}")
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

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
    web.run_app(main(), port=10000)

import os
from aiohttp import web
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # ← это URL Render (например, https://your-bot.onrender.com)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я нейроассистент.")

async def handle(request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))

# Устанавливаем webhook
async def setup_webhook():
    await application.bot.set_webhook(url=WEBHOOK_URL)

# Aiohttp сервер
async def main():
    await setup_webhook()
    app = web.Application()
    app.router.add_post("/", handle)
    return app

if __name__ == "__main__":
    web.run_app(main(), port=10000)  # Render ищет PORT в 10000+

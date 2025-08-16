import os
import json
import logging
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

# =======================
# Настройка логов
# =======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =======================
# Переменные окружения
# =======================
REQUIRED_ENV = ["TELEGRAM_TOKEN", "WEBHOOK_URL"]
missing = [var for var in REQUIRED_ENV if not os.getenv(var)]
if missing:
    logger.critical(f"Отсутствуют переменные окружения: {missing}")
    exit(1)

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# =======================
# Обработчики
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает! Отправьте сообщение.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Получено сообщение: {update.message.text}")
    await update.message.reply_text(f"Вы написали: {update.message.text}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=True)

# =======================
# Вебхук
# =======================
async def handle_webhook(request):
    try:
        data = await request.json()
        logger.info(f"Получен апдейт: {json.dumps(data)}")
        app = request.app["bot_app"]
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response(text="ok")
    except Exception as e:
        logger.exception(f"Ошибка вебхука: {e}")
        return web.Response(status=500)

# =======================
# Настройка бота
# =======================
async def setup_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_error_handler(error_handler)
    return app

async def init_app():
    bot_app = await setup_bot()

    # Установка вебхука
    async with bot_app:
        webhook_info = await bot_app.bot.get_webhook_info()
        if webhook_info.url != WEBHOOK_URL:
            logger.info(f"Устанавливаю вебхук: {WEBHOOK_URL}")
            await bot_app.bot.set_webhook(WEBHOOK_URL)

    # aiohttp сервер
    app = web.Application()
    app["bot_app"] = bot_app
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    return app

# =======================
# Точка входа
# =======================
if __name__ == "__main__":
    import asyncio
    from aiohttp import web

    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    web.run_app(app, host="0.0.0.0", port=10000)


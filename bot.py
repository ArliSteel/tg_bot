import os
import json
import logging
from aiohttp import web

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Вебхук - максимально упрощенный
async def handle_webhook(request):
    try:
        # Просто логируем что пришло и возвращаем OK
        data = await request.json()
        logger.info(f"📨 Received: {json.dumps(data, indent=2)}")
        return web.Response(text="OK")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return web.Response(text="OK")  # Всегда возвращаем OK для Telegram

# Health check
async def handle_health(request):
    return web.Response(text="Bot is alive")

# Создаем приложение
app = web.Application()
app.router.add_post("/", handle_webhook)
app.router.add_get("/health", handle_health)
app.router.add_get("/", handle_health)

# Запуск
if __name__ == "__main__":
    logger.info("🚀 Ultra simple bot started!")
    web.run_app(app, host="0.0.0.0", port=10000)
import os
import json
import httpx
import logging
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

# ==================== КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯ ====================

# Настройка логов с более информативным форматом
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка и валидация переменных окружения
def load_config():
    """Загрузка и проверка конфигурации"""
    config = {
        'BOT_TOKEN': os.getenv("TELEGRAM_TOKEN"),
        'WEBHOOK_URL': os.getenv("WEBHOOK_URL"),
        'YANDEX_API_KEY': os.getenv("YANDEX_API_KEY"),
        'YANDEX_FOLDER_ID': os.getenv("YANDEX_FOLDER_ID")
    }
    
    missing_vars = [key for key, value in config.items() if not value]
    if missing_vars:
        logger.critical(f"Отсутствуют переменные окружения: {missing_vars}")
        exit(1)
    
    return config

# Загружаем конфиг
CONFIG = load_config()

# Конфигурация салона (вынесено в отдельный блок)
SALON_CONFIG = {
    "name": "Right Style 89 | Студия детейлинга",
    "address": "г. Салехард, территория Площадка № 13, с. 26",
    "contacts": "+7 (912) 345-67-89",
    "working_hours": "10:00-22:00 (ежедневно)",
    "social_media": {
        "VK": "https://vk.com/right.style89",
        "Instagram": "@right.style89",
        "Telegram": "@rightstyle89"
    },
    "services": {
        "🚗 Удаление вмятин PDR": "от 1000₽",
        "🔧 Ремонт царапин до металла": "от 2500₽",
        "🎯 Локальный ремонт сколов": "от 1000₽",
        "✨ Восстановление кантов и порогов": "от 2800₽",
        "⚫️ Антихром (чернение хрома)": "от 500₽",
        "🎨 Окрас шильдиков и эмблем": "от 800₽",
        "💫 Индивидуальный дизайн": "по договорённости",
        "🔆 Локальная покраска деталей": "от 5000₽",
        "💎 Комплексная полировка кузова": "от 12000₽",
        "💡 Полировка фар и стоп-сигналов": "от 2500₽",
        "🛡️ Керамическое покрытие": "от 15000₽",
        "🧼 Химчистка салона": "от 8000₽"
    },
    "unique_selling_points": [
        "Бесплатная диагностика состояния ЛКП",
        "Гарантия на все виды работ 12 месяцев",
        "Используем профессиональные материалы Ceramic Pro, Koch Chemie",
        "Работаем с премиальными брендами: Mercedes, BMW, Audi, Porsche",
        "Технология Paintless Dent Repair (PDR)",
        "Экологичные материалы без токсичных веществ"
    ]
}

# Константы API
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
MODEL_CONFIG = {
    "temperature": 0.3,
    "max_tokens": 300
}

# Глобальная переменная для бота
bot_app = None

# ==================== YANDEX GPT КЛИЕНТ ====================

class YandexGPTClient:
    """Клиент для работы с Yandex GPT API"""
    
    @staticmethod
    def enhance_professional_terms(text: str) -> str:
        """Улучшение профессиональной терминологии в ответах"""
        term_mapping = {
            "покраска": "нанесение ЛКП",
            "царапина": "нарушение целостности ЛКП",
            "скол": "локальное повреждение ЛКП",
            "полировка": "восстановление глянца ЛКП",
            "покрытие": "защитное керамическое покрытие",
            "чистка": "профессиональная химчистка"
        }
        
        for common, professional in term_mapping.items():
            text = text.replace(common, professional)
        
        return text
    
    @staticmethod
    def create_system_prompt():
        """Создает динамический системный промпт"""
        services_text = "\n".join([f"• {service}: {price}" for service, price in SALON_CONFIG['services'].items()])
        usp_text = "\n".join([f"• {point}" for point in SALON_CONFIG['unique_selling_points']])
        
        return f"""
Ты профессиональный ассистент студии детейлинга "Right Style 89". Ты эксперт в области:
- Восстановления лакокрасочного покрытия (ЛКП)
- Удаления вмятин по технологии PDR
- Керамического покрытия и защитных составов
- Полировки и восстановления оптики
- Антихромирования и чернения деталей
- Химчистки салонов премиум-класса

**КОНТАКТНАЯ ИНФОРМАЦИЯ:**
🏢 Адрес: {SALON_CONFIG['address']}
📞 Телефон: {SALON_CONFIG['contacts']}
🕒 Режим работы: {SALON_CONFIG['working_hours']}
🌐 Соцсети: {', '.join(SALON_CONFIG['social_media'].values())}

**УСЛУГИ И ЦЕНЫ:**
{services_text}

**НАШИ ПРЕИМУЩЕСТВА:**
{usp_text}

**ПРАВИЛА ОБЩЕНИЯ:**
1. 🎯 Отвечай только на вопросы про детейлинг, покраску и смежные темы
2. 💰 Указывай цены как ориентировочные - говори "от X рублей"
3. 📅 На запрос записи предлагай позвонить по телефону для консультации
4. ❌ На вопросы не по теме отвечай: "Этот вопрос лучше обсудить с администратором"
5. ⚠️ Не давай медицинских, юридических или технических советов по ремонту
6. 🔧 При описании работ используй профессиональную терминологию: ЛКП, PDR, керамика, полимеризация
7. 🚗 Упоминай, что работаем с премиальными брендами
8. 🎨 Предлагай комплексные решения при проблемах с покрытием

**ВАЖНО:**
- Всегда сохраняй профессиональный тон эксперта детейлинга
- Не придумывай несуществующие услуги или технологии
- При сложных случаях предлагай бесплатную диагностику
- Упоминай гарантию 12 месяцев на работы
- Подчеркивай использование профессиональных материалов
"""
    
    @staticmethod
    async def generate_response(user_message: str) -> str:
        """Генерация ответа через YandexGPT API"""
        headers = {
            "Authorization": f"Bearer {CONFIG['YANDEX_API_KEY']}",
            "x-folder-id": CONFIG['YANDEX_FOLDER_ID'],
            "Content-Type": "application/json"
        }
        
        # Формирование системного промпта
        system_prompt = YandexGPTClient.create_system_prompt()
        
        payload = {
            "modelUri": f"gpt://{CONFIG['YANDEX_FOLDER_ID']}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": MODEL_CONFIG["temperature"],
                "maxTokens": MODEL_CONFIG["max_tokens"]
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt
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
                result = data['result']['alternatives'][0]['message']['text'].strip()
                return YandexGPTClient.enhance_professional_terms(result)
                
        except httpx.HTTPError as e:
            logger.error(f"Ошибка HTTP при запросе к YandexGPT: {str(e)}")
            return "Извините, произошла ошибка соединения. Пожалуйста, попробуйте позже."
        except Exception as e:
            logger.error(f"Неожиданная ошибка в YandexGPT: {str(e)}")
            return "Извините, произошла техническая ошибка. Пожалуйста, попробуйте позже."

# ==================== TELEGRAM HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        welcome_msg = (
            f"🚗 *Добро пожаловать в {SALON_CONFIG['name']}!* \n\n"
            f"Я ваш персональный ассистент по вопросам детейлинга и восстановления автомобилей. "
            f"Готов ответить на ваши вопросы о наших услугах:\n\n"
            
            f"✨ *Основные направления:*\n"
            f"• Восстановление ЛКП и удаление вмятин\n"
            f"• Керамическое покрытие и защита кузова\n"
            f"• Полировка фар и восстановление оптики\n"
            f"• Антихром и чернение хромированных деталей\n"
            f"• Химчистка салонов премиум-класса\n\n"
            
            f"📞 *Контакты для записи:*\n"
            f"Телефон: {SALON_CONFIG['contacts']}\n"
            f"Адрес: {SALON_CONFIG['address']}\n"
            f"Режим работы: {SALON_CONFIG['working_hours']}\n\n"
            
            f"🔧 *Персональное предложение:*\n"
            f"При записи через Telegram - *бесплатная диагностика* состояния лакокрасочного покрытия!\n\n"
            
            f"Задайте ваш вопрос, и я с радостью помогу! 🛠️"
        )
        
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
        logger.info(f"Отправлено приветственное сообщение пользователю {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике start: {e}")
        await update.message.reply_text("Добро пожаловать! Чем могу помочь?")

async def handle_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /services"""
    services_text = "\n".join([f"• {service}: {price}" for service, price in SALON_CONFIG['services'].items()])
    
    services_msg = (
        "🛠️ *Наши услуги и цены:*\n\n"
        f"{services_text}\n\n"
        "*Примечание:* Цены указаны в рублях и являются ориентировочными. "
        "Точную стоимость можно определить после диагностики автомобиля.\n\n"
        "📞 Запись на диагностику: " + SALON_CONFIG['contacts']
    )
    
    await update.message.reply_text(services_msg, parse_mode='Markdown')
    logger.info(f"Отправлен список услуг пользователю {update.effective_user.id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        user_text = update.message.text
        user_id = update.effective_user.id
        logger.info(f"Получено сообщение от {user_id}: {user_text}")
        
        # Показываем статус "печатает"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Получаем ответ от GPT
        reply = await YandexGPTClient.generate_response(user_text)
        
        # Фильтрация нежелательных фраз
        banned_phrases = ["лечебн", "медицинск", "гарантируем", "100%", "вылеч", "диагноз", "юридическ"]
        if any(phrase in reply.lower() for phrase in banned_phrases):
            reply = "🚫 Этот вопрос требует консультации специалиста. Пожалуйста, обратитесь к администратору по телефону."
        
        # Добавляем профессиональное завершение к ответам
        if not any(phrase in reply.lower() for phrase in ["звоните", "телефон", "контакт", "адрес"]):
            reply += "\n\n📞 Для записи на диагностику звоните: " + SALON_CONFIG['contacts']
        
        # Отправляем ответ
        await update.message.reply_text(reply)
        logger.info(f"Отправлен ответ пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        error_msg = (
            "⚠️ Произошла ошибка при обработке вашего запроса.\n"
            "Пожалуйста, попробуйте задать вопрос еще раз или позвоните нам напрямую: "
            f"{SALON_CONFIG['contacts']}"
        )
        await update.message.reply_text(error_msg)

# ==================== WEBHOOK HANDLERS ====================

async def handle_webhook(request):
    """Обработчик вебхука от Telegram"""
    try:
        data = await request.json()
        update_id = data.get('update_id', 'unknown')
        logger.info(f"Получен вебхук #{update_id}")
        
        if bot_app is None:
            logger.error("Бот не инициализирован при обработке вебхука")
            return web.Response(text="Bot not initialized", status=500)
        
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        
        return web.Response(text="OK")
        
    except json.JSONDecodeError:
        logger.error("Неверный JSON в вебхуке")
        return web.Response(text="Invalid JSON", status=400)
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return web.Response(text="OK")  # Всегда возвращаем OK для Telegram

async def handle_health(request):
    """Проверка здоровья сервиса"""
    return web.Response(text="✅ Bot is alive and healthy")

# ==================== ИНИЦИАЛИЗАЦИЯ И ЗАПУСК ====================

async def initialize_bot():
    """Инициализация бота один раз при старте"""
    global bot_app
    
    try:
        logger.info("Инициализация бота...")
        bot_app = Application.builder().token(CONFIG['BOT_TOKEN']).build()
        
        # Регистрация обработчиков
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("services", handle_services))
        bot_app.add_handler(CommandHandler("uslugi", handle_services))  # Русская версия
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Инициализация и установка вебхука
        await bot_app.initialize()
        await bot_app.bot.set_webhook(
            CONFIG['WEBHOOK_URL'],
            allowed_updates=["message", "callback_query"]
        )
        
        logger.info(f"Вебхук установлен: {CONFIG['WEBHOOK_URL']}")
        logger.info("Бот успешно инициализирован")
        
    except Exception as e:
        logger.critical(f"Ошибка инициализации бота: {e}")
        raise

async def init_app():
    """Инициализация aiohttp приложения"""
    await initialize_bot()
    
    app = web.Application()
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/", handle_health)
    
    return app

def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск бота с YandexGPT...")
    
    try:
        # Настройка event loop для совместимости
        if os.name == 'nt':  # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        app = loop.run_until_complete(init_app())
        web.run_app(app, host="0.0.0.0", port=10000)
        
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
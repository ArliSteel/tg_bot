# ==================== КОНФИГУРАЦИЯ И ИНИЦИАЛИЗАЦИЯя ====================

import os
import json
import httpx
import logging
import asyncio
import random
import time
import re
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from security import security, secure_handler

# Определяем окружение
environment = os.getenv('ENVIRONMENT', 'staging')
print(f"🚀 Запуск в окружении: {environment.upper()}")

# Настройка логов с указанием окружения
logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - {environment.upper()} - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка конфигурации
def load_config():
    """Загрузка и проверка конфигурации"""
    config = {
        'BOT_TOKEN': os.getenv("TELEGRAM_TOKEN"),
        'WEBHOOK_URL': os.getenv("WEBHOOK_URL"),
        'WEBHOOK_SECRET': os.getenv("WEBHOOK_SECRET", "default_secret_token"),
        'YANDEX_API_KEY': os.getenv("YANDEX_API_KEY"),
        'YANDEX_FOLDER_ID': os.getenv("YANDEX_FOLDER_ID"),
        'MAX_REQUESTS_PER_MINUTE': int(os.getenv("MAX_REQUESTS_PER_MINUTE", "200")),
        'MAX_TEXT_LENGTH': int(os.getenv("MAX_TEXT_LENGTH", "4000")),
        'BLOCK_DURATION': int(os.getenv("BLOCK_DURATION", "3600")),
        'WARNING_THRESHOLD': int(os.getenv("WARNING_THRESHOLD", "5")),
        'ENVIRONMENT': environment
    }
    
    # Проверка обязательных переменных
    required_vars = ['BOT_TOKEN', 'YANDEX_API_KEY', 'YANDEX_FOLDER_ID']
    missing_vars = [key for key in required_vars if not config[key]]
    
    if missing_vars:
        logger.critical(f"Отсутствуют обязательные переменные окружения: {missing_vars}")
        exit(1)
    
    # Маскируем чувствительные данные в логах
    masked_config = config.copy()
    for key in ['BOT_TOKEN', 'YANDEX_API_KEY', 'WEBHOOK_SECRET']:
        if masked_config[key]:
            masked_config[key] = masked_config[key][:10] + '...'
    
    logger.info(f"Загружена конфигурация: {masked_config}")
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
        "Telegram": "@Rightstyle89"
    },
    "services": {
        "🚗 Удаление вмятин PDR": "от 1000₽",
        "🔧 Ремонт царапин до металла": "от 2500₽",
        "🎯 Локальный ремонт сколов": "от 1000₽",
        "✨ Восстановление кантов и порогов": "от 2800₽",
        "⚫️ Антихром (чернение хрома):": "от 500₽",
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

# FAQ карточки
FAQ_CARDS = {
    "pdr_technology": {
        "question": "🤔 Что такое технология PDR?",
        "answer": "🔧 *PDR (Paintless Dent Repair)* — это современная технология удаления вмятин без покраски.\n\n*Преимущества:*\n• Сохранение заводского ЛКП\n• Быстрое выполнение (от 30 минут)\n• Гарантия 12 месяцев\n• Экономия до 70% compared с традиционным ремонтом"
    },
    "ceramic_coating": {
        "question": "💎 Что дает керамическое покрытие?",
        "answer": "✨ *Керамическое покрытие* — это нано-защита для вашего авто:\n\n*Преимущества:*\n• Защита от УФ-лучей и выцветания\n• Стойкость к химическим воздействиям\n• Гидрофобный эффект (вода скатывается)\n• Легкость в мойке\n• Блеск как у нового авто\n• Гарантия до 5 лет"
    },
    "polishing_types": {
        "question": "🔆 Какие виды полировки бывают?",
        "answer": "📋 *Мы предлагаем 3 вида полировки:*\n\n1. *Восстановительная* — удаление царапин и дефектов\n2. *Защитная* — нанесение восков/синтетики\n3. *Керамическая* — долговременная защита\n\n💡 *Бесплатная диагностика* определит нужный тип для вашего авто!"
    },
    "paint_repair": {
        "question": "🎨 Как ремонтируют сколы и царапины?",
        "answer": "🛠️ *Процесс ремонта ЛКП:*\n\n1. Очистка и обезжиривание\n2. Подбор цвета по VIN-коду\n3. Локальное нанесение краски\n4. Сушение ИК-лампой\n5. Полировка до идеального глянца\n\n⚡ *Результат:* неотличимо от заводского покрытия!"
    }
}

# Константы API
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
MODEL_CONFIG = {
    "temperature": 0.3,
    "max_tokens": 300
}

# Настройки симуляции человека
HUMAN_SIMULATION = {
    "min_typing_delay": 2,  # минимальная задержка перед ответом (сек)
    "max_typing_delay": 8,  # максимальная задержка перед ответом (сек)
    "chars_per_second": 10,  # скорость "печатания" (символов в секунду)
    "typing_variation": 0.3,  # вариативность скорости печатания (30%)
    "error_probability": 0.05,  # вероятность "ошибки" и перепечатывания (5%)
}

# Глобальная переменная для бота
bot_app = None

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def escape_markdown_text(text: str) -> str:
    """Экранирует специальные символы MarkdownV2"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def log_user_action(user_id, action, details):
    """Логирует действия пользователя"""
    logger.info(f"User {user_id}: {action} - {details}")

def contains_banned_content(text):
    """Проверяет, содержит ли текст запрещенный контент"""
    text_lower = text.lower()
    medical_phrases = ["лечебн", "медицинск", "вылеч"]
    legal_phrases = ["юридическ", "адвокат", "суд"]

    # Проверяем медицинские фразы в неподходящем контексте
    if any(phrase in text_lower for phrase in medical_phrases) and "авто" not in text_lower:
        return True
        
    # Проверяем юридические фразы
    if any(phrase in text_lower for phrase in legal_phrases):
        return True
        
    return False

def check_response_safety(text):
    """Проверяет ответ LLM на утечку конфиденциальной информации"""
    if not text:
        return True
        
    # Проверяем на утечку потенциальных секретов
    secret_patterns = [
        r'[A-Za-z0-9]{32,}',  # Длинные строки, похожие на хэши/токены
        r'password.*:.+',      # Упоминание паролей
        r'token.*:.+',         # Упоминание токенов
        r'api[_-]?key.*:.+',   # Упоминание API-ключей
        r'secret.*:.+',        # Упоминание секретов
    ]
    
    for pattern in secret_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Обнаружена потенциальная утечка в ответе LLM: {pattern}")
            return False
            
    # Проверяем на наличие конфиденциальных данных из конфига
    sensitive_data = [
        CONFIG['BOT_TOKEN'],
        CONFIG['YANDEX_API_KEY'],
        CONFIG['WEBHOOK_SECRET'],
        SALON_CONFIG['contacts'],
    ]
    
    for data in sensitive_data:
        if data and data in text:
            logger.warning("Обнаружена утечка конфиденциальных данных в ответе LLM")
            return False
            
    return True

# ==================== YANDEX GPT КЛИЕНТ ====================

class YandexGPTClient:
    """Клиент для работы с Yandex GPT API"""
    
    @staticmethod
    def enhance_professional_terms(text: str) -> str:
        """Улучшение профессиональной терминологии в ответах"""
        term_mapping = {
            "покраска": "нанесение ЛКП",
            "царапина": "нарушение целостности ЛКП",
            "скол": " локальное повреждение ЛКП",
            "полировка": "восстановление глянца ЛКП",
            "покрытие": "защитное керамическое покрытие",
            "чистка": "профессиональная химчистка"
        }
        
        for common, professional in term_mapping.items():
            text = text.replace(common, professional)
        
        return text
    
    @staticmethod
    def format_with_markdown(text: str) -> str:
        """Преобразует текст в Markdown-формат для лучшего отображения"""
        # Сначала экранируем весь текст
        text = escape_markdown_text(text)
        
        # Затем добавляем форматирование
        text = re.sub(r'(\d+\.\s+)([^:\n]+:)', r'\1**\2**', text)
        text = re.sub(r'(\d+\.\s+)([^\n]+)', r'\1**\2**', text)
        
        # Добавляем жирный шрифт к подзаголовкам
        text = re.sub(r'([А-Яа-яA-Za-z]+:)', r'**\1**', text)
        
        # Улучшаем форматирование списков
        text = re.sub(r'^(\s*[-•*])\s+', r'• ', text, flags=re.MULTILINE)
        
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
1. Отвечай как живой человек, а не как бot
2. Используй неформальный, но профессиональный стиль общения
3. Можешь использовать разговорные выражения, соответствующие стилю общения автосервиса
4. Иногда можешь делать небольшие опечатки для естественности
5. Отвечай так, как будто ты настоящий специалист по детейлингу
6. Всегда используй Markdown-разметку для форматирования ответов:
   - Заголовки выделяй **жирным текстом**
   - Важные моменты выделяй *курсивом**
   - Используй эмодзи для визуального оформления 🚗✨🔧
   - Списки оформляй с помощью цифр или пунктов

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
                
                # Улучшаем профессиональные термины и добавляем Markdown-разметку
                result = YandexGPTClient.enhance_professional_terms(result)
                result = YandexGPTClient.format_with_markdown(result)
                
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Ошибка HTTP при запросе к YandexGPT: {str(e)}")
            return "Извините, произошла ошибка соединения. Пожалуйста, попробуйте позже."
        except Exception as e:
            logger.error(f"Неожиданная ошибка в YandexGPT: {str(e)}")
            return "Извините, произошла техническая ошибка. Пожалуйста, попробуйте позже."

# ==================== СИМУЛЯЦИЯ ЧЕЛОВЕЧЕСКОГО ПОВЕДЕНИЯ ====================

async def simulate_typing(chat_id, context, text_length):
    """Симуляция печатания человека с учетом длины текста"""
    # Расчет времени печатания на основе длины текста
    base_typing_time = text_length / HUMAN_SIMULATION['chars_per_second']
    
    # Добавление вариативности
    variation = base_typing_time * HUMAN_SIMULATION['typing_variation']
    typing_time = base_typing_time + random.uniform(-variation, variation)
    
    # Ограничение минимального и максимального времени
    typing_time = max(HUMAN_SIMULATION['min_typing_delay'], 
                     min(typing_time, HUMAN_SIMULATION['max_typing_delay']))
    
    # Симуляция печатания с обновлением статуса
    start_time = time.time()
    while time.time() - start_time < typing_time:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(4.5)  # Обновляем статус каждые 4.5 секунд (Telegram скрывает через 5)
    
    return typing_time

async def simulate_human_typing_mistakes(text):
    """Добавление случайных опечаток для естественности"""
    if random.random() > HUMAN_SIMULATION['error_probability']:
        return text
    
    # Случайные опечатки
    mistakes = [
        (("о", "а"), 0.3),  # замена о на а и наоборот
        (("е", "и"), 0.2),  # замена е на и и наоборот
        (("с", 'ш'), 0.1),  # замена с на ш и наоборот
        (("."), 0.05),      # пропуск точки
        ((","), 0.05),      # пропуск запятой
    ]
    
    words = text.split()
    if len(words) > 3:
        # Выбираем случайное слово для ошибки (не первое и не последнее)
        word_idx = random.randint(1, len(words) - 2)
        word = words[word_idx]
        
        for chars, prob in mistakes:
            if random.random() < prob and any(c in word for c in chars):
                if len(chars) == 1:
                    # Пропуск символа
                    if chars[0] in word:
                        words[word_idx] = word.replace(chars[0], "", 1)
                        break
                else:
                    # Замена символа
                    from_char, to_char = chars
                    if from_char in word:
                        words[word_idx] = word.replace(from_char, to_char, 1)
                        break
                break
    
    return " ".join(words)

async def simulate_typing_with_errors(chat_id, context, text):
    """Полная симуляция печатания с возможными ошибками и исправлениями"""
    # Первая попытка "печатания"
    typing_time = await simulate_typing(chat_id, context, len(text))
    
    # Случайная "ошибка" и перепечатывание
    if random.random() < HUMAN_SIMULATION['error_probability']:
        await asyncio.sleep(0.5)
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(1.5)
        
        # "Исправление" ошибки
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(1.0)
        
        typing_time += 3.0  # Добавляем время на исправление
    
    return typing_time

# ==================== TELEGRAM HANDLERS ====================

@secure_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        user_id = update.effective_user.id
        log_user_action(user_id, "start", "User initiated /start command")
        
        # Симуляция печатания
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await asyncio.sleep(random.uniform(1.5, 3.0))
        
        # Создаем приветственное сообщение с правильным экранированием
        welcome_msg = escape_markdown_text(
            "Привет! 👋\n\n"
            f"Я ассистент студии детейлинга «{SALON_CONFIG['name']}». Чем могу помочь?\n\n"
            "Мы занимаемся восстановлением лакокрасочного покрытия, удалением вмятин по технологии PDR, "
            "керамическим покрытием, полировкой оптики и многим другим.\n\n"
            "Если у вас есть вопросы по услугам или хотите записаться на бесплатную диагностику — "
            "я с радостью помогу! 😉\n\n"
            f"📞 Для записи на диагностику звоните: {SALON_CONFIG['contacts']}"
        )
        
        # Создаем клавиатуру для главного меню
        keyboard = [
            [InlineKeyboardButton("❓ Частые вопросы", callback_data="show_faq")],
            [InlineKeyboardButton("🛠️ Наши услуги", callback_data="show_services")],
            [InlineKeyboardButton("📞 Связаться с нами", callback_data="show_contacts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_msg, parse_mode='MarkdownV2', reply_markup=reply_markup)
        logger.info(f"Отправлено приветственное сообщение пользователю {user_id}")
        log_user_action(user_id, "start_success", "Welcome message sent")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике start: {e}")
        error_msg = escape_markdown_text("Добро пожаловать! Чем могу помочь?")
        await update.message.reply_text(error_msg, parse_mode='MarkdownV2')
        log_user_action(update.effective_user.id, "start_error", f"Error: {str(e)}")

@secure_handler
async def handle_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /services"""
    try:
        user_id = update.effective_user.id
        log_user_action(user_id, "services", "User requested services list")
        
        # Симуляция печатания
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await asyncio.sleep(random.uniform(2.0, 4.0))
        
        services_text = "\n".join([f"• {service}: {price}" for service, price in SALON_CONFIG['services'].items()])
        
        services_msg = escape_markdown_text(
            "🛠️ Наши услуги и цены:\n\n"
            f"{services_text}\n\n"
            "Примечание: Цены указаны в рублях и являются ориентировочными. "
            "Точную стоимость можно определить после диагностики автомобиля.\n\n"
            f"📞 Запись на диагностику: {SALON_CONFIG['contacts']}"
        )
        
        # Добавляем кнопку возврата
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(services_msg, parse_mode='MarkdownV2', reply_markup=reply_markup)
        logger.info(f"Отправлен список услуг пользователю {user_id}")
        log_user_action(user_id, "services_success", "Services list sent")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике services: {e}")
        error_msg = escape_markdown_text("Извините, произошла ошибка при загрузке услуг.")
        await update.message.reply_text(error_msg, parse_mode='MarkdownV2')
        log_user_action(update.effective_user.id, "services_error", f"Error: {str(e)}")

@secure_handler
async def handle_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /faq - показывает меню с FAQ"""
    try:
        user_id = update.effective_user.id
        log_user_action(user_id, "faq", "User requested FAQ menu")
        
        # Создаем клавиатуру с кнопками FAQ
        keyboard = []
        for key, data in FAQ_CARDS.items():
            keyboard.append([InlineKeyboardButton(data["question"], callback_data=f"faq_{key}")])
        
        # Добавляем кнопку "Назад" в главное меню
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        faq_text = escape_markdown_text(
            "❓ Выберите интересующий вопрос:\n\n"
            "Здесь собраны самые популярные вопросы о наших услугах. "
            "Если не найдете ответ — просто напишите свой вопрос!"
        )
        
        await update.message.reply_text(
            faq_text,
            parse_mode='MarkdownV2',
            reply_markup=reply_markup
        )
        logger.info(f"Показано меню FAQ пользователю {user_id}")
        log_user_action(user_id, "faq_success", "FAQ menu shown")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике FAQ: {e}")
        error_msg = escape_markdown_text("Извините, произошла ошибка при загрузке меню.")
        await update.message.reply_text(error_msg, parse_mode='MarkdownV2')
        log_user_action(update.effective_user.id, "faq_error", f"Error: {str(e)}")

@secure_handler
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик медиа-файлов"""
    try:
        user_id = update.effective_user.id
        log_user_action(user_id, "media", "User sent media file")
        
        error_msg = escape_markdown_text(
            "📎 Я обрабатываю только текстовые сообщения. "
            "Опишите вашу проблему текстом, и я с радостью помогу!"
        )
        await update.message.reply_text(error_msg, parse_mode='MarkdownV2')
        logger.info(f"Получен медиа-файл от пользователя {user_id}")
        log_user_action(user_id, "media_response", "Media response sent")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике медиа: {e}")
        log_user_action(update.effective_user.id, "media_error", f"Error: {str(e)}")

@secure_handler
async def handle_faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки FAQ"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    try:
        if callback_data.startswith("faq_"):
            # Показываем ответ на вопрос
            faq_key = callback_data[4:]  # Убираем префикс "faq_"
            log_user_action(user_id, "faq_selected", f"Selected FAQ: {faq_key}")
            
            if faq_key in FAQ_CARDS:
                answer = FAQ_CARDS[faq_key]["answer"]
                
                # Создаем клавиатуру для возврата
                keyboard = [[InlineKeyboardButton("⬅️ Назад к вопросам", callback_data="back_to_faq")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                answer_text = escape_markdown_text(f"{answer}\n\nЕсть дополнительные вопросы? Звоните: {SALON_CONFIG['contacts']}")
                
                await query.edit_message_text(
                    text=answer_text,
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
                logger.info(f"Показан ответ на вопрос {faq_key} пользователю {user_id}")
                log_user_action(user_id, "faq_answer_shown", f"FAQ answer shown: {faq_key}")
        
        elif callback_data == "back_to_faq":
            # Возвращаемся к меню FAQ
            log_user_action(user_id, "faq_back", "Returned to FAQ menu")
            
            keyboard = []
            for key, data in FAQ_CARDS.items():
                keyboard.append([InlineKeyboardButton(data["question"], callback_data=f"faq_{key}")])
            
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            faq_text = escape_markdown_text(
                "❓ Выберите интересующий вопрос:\n\n"
                "Здесь собраны самые популярные вопросы о наших услугах. "
                "Если не найдете ответ — просто напишите свой вопрос!"
            )
            
            await query.edit_message_text(
                faq_text,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )
            
        elif callback_data == "back_to_main":
            # Возвращаемся к главному меню (стартовому сообщению)
            log_user_action(user_id, "main_menu_back", "Returned to main menu")
            
            welcome_msg = escape_markdown_text(
                "Привет! 👋\n\n"
                f"Я ассистент студии детейлинга «{SALON_CONFIG['name']}». Чем могу помочь?\n\n"
                "Мы занимаемся восстановлением лакокрасочного покрытия, удалением вмятин по технологии PDR, "
                "керамическим покрытием, полировкой оптики и многим другим.\n\n"
                "Если у вас есть вопросы по услугам или хотите записаться на бесплатную диагностику — "
                "я с радостью помогу! 😉\n\n"
                f"📞 Для записи на диагностику звоните: {SALON_CONFIG['contacts']}"
            )
            
            # Создаем клавиатуру для главного меню
            keyboard = [
                [InlineKeyboardButton("❓ Частые вопросы", callback_data="show_faq")],
                [InlineKeyboardButton("🛠️ Наши услуги", callback_data="show_services")],
                [InlineKeyboardButton("📞 Связаться с нами", callback_data="show_contacts")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                welcome_msg,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки callback: {e}")
        error_msg = escape_markdown_text("⚠️ Произошла ошибка. Пожалуйста, попробуйте еще раз.")
        await query.edit_message_text(error_msg, parse_mode='MarkdownV2')
        log_user_action(user_id, "callback_error", f"Error: {str(e)}")

@secure_handler
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок главного меню"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    try:
        if query.data == "show_faq":
            log_user_action(user_id, "main_menu", "Selected FAQ from main menu")
            # Показываем меню FAQ
            keyboard = []
            for key, data in FAQ_CARDS.items():
                keyboard.append([InlineKeyboardButton(data["question"], callback_data=f"faq_{key}")])
            
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            faq_text = escape_markdown_text(
                "❓ Выберите интересующий вопрос:\n\n"
                "Здесь собраны самые популярные вопросы о наших услугах. "
                "Если не найдете ответ — просто напишите свой вопрос!"
            )
            
            await query.edit_message_text(
                faq_text,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )
            
        elif query.data == "show_services":
            log_user_action(user_id, "main_menu", "Selected Services from main menu")
            # Показываем услуги
            services_text = "\n".join([f"• {service}: {price}" for service, price in SALON_CONFIG['services'].items()])
            
            services_msg = escape_markdown_text(
                "🛠️ Наши услуги и цены:\n\n"
                f"{services_text}\n\n"
                "Примечание: Цены указаны в рублях и являются ориентировочными. "
                "Точную стоимость можно определить после диагностики автомобиля.\n\n"
                f"📞 Запись на диагностику: {SALON_CONFIG['contacts']}"
            )
            
            # Добавляем кнопку возврата
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(services_msg, parse_mode='MarkdownV2', reply_markup=reply_markup)
            
        elif query.data == "show_contacts":
            log_user_action(user_id, "main_menu", "Selected Contacts from main menu")
            # Показываем контакты
            contacts_msg = escape_markdown_text(
                "📞 Наши контакты:\n\n"
                f"Телефон: {SALON_CONFIG['contacts']}\n"
                f"Адрес: {SALON_CONFIG['address']}\n"
                f"Режим работы: {SALON_CONFIG['working_hours']}\n\n"
                f"🌐 Соцсети:\n"
                f"VK: {SALON_CONFIG['social_media']['VK']}\n"
                f"Instagram: {SALON_CONFIG['social_media']['Instagram']}\n"
                f"Telegram: {SALON_CONFIG['social_media']['Telegram']}\n\n"
                "🚗 Приезжайте к нам на бесплатную диагностику!"
            )
            
            # Добавляем кнопку возврата
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(contacts_msg, parse_mode='MarkdownV2', reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Ошибка обработки главного меню: {e}")
        error_msg = escape_markdown_text("⚠️ Произошла ошибка. Пожалуйста, попробуйте еще раз.")
        await query.edit_message_text(error_msg, parse_mode='MarkdownV2')
        log_user_action(user_id, "main_menu_error", f"Error: {str(e)}")

@secure_handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        # Проверяем, не является ли сообщение командой меню
        user_text = update.message.text.lower()
        if user_text in ['меню', 'start', 'начать', 'faq', 'вопросы']:
            await start(update, context)
            return
            
        # Используем безопасный текст из контекста (после обработки secure_handler)
        user_text = context.safe_text
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Логируем только факт получения сообщения без полного текста
        logger.info(f"Получено сообщение от {user_id}, длина: {len(user_text)} символов")
        log_user_action(user_id, "message_received", f"Message length: {len(user_text)} chars")
        
        # Показываем статус "печатает"
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # Получаем ответ от GPT
        reply = await YandexGPTClient.generate_response(user_text)
        
        # Проверяем безопасность ответа
        if not check_response_safety(reply):
            logger.warning(f"Ответ LLM содержит потенциально опасный контент: {reply[:100]}...")
            reply = "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте другой вопрос."
            log_user_action(user_id, "response_safety_check", "Failed safety check")
        
        # Ограничиваем длину ответа
        if len(reply) > CONFIG['MAX_TEXT_LENGTH']:
            reply = reply[:CONFIG['MAX_TEXT_LENGTH']] + "..."
        
        # Симуляция человеческого печатания
        typing_time = await simulate_typing_with_errors(chat_id, context, reply)
        logger.info(f"Симуляция печатания заняла {typing_time:.2f} секунд")
        
        # Добавляем случайные опечатки для естественности
        reply = await simulate_human_typing_mistakes(reply)
        
        # Фильтрация нежелательных фраз
        if contains_banned_content(reply):
            reply = "🚫 Этот вопрос требует консультации специалиста. Пожалуйста, обратитесь к администратору по телефону."
            log_user_action(user_id, "banned_content", "Response contained banned content")
        
        # Добавляем профессиональное завершение к ответам
        if not any(phrase in reply.lower() for phrase in ["звоните", "телефон", "контакт", "адрес"]):
            reply += f"\n\n📞 Для записи на диагностику звоните: {escape_markdown_text(SALON_CONFIG['contacts'])}"
        
        # Отправляем ответ с MarkdownV2
        await update.message.reply_text(reply, parse_mode='MarkdownV2')
        logger.info(f"Отправлен ответ пользователю {user_id}, длина: {len(reply)} символов")
        log_user_action(user_id, "response_sent", f"Response length: {len(reply)} chars")
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        # Короткая задержка перед отправкой ошибки
        await asyncio.sleep(1.5)
        error_msg = (
            "⚠️ Произошла ошибка при обработке вашего запроса.\n"
            "Пожалуйста, попробуйте задать вопрос еще раз или позвоните нам напрямую: "
            f"{SALON_CONFIG['contacts']}"
        )
        # Экранируем сообщение об ошибке
        escaped_error_msg = escape_markdown_text(error_msg)
        await update.message.reply_text(escaped_error_msg, parse_mode='MarkdownV2')
        log_user_action(update.effective_user.id, "message_error", f"Error: {str(e)}")

# ==================== WEBHOOK HANDLERS ====================

async def handle_webhook(request):
    """Обработчик вебхука от Telegram с проверкой секретного токена"""
    try:
        # Проверка секретного токена
        expected_token = CONFIG['WEBHOOK_SECRET']
        received_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        
        if expected_token != received_token:
            logger.warning(f"Invalid webhook secret token: {received_token}")
            return web.Response(text="Invalid token", status=403)
        
        data = await request.json()
        update_id = data.get('update_id', 'unknown')
        logger.info(f"Получен вебхук #{update_id}")
        
        # Проверка безопасности на уровне вебхука
        if not security.check_global_limit(max_requests=CONFIG['MAX_REQUESTS_PER_MINUTE'], period=60):
            return web.Response(text="Rate limit exceeded", status=429)
        
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
        bot_app.add_handler(CommandHandler("faq", handle_faq))  # Добавляем команду /faq
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Обработчик медиа-файлов
        bot_app.add_handler(MessageHandler(
            filters.AUDIO | filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.VOICE, 
            handle_media
        ))
        
        # Обработчики callback-запросов
        bot_app.add_handler(CallbackQueryHandler(handle_faq_callback, pattern="^faq_"))
        bot_app.add_handler(CallbackQueryHandler(handle_faq_callback, pattern="^back_to_"))
        bot_app.add_handler(CallbackQueryHandler(handle_main_menu, pattern="^show_"))
        
        # Инициализация и установка вебхука с секретным токеном
        await bot_app.initialize()
        await bot_app.bot.set_webhook(
            CONFIG['WEBHOOK_URL'],
            allowed_updates=["message", "callback_query"],
            secret_token=CONFIG['WEBHOOK_SECRET']
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
import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from bot.services.security import secure_handler
from bot.utils.formatting import escape_markdown_text
from bot.models.config import SALON_CONFIG

logger = logging.getLogger(__name__)

@secure_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        user_id = update.effective_user.id
        logger.info(f"User {user_id}: start - User initiated /start command")
        
        # Симуляция печатания
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await asyncio.sleep(random.uniform(1.5, 3.0))
        
        # Создаем приветственное сообщение
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
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике start: {e}")
        error_msg = escape_markdown_text("Добро пожаловать! Чем могу помочь?")
        await update.message.reply_text(error_msg, parse_mode='MarkdownV2')

@secure_handler
async def handle_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /services"""
    try:
        user_id = update.effective_user.id
        logger.info(f"User {user_id}: services - User requested services list")
        
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
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике services: {e}")
        error_msg = escape_markdown_text("Извините, произошла ошибка при загрузке услуг.")
        await update.message.reply_text(error_msg, parse_mode='MarkdownV2')

@secure_handler
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок главного меню"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    try:
        if query.data == "show_faq":
            logger.info(f"User {user_id}: main_menu - Selected FAQ from main menu")
            # Перенаправляем в обработчик FAQ
            from bot.handlers.faq import handle_faq
            await handle_faq(update, context)
            
        elif query.data == "show_services":
            logger.info(f"User {user_id}: main_menu - Selected Services from main menu")
            # Перенаправляем в обработчик услуг
            await handle_services(update, context)
            
        elif query.data == "show_contacts":
            logger.info(f"User {user_id}: main_menu - Selected Contacts from main menu")
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

def register_base_handlers(application):
    """Регистрация обработчиков базовых команд"""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("services", handle_services))
    application.add_handler(CommandHandler("uslugi", handle_services))  # Русская версия
    application.add_handler(CallbackQueryHandler(handle_main_menu, pattern="^show_"))
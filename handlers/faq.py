import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from bot.services.security import secure_handler
from bot.utils.formatting import escape_markdown_text
from bot.models.config import SALON_CONFIG, FAQ_CARDS

logger = logging.getLogger(__name__)

@secure_handler
async def handle_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /faq - показывает меню с FAQ"""
    try:
        user_id = update.effective_user.id
        logger.info(f"User {user_id}: faq - User requested FAQ menu")
        
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
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике FAQ: {e}")
        error_msg = escape_markdown_text("Извините, произошла ошибка при загрузке меню.")
        await update.message.reply_text(error_msg, parse_mode='MarkdownV2')

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
            logger.info(f"User {user_id}: faq_selected - Selected FAQ: {faq_key}")
            
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
        
        elif callback_data == "back_to_faq":
            # Возвращаемся к меню FAQ
            logger.info(f"User {user_id}: faq_back - Returned to FAQ menu")
            
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
            logger.info(f"User {user_id}: main_menu_back - Returned to main menu")
            
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

def register_faq_handlers(application):
    """Регистрация обработчиков FAQ"""
    application.add_handler(CommandHandler("faq", handle_faq))
    application.add_handler(CallbackQueryHandler(handle_faq_callback, pattern="^faq_"))
    application.add_handler(CallbackQueryHandler(handle_faq_callback, pattern="^back_to_"))
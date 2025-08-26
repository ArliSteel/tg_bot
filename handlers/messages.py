import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.models.config import SALON_CONFIG
from bot.services.security import secure_handler
from bot.services.state_manager import user_state
from bot.utils.formatting import escape_markdown_text

logger = logging.getLogger(__name__)

@secure_handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        # Пропускаем команды меню
        user_text = update.message.text.lower()
        if user_text in ['меню', 'start', 'начать', 'faq', 'вопросы']:
            from bot.handlers.base import start
            await start(update, context)
            return
            
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Добавляем сообщение в очередь и обрабатываем
        await user_state.add_and_process_message(user_id, chat_id, context, context.safe_text)
        
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

@secure_handler
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик медиа-файлов"""
    try:
        user_id = update.effective_user.id
        logger.info(f"User {user_id}: media - User sent media file")
        
        error_msg = escape_markdown_text(
            "📎 Я обрабатываю только текстовые сообщения. "
            "Опишите вашу проблему текстом, и я с радостью помогу!"
        )
        await update.message.reply_text(error_msg, parse_mode='MarkdownV2')
        logger.info(f"Получен медиа-файл от пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике медиа: {e}")

def register_message_handlers(application):
    """Регистрация обработчиков сообщений"""
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(
        filters.AUDIO | filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.VOICE, 
        handle_media
    ))
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from models.config import SALON_CONFIG
from services.security import secure_handler
from services.state_manager import user_state
from services.database import log_user_message  # 🔥 НОВЫЙ ИМПОРТ
from utils.formatting import escape_markdown_text

logger = logging.getLogger(__name__)

@secure_handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        # 🔥 НОВОЕ: Логируем сообщение пользователя в базу данных
        user = update.effective_user
        chat = update.effective_chat
        user_text = update.message.text
        
        # Логируем в фоне, не блокируя основной поток
        asyncio.create_task(
            log_user_message(
                user_id=user.id,
                username=user.username,
                chat_id=chat.id,
                message_text=user_text[:1000]  # Ограничиваем длину для безопасности
            )
        )
        
        # Пропускаем команды меню
        user_text_lower = user_text.lower()
        if user_text_lower in ['меню', 'start', 'начать', 'faq', 'вопросы']:
            from handlers.base import start
            await start(update, context)
            return
            
        user_id = user.id
        chat_id = chat.id
        
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
        
        # 🔥 НОВОЕ: Логируем медиа-сообщение
        user = update.effective_user
        chat = update.effective_chat
        asyncio.create_task(
            log_user_message(
                user_id=user.id,
                username=user.username,
                chat_id=chat.id,
                message_text="[MEDIA_FILE]"
            )
        )
        
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
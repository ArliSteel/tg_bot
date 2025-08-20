# security.py
import time
import html
import re
import logging
from datetime import datetime
from collections import defaultdict
from functools import wraps

# Добавляем необходимые импорты для telegram бота
from telegram import Update
from telegram.ext import ContextTypes

# Настройка логгера для модуля безопасности
logger = logging.getLogger(__name__)

class SecuritySystem:
    def __init__(self):
        self.user_activity = defaultdict(list)
        self.global_activity = []
        self.blocked_users = set()
        self.suspicious_patterns = [
            r"<script.*?>", r"javascript:", r"onload=", r"onerror=",
            r"DROP TABLE", r"UNION SELECT", r"INSERT INTO", r"DELETE FROM",
            r"\.\./", r"\.\.\\", r"eval\(", r"exec\(", r"alert\(",
            r"window\.location", r"document\.cookie", r"localStorage",
            r"process\.env", r"require\(", r"fs\.", r"child_process",
            r"\.env", r"config\.", r"password", r"token", r"secret",
            r"bash.*-i", r"curl.*bash", r"wget.*bash"  # Добавлены паттерны для reverse shell
        ]
    
    def check_rate_limit(self, user_id, max_requests=5, period=60):
        """Проверка ограничения частоты запросов"""
        current_time = time.time()
        
        # Очистка старых запросов
        self.user_activity[user_id] = [
            t for t in self.user_activity[user_id] 
            if current_time - t < period
        ]
        
        if len(self.user_activity[user_id]) >= max_requests:
            self.log_security_event(user_id, "RATE_LIMIT_EXCEEDED", 
                                  f"Attempts: {len(self.user_activity[user_id])}")
            return False
        
        self.user_activity[user_id].append(current_time)
        return True
    
    def check_global_limit(self, max_requests=100, period=60):
        """Глобальное ограничение запросов"""
        current_time = time.time()
        self.global_activity = [
            t for t in self.global_activity 
            if current_time - t < period
        ]
        
        if len(self.global_activity) >= max_requests:
            self.log_security_event("GLOBAL", "GLOBAL_RATE_LIMIT_EXCEEDED",
                                  f"Global attempts: {len(self.global_activity)}")
            return False
        
        self.global_activity.append(current_time)
        return True
    
    def sanitize_input(self, text):
        """Очистка входных данных"""
        if not text or not isinstance(text, str):
            return ""
            
        # Ограничение длины
        if len(text) > 1000:
            text = text[:1000]
        
        # Экранирование HTML
        safe_text = html.escape(text)
        
        # Проверка на опасные паттерны
        for pattern in self.suspicious_patterns:
            if re.search(pattern, safe_text, re.IGNORECASE):
                self.log_security_event("INPUT_VALIDATION", "SUSPICIOUS_PATTERN",
                                      f"Pattern: {pattern}, Text: {safe_text[:100]}")
                return None
        
        return safe_text
    
    def block_user(self, user_id, duration=3600):
        """Блокировка пользователя на определенное время"""
        self.blocked_users.add(user_id)
        self.log_security_event(user_id, "USER_BLOCKED", f"Duration: {duration} seconds")
        
        # Запланировать разблокировку через duration секунд
        # В реальной системе нужно использовать asyncio или планировщик задач
        
    def is_user_blocked(self, user_id):
        """Проверка, заблокирован ли пользователь"""
        return user_id in self.blocked_users
    
    def log_security_event(self, user_id, event_type, message=""):
        """Логирование событий безопасности"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[SECURITY] {timestamp} - {event_type} - User: {user_id}"
        
        if message:
            log_message += f" - Details: {message}"
        
        # Запись в файл
        try:
            with open("security.log", "a", encoding="utf-8") as log_file:
                log_file.write(log_message + "\n")
        except Exception as e:
            logger.error(f"Failed to write to security log: {e}")
        
        # Также логируем через стандартный логгер
        if "RATE_LIMIT" in event_type or "BLOCKED" in event_type:
            logger.warning(log_message)
        else:
            logger.info(log_message)

# Инициализация системы безопасности
security = SecuritySystem()

# Декоратор для проверки безопасности
def secure_handler(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Пропускаем сообщения без текста (медиа, команды и т.д.)
        if not update.message or not update.message.text:
            return await func(update, context)
            
        user_id = update.effective_user.id
        
        # Проверка блокировки
        if security.is_user_blocked(user_id):
            await update.message.reply_text("⛔ Вы временно заблокированы за нарушение правил.")
            security.log_security_event(user_id, "BLOCKED_USER_ATTEMPT")
            return
        
        # Проверка глобального лимита
        if not security.check_global_limit():
            await update.message.reply_text("⚠️ Система перегружена. Попробуйте позже.")
            return
        
        # Проверка лимита для пользователя
        if not security.check_rate_limit(user_id):
            await update.message.reply_text("⚠️ Слишком много запросов. Подождите минуту.")
            return
        
        # Очистка входных данных
        safe_text = security.sanitize_input(update.message.text)
        if safe_text is None:
            security.block_user(user_id)
            await update.message.reply_text("❌ Обнаружены недопустимые символы. Вы заблокированы.")
            return
        
        # Передаем безопасный текст через контекст вместо изменения сообщения
        context.safe_text = safe_text
        
        # Вызываем оригинальный обработчик
        try:
            return await func(update, context)
        except Exception as e:
            security.log_security_event(user_id, "HANDLER_ERROR", f"Error: {str(e)}")
            raise
    
    return wrapper
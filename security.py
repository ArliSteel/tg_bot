# security.py
import time
import html
import re
import logging
import asyncio
from datetime import datetime
from collections import defaultdict
from functools import wraps
import logging.handlers
import os

# Добавляем необходимые импорты для telegram бота
from telegram import Update
from telegram.ext import ContextTypes

# Настройка логгера для модуля безопасности
logger = logging.getLogger(__name__)

# Конфигурация безопасности с возможностью переопределения через переменные окружения
SECURITY_CONFIG = {
    'MAX_TEXT_LENGTH': int(os.getenv("MAX_TEXT_LENGTH", "800")),
    'USER_RATE_LIMIT': int(os.getenv("USER_RATE_LIMIT", "5")),
    'USER_RATE_PERIOD': int(os.getenv("USER_RATE_PERIOD", "60")),
    'GLOBAL_RATE_LIMIT': int(os.getenv("GLOBAL_RATE_LIMIT", "100")),
    'GLOBAL_RATE_PERIOD': int(os.getenv("GLOBAL_RATE_PERIOD", "60")),
    'DEFAULT_BLOCK_DURATION': int(os.getenv("BLOCK_DURATION", "3600")),
    'WARNING_THRESHOLD': int(os.getenv("WARNING_THRESHOLD", "3")),
    'WARNING_DURATION': int(os.getenv("WARNING_DURATION", "3600")),
    'LOG_MAX_BYTES': 10 * 1024 * 1024,  # 10MB
    'LOG_BACKUP_COUNT': 5
}

class SecuritySystem:
    def __init__(self):
        self.user_activity = defaultdict(list)
        self.global_activity = []
        self.blocked_users = {}
        self.user_warnings = defaultdict(list)  # user_id: list of (timestamp, reason)
        self.config = SECURITY_CONFIG
        
        # Критические паттерны - немедленная блокировка
        self.critical_patterns = [
            r"<script.*?>", r"javascript:", r"onload=", r"onerror=",
            r"DROP TABLE", r"UNION SELECT", r"INSERT INTO", r"DELETE FROM",
            r"\.\./", r"\.\.\\", r"eval\(", r"exec\(", r"alert\(",
            r"window\.location", r"document\.cookie", r"localStorage",
            r"process\.env", r"require\(", r"fs\.", r"child_process",
            r"bash.*-i", r"curl.*bash", r"wget.*bash"  # Паттерны для reverse shell
        ]
        
        # Не критические паттерны - предупреждения
        self.non_critical_patterns = [
            r"\.env", r"config\.", r"password", r"token", r"secret",
            r"api[_-]?key", r"auth", r"login", r"credential"
        ]
        
        # Настройка ротации логов
        self.setup_logging()
    
    def setup_logging(self):
        """Настройка ротации логов безопасности"""
        try:
            # Создаем директорию для логов, если её нет
            os.makedirs("logs", exist_ok=True)
            
            log_handler = logging.handlers.RotatingFileHandler(
                "logs/security.log",
                maxBytes=self.config['LOG_MAX_BYTES'],
                backupCount=self.config['LOG_BACKUP_COUNT'],
                encoding='utf-8'
            )
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            log_handler.setFormatter(formatter)
            
            security_logger = logging.getLogger('security')
            security_logger.addHandler(log_handler)
            security_logger.setLevel(logging.INFO)
        except Exception as e:
            logger.error(f"Failed to setup security log rotation: {e}")
    
    def get_current_request_count(self, user_id, period=None):
        """Возвращает текущее количество запросов пользователя за период"""
        period = period or self.config['USER_RATE_PERIOD']
        current_time = time.time()
        
        # Очистка старых запросов
        self.user_activity[user_id] = [
            t for t in self.user_activity[user_id] 
            if current_time - t < period
        ]
        
        return len(self.user_activity[user_id])
    
    def detect_suspicious(self, text):
        """Обнаружение подозрительных паттернов с разделением на критические и не критические"""
        if not text or not isinstance(text, str):
            return None
            
        # Сначала проверяем критические паттерны
        for pattern in self.critical_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return 'critical'
        
        # Затем не критические паттерны
        for pattern in self.non_critical_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return 'non_critical'
                
        return None
    
    def check_rate_limit(self, user_id, max_requests=None, period=None):
        """Проверка ограничения частоты запросов"""
        max_requests = max_requests or self.config['USER_RATE_LIMIT']
        period = period or self.config['USER_RATE_PERIOD']
        
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
    
    def check_global_limit(self, max_requests=None, period=None):
        """Глобальное ограничение запросов"""
        max_requests = max_requests or self.config['GLOBAL_RATE_LIMIT']
        period = period or self.config['GLOBAL_RATE_PERIOD']
        
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
    
    def add_warning(self, user_id, reason):
        """Добавляет предупреждение пользователю и возвращает True, если превышен лимит"""
        current_time = time.time()
        
        # Очищаем старые предупреждения
        self.user_warnings[user_id] = [
            (t, r) for t, r in self.user_warnings[user_id] 
            if current_time - t < self.config['WARNING_DURATION']
        ]
        
        # Добавляем новое предупреждение
        self.user_warnings[user_id].append((current_time, reason))
        
        # Логируем добавление предупреждения
        self.log_security_event(user_id, "WARNING_ADDED", 
                              f"Reason: {reason}, Count: {len(self.user_warnings[user_id])}")
        
        # Проверяем, превышен ли лимит предупреждений
        if len(self.user_warnings[user_id]) >= self.config['WARNING_THRESHOLD']:
            self.log_security_event(user_id, "WARNING_LIMIT_EXCEEDED",
                                  f"Warning count: {len(self.user_warnings[user_id])}")
            return True
            
        return False
    
    def get_warning_count(self, user_id):
        """Возвращает количество активных предупреждений пользователя"""
        current_time = time.time()
        
        # Очищаем старые предупреждения
        self.user_warnings[user_id] = [
            (t, r) for t, r in self.user_warnings[user_id] 
            if current_time - t < self.config['WARNING_DURATION']
        ]
        
        return len(self.user_warnings[user_id])
    
    def sanitize_input(self, text):
        """Очистка входных данных"""
        if not text or not isinstance(text, str):
            return ""
            
        # Сначала проверка на опасные паттерны в сыром тексте
        suspicious_type = self.detect_suspicious(text)
        if suspicious_type:
            self.log_security_event("INPUT_VALIDATION", f"SUSPICIOUS_PATTERN_{suspicious_type.upper()}",
                                  f"Text: {text[:100]}...")
            return None
            
        # Ограничение длины
        if len(text) > self.config['MAX_TEXT_LENGTH']:
            text = text[:self.config['MAX_TEXT_LENGTH']]
        
        # Экранирование HTML
        return html.escape(text)
    
    async def block_user(self, user_id, duration=None):
        """Блокировка пользователя на определенное время с автоматической разблокировкой"""
        duration = duration or self.config['DEFAULT_BLOCK_DURATION']
        unblock_time = time.time() + duration
        
        self.blocked_users[user_id] = unblock_time
        self.log_security_event(user_id, "USER_BLOCKED", f"Duration: {duration} seconds")
        
        # Запланировать автоматическую разблокировку
        asyncio.create_task(self._unblock_user(user_id, duration))
    
    async def _unblock_user(self, user_id, duration):
        """Автоматическая разблокировка пользователя после истечения времени"""
        await asyncio.sleep(duration)
        if user_id in self.blocked_users:
            del self.blocked_users[user_id]
            self.log_security_event(user_id, "USER_UNBLOCKED", "Auto-unblock after timeout")
        
    def is_user_blocked(self, user_id):
        """Проверка, заблокирован ли пользователь"""
        if user_id not in self.blocked_users:
            return False
            
        # Проверяем, не истекло ли время блокировки
        if time.time() > self.blocked_users[user_id]:
            del self.blocked_users[user_id]
            return False
            
        return True
    
    def log_security_event(self, user_id, event_type, message=""):
        """Логирование событий безопасности с маскированием конфиденциальных данных"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Маскирование пользовательских данных в логах
        masked_message = message
        if "Text:" in message:
            # Оставляем только первые 50 символов для диагностики
            text_part = message.split("Text:")[1]
            if len(text_part) > 50:
                masked_message = message.replace(text_part, text_part[:50] + "...")
        
        log_message = f"[SECURITY] {timestamp} - {event_type} - User: {user_id}"
        
        if masked_message:
            log_message += f" - Details: {masked_message}"
        
        # Запись в файл с ротацией
        try:
            security_logger = logging.getLogger('security')
            if "RATE_LIMIT" in event_type or "BLOCKED" in event_type or "WARNING_LIMIT" in event_type:
                security_logger.warning(log_message)
            else:
                security_logger.info(log_message)
        except Exception as e:
            logger.error(f"Failed to write to security log: {e}")
        
        # Также логируем через стандартный логгер
        if "RATE_LIMIT" in event_type or "BLOCKED" in event_type or "WARNING_LIMIT" in event_type:
            logger.warning(log_message)
        else:
            logger.info(log_message)

# Инициализация системы безопасности
security = SecuritySystem()

# Исправленный декоратор secure_handler
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
        
        # Проверка на опасные паттерны в сыром тексте
        raw_text = update.message.text
        suspicious_type = security.detect_suspicious(raw_text)
        
        if suspicious_type == 'critical':
            # Критическое нарушение - немедленная блокировка
            await security.block_user(user_id)
            await update.message.reply_text("❌ Обнаружены недопустимые символы. Вы заблокированы на 1 час.")
            return
        elif suspicious_type == 'non_critical':
            # Не критическое нарушение - добавляем предупреждение
            warning_exceeded = security.add_warning(user_id, "SUSPICIOUS_CONTENT")
            
            if warning_exceeded:
                await security.block_user(user_id)
                await update.message.reply_text("❌ Вы заблокированы за многократные нарушения.")
            else:
                warning_count = security.get_warning_count(user_id)
                max_warnings = security.config['WARNING_THRESHOLD']
                await update.message.reply_text(
                    f"⚠️ Обнаружены подозрительные символы. Предупреждение {warning_count}/{max_warnings}. "
                    f"После {max_warnings} предупреждений вы будете заблокированы."
                )
            return
        
        # Очистка входных данных
        safe_text = security.sanitize_input(raw_text)
        if safe_text is None:
            # Добавляем предупреждение за недопустимые символы
            warning_exceeded = security.add_warning(user_id, "INVALID_CONTENT")
            
            if warning_exceeded:
                await security.block_user(user_id)
                await update.message.reply_text("❌ Вы заблокированы за многократные нарушения.")
            else:
                warning_count = security.get_warning_count(user_id)
                max_warnings = security.config['WARNING_THRESHOLD']
                await update.message.reply_text(
                    f"⚠️ Обнаружены недопустимые символы. Предупреждение {warning_count}/{max_warnings}. "
                    f"После {max_warnings} предупреждений вы будете заблокированы."
                )
            return
        
        # Передаем безопасный текст через контекст
        context.safe_text = safe_text
        
        # Вызываем оригинальный обработчик
        try:
            return await func(update, context)
        except Exception as e:
            security.log_security_event(user_id, "HANDLER_ERROR", f"Error: {str(e)}")
            raise
    
    return wrapper
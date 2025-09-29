import asyncio
import time
import logging
import re
from collections import defaultdict
from services.yandex_gpt import YandexGPTClient
from services.security import security
from services.database import log_bot_response  # 🔥 НОВЫЙ ИМПОРТ
from utils.simulation import simulate_typing_with_errors, simulate_human_typing_mistakes
from utils.formatting import escape_markdown_text
from models.config import SALON_CONFIG
from config import load_config

logger = logging.getLogger(__name__)

class UserStateManager:
    """Менеджер состояния пользователей для обработки сообщений"""
    
    def __init__(self):
        self.user_message_queues = defaultdict(list)
        self.user_processing_tasks = {}
        self.processing_lock = asyncio.Lock()
    
    async def add_and_process_message(self, user_id, chat_id, context, message):
        """Добавляет сообщение в очередь и запускает обработку"""
        async with self.processing_lock:
            # Инициализируем очередь для пользователя, если нужно
            if user_id not in self.user_message_queues:
                self.user_message_queues[user_id] = []
            
            # Добавляем сообщение в очередь
            self.user_message_queues[user_id].append(message)
            
            # Если уже есть задача обработки, отменяем ее
            if user_id in self.user_processing_tasks:
                try:
                    self.user_processing_tasks[user_id].cancel()
                except:
                    pass
            
            # Создаем новую задачу обработки
            self.user_processing_tasks[user_id] = asyncio.create_task(
                self.process_user_messages(user_id, chat_id, context)
            )
    
    async def process_user_messages(self, user_id, chat_id, context):
        """Обрабатывает все сообщения пользователя за раз"""
        try:
            # Ждем 1 секунду для получения возможных дополнительных сообщений
            await asyncio.sleep(1.0)
            
            async with self.processing_lock:
                if user_id not in self.user_message_queues or not self.user_message_queues[user_id]:
                    return
                
                # Получаем все сообщения из очереди
                messages = self.user_message_queues[user_id].copy()
                self.user_message_queues[user_id] = []
                
                # Удаляем задачу обработки
                if user_id in self.user_processing_tasks:
                    del self.user_processing_tasks[user_id]
            
            # Проверяем лимиты без добавления запросов
            current_count = security.get_current_request_count(user_id)
            max_requests = security.config['USER_RATE_LIMIT']
            
            if current_count + len(messages) > max_requests:
                # Превышение лимита - добавляем предупреждение
                warning_exceeded = security.add_warning(user_id, "RATE_LIMIT_EXCEEDED")
                
                if warning_exceeded:
                    await security.block_user(user_id)
                    await context.bot.send_message(chat_id, "⛔ Вы заблокированы за спам.")
                else:
                    warning_count = security.get_warning_count(user_id)
                    max_warnings = security.config['WARNING_THRESHOLD']
                    await context.bot.send_message(
                        chat_id,
                        f"⚠️ Слишком много сообщений. Предупреждение {warning_count}/{max_warnings}."
                    )
                
                # Добавляем запросы в историю (по одному на каждое сообщение)
                for _ in range(len(messages)):
                    security.user_activity[user_id].append(time.time())
                return
            
            # Добавляем запросы в историю (по одному на каждое сообщение)
            for _ in range(len(messages)):
                security.user_activity[user_id].append(time.time())
            
            # Объединяем сообщения в один текст (исключаем дубликаты)
            unique_messages = []
            for msg in messages:
                if msg not in unique_messages:
                    unique_messages.append(msg)
            
            combined_text = " ".join(unique_messages)
            
            # Генерируем ответ
            reply = await YandexGPTClient.generate_response(combined_text)
            
            # Проверяем безопасность ответа
            if not self.check_response_safety(reply):
                logger.warning(f"Ответ LLM содержит потенциально опасный контент: {reply[:100]}...")
                reply = "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте другой вопрос."
            
            # Ограничиваем длину ответа
            if len(reply) > 4000:  # MAX_TEXT_LENGTH из конфига
                reply = reply[:4000] + "..."
            
            # Симуляция человеческого печатания
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            typing_time = await simulate_typing_with_errors(chat_id, context, reply)
            logger.info(f"Симуляция печатания заняла {typing_time:.2f} секунд")
            
            # Добавляем случайные опечатки для естественности
            reply = await simulate_human_typing_mistakes(reply)
            
            # Фильтрация нежелательных фраз
            if self.contains_banned_content(reply):
                reply = "🚫 Этот вопрос требует консультации специалиста. Пожалуйста, обратитесь к администратору по телефону."
            
            # Добавляем профессиональное завершение к ответам
            if not any(phrase in reply.lower() for phrase in ["звоните", "телефон", "контакт", "адрес"]):
                reply += f"\n\n📞 Для записи на диагностику звоните: {SALON_CONFIG['contacts']}"
            
            # Пробуем отправить с MarkdownV2
            try:
                # Импортируем функцию валидации
                from utils.formatting import validate_markdown
                
                # Проверяем корректность MarkdownV2
                if validate_markdown(reply):
                    await context.bot.send_message(chat_id, reply, parse_mode='MarkdownV2')
                    
                    # 🔥 НОВОЕ: Логируем ответ бота в базу данных
                    asyncio.create_task(
                        log_bot_response(
                            user_id=user_id,
                            chat_id=chat_id,
                            response_text=reply[:1000]  # Ограничиваем длину
                        )
                    )
                    
                    logger.info(f"Отправлен ответ с MarkdownV2 пользователю {user_id}, длина: {len(reply)} символов")
                else:
                    # Если валидация не прошла - отправляем без форматирования
                    clean_reply = self.strip_markdown(reply)
                    await context.bot.send_message(chat_id, clean_reply)
                    
                    # 🔥 НОВОЕ: Логируем ответ бота в базу данных
                    asyncio.create_task(
                        log_bot_response(
                            user_id=user_id,
                            chat_id=chat_id,
                            response_text=clean_reply[:1000]  # Ограничиваем длину
                        )
                    )
                    
                    logger.info(f"Отправлен ответ БЕЗ форматирования (валидация не прошла) пользователю {user_id}")
                    
            except Exception as parse_error:
                logger.warning(f"Ошибка отправки с MarkdownV2: {parse_error}")
                # Отправляем без форматирования
                clean_reply = self.strip_markdown(reply)
                try:
                    await context.bot.send_message(chat_id, clean_reply)
                    
                    # 🔥 НОВОЕ: Логируем ответ бота в базу данных
                    asyncio.create_task(
                        log_bot_response(
                            user_id=user_id,
                            chat_id=chat_id,
                            response_text=clean_reply[:1000]  # Ограничиваем длину
                        )
                    )
                    
                    logger.info(f"Отправлен запасной ответ БЕЗ форматирования пользователю {user_id}")
                except Exception as final_error:
                    logger.error(f"Критическая ошибка отправки сообщения: {final_error}")
                    # Последняя попытка с минимальным сообщением
                    error_msg = "Извините, произошла техническая ошибка. Попробуйте позже."
                    await context.bot.send_message(chat_id, error_msg)
                    
                    # 🔥 НОВОЕ: Логируем ошибку в базу данных
                    asyncio.create_task(
                        log_bot_response(
                            user_id=user_id,
                            chat_id=chat_id,
                            response_text=error_msg
                        )
                    )
            
        except asyncio.CancelledError:
            # Задача была отменена, это нормально
            pass
        except Exception as e:
            logger.error(f"Ошибка в process_user_messages: {e}")
    
    def strip_markdown(self, text):
        """Удаляет все Markdown символы из текста"""
        if not text:
            return ""
        # Удаляем все markdown символы
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Жирный текст
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Курсив
        # Убираем экранированные символы
        text = re.sub(r'\\([_\[\]()~`>#+=|{}.!-])', r'\1', text)
        return text
    
    def contains_banned_content(self, text):
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
    
    def check_response_safety(self, text):
        """Проверяет ответ LLM на утечку конфиденциальной информации"""
        if not text:
            return True
        
        # Убираем из проверки публичную информацию, которая должна быть в ответах
        config = load_config()
        
        # Список публичной информации, которая РАЗРЕШЕНА в ответах
        allowed_public_info = [
            SALON_CONFIG['contacts'],  # Публичный номер телефона
            SALON_CONFIG['address'],   # Публичный адрес
            SALON_CONFIG['name'],      # Название компании
            config.webhook_url if config.webhook_url else "",  # URL вебхука (если публичный)
        ]
        
        # Создаем временную копию текста без разрешенной публичной информации
        temp_text = text
        for allowed_info in allowed_public_info:
            if allowed_info:
                temp_text = temp_text.replace(str(allowed_info), "")
        
        # Проверяем на утечку РЕАЛЬНЫХ секретов (но не публичной информации)
        secret_patterns = [
            r'[A-Za-z0-9]{40,}',       # Очень длинные строки (токены/ключи)
            r'sk-[A-Za-z0-9]{20,}',    # API ключи OpenAI
            r'AKIA[0-9A-Z]{16}',       # AWS ключи
            r'password\s*[:=]\s*\S+',  # Пароли в формате "password: xxx"
            r'token\s*[:=]\s*[A-Za-z0-9]{20,}',  # Токены в формате "token: xxx"
            r'api[_-]?key\s*[:=]\s*[A-Za-z0-9]{20,}',  # API ключи в формате "api_key: xxx"
            r'secret\s*[:=]\s*[A-Za-z0-9]{20,}',  # Секреты в формате "secret: xxx"
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, temp_text, re.IGNORECASE):
                logger.warning(f"Обнаружена потенциальная утечка в ответе LLM: {pattern}")
                return False
        
        # Проверяем на наличие НАСТОЯЩИХ конфиденциальных данных (не публичных)
        truly_sensitive_data = [
            config.bot_token,
            config.yandex_api_key,
            config.webhook_secret,
        ]
        
        for data in truly_sensitive_data:
            if data and len(str(data)) > 10 and str(data) in text:
                logger.warning("Обнаружена утечка НАСТОЯЩИХ конфиденциальных данных в ответе LLM")
                return False
        
        return True
    
    async def cleanup_queues(self):
        """Очищает старые очереди сообщений"""
        while True:
            await asyncio.sleep(300)  # Каждые 5 минут
            current_time = time.time()
            async with self.processing_lock:
                for user_id in list(self.user_message_queues.keys()):
                    # Если очередь пуста более 10 минут, удаляем ее
                    if not self.user_message_queues[user_id]:
                        del self.user_message_queues[user_id]
                for user_id in list(self.user_processing_tasks.keys()):
                    # Если задача завершена, удаляем ее
                    if self.user_processing_tasks[user_id].done():
                        del self.user_processing_tasks[user_id]

# Глобальный экземпляр менеджера состояния
user_state = UserStateManager()
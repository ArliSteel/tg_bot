import asyncio
import time
import logging
import re
from collections import defaultdict
from services.yandex_gpt import YandexGPTClient
from services.security import security
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
            if user_id not in self.user_message_queues:
                self.user_message_queues[user_id] = []
            
            self.user_message_queues[user_id].append(message)
            
            if user_id in self.user_processing_tasks:
                try:
                    self.user_processing_tasks[user_id].cancel()
                except:
                    pass
            
            self.user_processing_tasks[user_id] = asyncio.create_task(
                self.process_user_messages(user_id, chat_id, context)
            )
    
    async def process_user_messages(self, user_id, chat_id, context):
        """Обрабатывает все сообщения пользователя за раз"""
        try:
            await asyncio.sleep(1.0)
            
            async with self.processing_lock:
                if user_id not in self.user_message_queues or not self.user_message_queues[user_id]:
                    return
                
                messages = self.user_message_queues[user_id].copy()
                self.user_message_queues[user_id] = []
                
                if user_id in self.user_processing_tasks:
                    del self.user_processing_tasks[user_id]
            
            # Проверяем лимиты
            current_count = security.get_current_request_count(user_id)
            max_requests = security.config['USER_RATE_LIMIT']
            
            if current_count + len(messages) > max_requests:
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
                
                for _ in range(len(messages)):
                    security.user_activity[user_id].append(time.time())
                return
            
            for _ in range(len(messages)):
                security.user_activity[user_id].append(time.time())
            
            # Объединяем сообщения
            unique_messages = []
            for msg in messages:
                if msg not in unique_messages:
                    unique_messages.append(msg)
            
            combined_text = " ".join(unique_messages)
            
            # 🔥 ПРОСТОЙ ПОДХОД: считаем примерное количество тем
            theme_count = self._count_simple_themes(combined_text)
            
            if theme_count >= 3:
                logger.info(f"Сложный запрос: {theme_count} тем")
                # Для сложных запросов добавляем строгое требование
                strict_prompt = f"""
Клиент задал запрос с {theme_count} темами. Ты ОБЯЗАН ответить на КАЖДУЮ тему!

Основные темы в запросе: {self._get_simple_themes_list(combined_text)}

ПРАВИЛА ОТВЕТА:
1. Ответь на ВСЕ темы по порядку
2. Давай конкретные цены и сроки  
3. Не пропускай ни одной темы
4. Будь краток, но информативен

Запрос клиента: {combined_text}
"""
                reply = await YandexGPTClient.generate_response(strict_prompt)
            else:
                reply = await YandexGPTClient.generate_response(combined_text)
            
            # 🔥 ПРОВЕРКА: если ответ слишком короткий, пробуем еще раз
            if theme_count >= 3 and len(reply) < 500:
                logger.warning("Ответ слишком краткий, пробуем еще раз")
                retry_prompt = f"""
Предыдущий ответ был слишком коротким! Клиент ждет ответа на ВСЕ темы.

Темы которые нужно охватить: {self._get_simple_themes_list(combined_text)}

Сделай развернутый ответ на каждую тему! Не пропускай ничего!

Запрос: {combined_text}
"""
                reply = await YandexGPTClient.generate_response(retry_prompt)
            
            # Проверяем безопасность
            if not self.check_response_safety(reply):
                logger.warning("Небезопасный ответ LLM")
                reply = "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте другой вопрос."
            
            # Ограничиваем длину
            if len(reply) > 4000:
                reply = reply[:4000] + "..."
            
            # СИМУЛЯЦИЯ ПЕЧАТАНИЯ
            try:
                typing_time = await simulate_typing_with_errors(chat_id, context, reply)
                logger.info(f"Печатание: {typing_time:.2f} сек")
            except Exception as e:
                logger.error(f"Ошибка симуляции: {e}")
                await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                await asyncio.sleep(2)
            
            # Добавляем опечатки
            reply = await simulate_human_typing_mistakes(reply)
            
            # Фильтрация
            if self.contains_banned_content(reply):
                reply = "🚫 Этот вопрос требует консультации специалиста. Пожалуйста, обратитесь к администратору по телефону."
            
            # Добавляем контакты если их нет
            if not any(phrase in reply.lower() for phrase in ["звоните", "телефон", "контакт", "адрес", "диагностик"]):
                reply += f"\n\n📞 Для уточнения деталей звоните: {SALON_CONFIG['contacts']}"
            
            # Отправляем сообщение
            try:
                from utils.formatting import validate_markdown
                
                if validate_markdown(reply):
                    await context.bot.send_message(chat_id, reply, parse_mode='MarkdownV2')
                    logger.info(f"✅ Ответ отправлен пользователю {user_id}")
                else:
                    clean_reply = self.strip_markdown(reply)
                    await context.bot.send_message(chat_id, clean_reply)
                    logger.info(f"⚠️ Ответ без форматирования пользователю {user_id}")
                    
            except Exception as parse_error:
                logger.warning(f"Ошибка Markdown: {parse_error}")
                clean_reply = self.strip_markdown(reply)
                try:
                    await context.bot.send_message(chat_id, clean_reply)
                    logger.info(f"✅ Запасной ответ пользователю {user_id}")
                except Exception as final_error:
                    logger.error(f"❌ Критическая ошибка: {final_error}")
                    error_msg = "Извините, произошла техническая ошибка. Попробуйте позже."
                    await context.bot.send_message(chat_id, error_msg)
            
        except asyncio.CancelledError:
            logger.info(f"Задача отменена для пользователя {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            try:
                error_msg = "⚠️ Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
                await context.bot.send_message(chat_id, error_msg)
            except:
                pass
    
    def _count_simple_themes(self, text: str) -> int:
        """Простой подсчет тем по ключевым словам"""
        text_lower = text.lower()
        themes = [
            'полировка', 'покраск', 'керамик', 'фары', 'химчистк', 
            'скидк', 'время', 'срок', 'гарантия', 'цена', 'стоимость',
            'диагностик', 'запись', 'pdr', 'вмятины', 'скол'
        ]
        return sum(1 for theme in themes if theme in text_lower)
    
    def _get_simple_themes_list(self, text: str) -> str:
        """Возвращает список тем для промпта"""
        text_lower = text.lower()
        theme_map = {
            'полировка': 'виды полировки и цены',
            'покраск': 'покраска и восстановление',
            'керамик': 'керамическое покрытие', 
            'фары': 'полировка фар',
            'химчистк': 'химчистка салона',
            'скидк': 'скидки и акции',
            'время': 'сроки работ',
            'гарантия': 'гарантия на работы',
            'pdr': 'технология PDR'
        }
        
        found = []
        for theme, description in theme_map.items():
            if theme in text_lower:
                found.append(description)
        
        return ", ".join(found) if found else "все вопросы клиента"
    
    def strip_markdown(self, text):
        if not text:
            return ""
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'\\([_\[\]()~`>#+=|{}.!-])', r'\1', text)
        return text
    
    def contains_banned_content(self, text):
        if not text:
            return False
        text_lower = text.lower()
        medical_phrases = ["лечебн", "медицинск", "вылеч"]
        legal_phrases = ["юридическ", "адвокат", "суд"]

        if any(phrase in text_lower for phrase in medical_phrases) and "авто" not in text_lower:
            return True
        if any(phrase in text_lower for phrase in legal_phrases):
            return True
        return False
    
    def check_response_safety(self, text):
        if not text:
            return True
        
        config = load_config()
        allowed_public_info = [
            SALON_CONFIG['contacts'],
            SALON_CONFIG['address'], 
            SALON_CONFIG['name'],
            config.webhook_url if config.webhook_url else "",
        ]
        
        temp_text = text
        for allowed_info in allowed_public_info:
            if allowed_info:
                temp_text = temp_text.replace(str(allowed_info), "")
        
        secret_patterns = [
            r'[A-Za-z0-9]{40,}',
            r'sk-[A-Za-z0-9]{20,}',
            r'AKIA[0-9A-Z]{16}',
            r'password\s*[:=]\s*\S+',
            r'token\s*[:=]\s*[A-Za-z0-9]{20,}',
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, temp_text, re.IGNORECASE):
                return False
        
        truly_sensitive_data = [
            config.bot_token,
            config.yandex_api_key,
            config.webhook_secret,
        ]
        
        for data in truly_sensitive_data:
            if data and len(str(data)) > 10 and str(data) in text:
                return False
        
        return True
    
    async def cleanup_queues(self):
        while True:
            await asyncio.sleep(300)
            current_time = time.time()
            async with self.processing_lock:
                users_to_remove = []
                for user_id in self.user_message_queues:
                    if not self.user_message_queues[user_id]:
                        users_to_remove.append(user_id)
                for user_id in users_to_remove:
                    del self.user_message_queues[user_id]
                
                tasks_to_remove = []
                for user_id in self.user_processing_tasks:
                    if self.user_processing_tasks[user_id].done():
                        tasks_to_remove.append(user_id)
                for user_id in tasks_to_remove:
                    del self.user_processing_tasks[user_id]

user_state = UserStateManager()
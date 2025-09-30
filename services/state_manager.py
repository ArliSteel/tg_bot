# services/state_manager.py
import asyncio
import time
import logging
import re
from collections import defaultdict
from services.yandex_gpt import YandexGPTClient
from services.security import security
# from services.database import log_bot_response  # Временно отключено
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
            
            # 🔥 УМНЫЙ АНАЛИЗ ЛЮБОГО ЗАПРОСА
            query_analysis = self._analyze_query_structure(combined_text)
            
            logger.info(f"📊 Анализ запроса от {user_id}: {query_analysis['questions_count']} вопросов, {len(query_analysis['themes'])} тем, сложность {query_analysis['complexity']}/5")
            
            if query_analysis['complexity'] >= 2:
                # Для сложных запросов создаем умный промпт
                smart_prompt = self._create_smart_prompt(combined_text, query_analysis)
                reply = await YandexGPTClient.generate_response(smart_prompt)
            else:
                reply = await YandexGPTClient.generate_response(combined_text)
            
            # 🔥 ПРОВЕРКА ПОЛНОТЫ ОТВЕТА ДЛЯ СЛОЖНЫХ ЗАПРОСОВ
            if query_analysis['complexity'] >= 3:
                is_complete = self._check_answer_completeness(reply, combined_text)
                if not is_complete:
                    logger.warning(f"❌ Ответ слишком краткий для сложного запроса, генерируем улучшенную версию")
                    # Генерируем ответ еще раз с более строгим промптом
                    strict_prompt = self._create_strict_prompt(combined_text, query_analysis)
                    reply = await YandexGPTClient.generate_response(strict_prompt)
            
            # Проверяем безопасность ответа
            if not self.check_response_safety(reply):
                logger.warning(f"Ответ LLM содержит потенциально опасный контент: {reply[:100]}...")
                reply = "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте другой вопрос."
            
            # Ограничиваем длину ответа
            if len(reply) > 4000:  # MAX_TEXT_LENGTH из конфига
                reply = reply[:4000] + "..."
            
            # 🔥 УЛУЧШЕННАЯ СИМУЛЯЦИЯ ПЕЧАТАНИЯ
            try:
                # Новая реалистичная симуляция печатания
                typing_time = await simulate_typing_with_errors(chat_id, context, reply)
                logger.info(f"✅ Реалистичная симуляция печатания заняла {typing_time:.2f} секунд для {len(reply)} символов")
            except Exception as e:
                logger.error(f"Ошибка симуляции печатания: {e}")
                # Фолбэк: простая задержка
                await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                await asyncio.sleep(2)
            
            # Добавляем случайные опечатки для естественности
            reply = await simulate_human_typing_mistakes(reply)
            
            # Фильтрация нежелательных фраз
            if self.contains_banned_content(reply):
                reply = "🚫 Этот вопрос требует консультации специалиста. Пожалуйста, обратитесь к администратору по телефону."
            
            # Добавляем профессиональное завершение к ответам, если его нет
            if not any(phrase in reply.lower() for phrase in ["звоните", "телефон", "контакт", "адрес", "диагностик"]):
                reply += f"\n\n📞 Для уточнения деталей звоните: {SALON_CONFIG['contacts']}"
            
            # Пробуем отправить с MarkdownV2
            try:
                # Импортируем функцию валидации
                from utils.formatting import validate_markdown
                
                # Проверяем корректность MarkdownV2
                if validate_markdown(reply):
                    await context.bot.send_message(chat_id, reply, parse_mode='MarkdownV2')
                    
                    # 🔥 ВРЕМЕННО ОТКЛЮЧЕНО: Логирование ответа бота в базу данных
                    # try:
                    #     asyncio.create_task(
                    #         log_bot_response(
                    #             user_id=user_id,
                    #             chat_id=chat_id,
                    #             response_text=reply[:1000]
                    #         )
                    #     )
                    # except Exception as db_error:
                    #     logger.error(f"Ошибка логирования в БД: {db_error}")
                    
                    logger.info(f"✅ Отправлен развернутый ответ пользователю {user_id}, длина: {len(reply)} символов")
                else:
                    # Если валидация не прошла - отправляем без форматирования
                    clean_reply = self.strip_markdown(reply)
                    await context.bot.send_message(chat_id, clean_reply)
                    
                    # 🔥 ВРЕМЕННО ОТКЛЮЧЕНО: Логирование ответа бота в базу данных
                    # try:
                    #     asyncio.create_task(
                    #         log_bot_response(
                    #             user_id=user_id,
                    #             chat_id=chat_id,
                    #             response_text=clean_reply[:1000]
                    #         )
                    #     )
                    # except Exception as db_error:
                    #     logger.error(f"Ошибка логирования в БД: {db_error}")
                    
                    logger.info(f"⚠️ Отправлен ответ БЕЗ форматирования (валидация не прошла) пользователю {user_id}")
                    
            except Exception as parse_error:
                logger.warning(f"Ошибка отправки с MarkdownV2: {parse_error}")
                # Отправляем без форматирования
                clean_reply = self.strip_markdown(reply)
                try:
                    await context.bot.send_message(chat_id, clean_reply)
                    
                    # 🔥 ВРЕМЕННО ОТКЛЮЧЕНО: Логирование ответа бота в базу данных
                    # try:
                    #     asyncio.create_task(
                    #         log_bot_response(
                    #             user_id=user_id,
                    #             chat_id=chat_id,
                    #             response_text=clean_reply[:1000]
                    #         )
                    #     )
                    # except Exception as db_error:
                    #     logger.error(f"Ошибка логирования в БД: {db_error}")
                    
                    logger.info(f"✅ Отправлен запасной ответ БЕЗ форматирования пользователю {user_id}")
                except Exception as final_error:
                    logger.error(f"❌ Критическая ошибка отправки сообщения: {final_error}")
                    # Последняя попытка с минимальным сообщением
                    error_msg = "Извините, произошла техническая ошибка. Попробуйте позже."
                    await context.bot.send_message(chat_id, error_msg)
                    
                    # 🔥 ВРЕМЕННО ОТКЛЮЧЕНО: Логирование ошибки в базу данных
                    # try:
                    #     asyncio.create_task(
                    #         log_bot_response(
                    #             user_id=user_id,
                    #             chat_id=chat_id,
                    #             response_text=error_msg
                    #         )
                    #     )
                    # except Exception as db_error:
                    #     logger.error(f"Ошибка логирования в БД: {db_error}")
            
        except asyncio.CancelledError:
            # Задача была отменена, это нормально
            logger.info(f"Задача обработки сообщений пользователя {user_id} отменена")
        except Exception as e:
            logger.error(f"❌ Ошибка в process_user_messages: {e}")
            try:
                # Пытаемся отправить сообщение об ошибке
                error_msg = "⚠️ Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
                await context.bot.send_message(chat_id, error_msg)
            except:
                pass
    
    def _analyze_query_structure(self, text: str) -> dict:
        """Анализирует структуру запроса и выделяет все вопросы"""
        # Разбиваем текст на предложения
        sentences = re.split(r'[.!?]+', text)
        questions = []
        
        # Ищем вопросы по ключевым словам и знакам препинания
        question_indicators = [
            '?', 'сколько', 'как', 'что', 'когда', 'почему', 'можно ли',
            'расскажите', 'интересует', 'вопрос', 'подскажите', 'есть ли'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if any(indicator in sentence.lower() for indicator in question_indicators) and len(sentence) > 10:
                questions.append(sentence)
        
        # Если не нашли явных вопросов, разбиваем по темам
        if not questions:
            themes = self._extract_all_themes(text)
            questions = [f"Вопрос про {theme}" for theme in themes]
        
        return {
            'questions_count': len(questions),
            'questions': questions,
            'themes': self._extract_all_themes(text),
            'complexity': self._calculate_complexity_score(text)
        }
    
    def _extract_all_themes(self, text: str) -> list:
        """Извлекает ВСЕ возможные темы из текста"""
        text_lower = text.lower()
        all_possible_themes = []
        
        # Все услуги из конфига
        for service in SALON_CONFIG['services'].keys():
            service_lower = service.lower()
            if any(word in text_lower for word in service_lower.split()):
                all_possible_themes.append(service_lower)
        
        # Общие темы детейлинга
        general_themes = [
            'полировка', 'покраска', 'керамика', 'фары', 'химчистка', 
            'скидка', 'время', 'срок', 'гарантия', 'цена', 'стоимость',
            'диагностика', 'запись', 'pdr', 'вмятины', 'скол', 'царапина',
            'бренд', 'материал', 'технология', 'оплата', 'рассрочка',
            'парковка', 'график', 'режим работы', 'адрес', 'контакты',
            'отзыв', 'рекомендация', 'пример', 'фото', 'результат'
        ]
        
        for theme in general_themes:
            if theme in text_lower:
                all_possible_themes.append(theme)
        
        return list(set(all_possible_themes))  # Убираем дубли
    
    def _calculate_complexity_score(self, text: str) -> int:
        """Рассчитывает сложность запроса от 1 до 5"""
        score = 0
        
        # Длина текста
        if len(text) > 800:
            score += 2
        elif len(text) > 400:
            score += 1
        
        # Количество тем
        themes_count = len(self._extract_all_themes(text))
        if themes_count >= 5:
            score += 2
        elif themes_count >= 3:
            score += 1
        
        # Наличие технических терминов
        technical_terms = ['pdr', 'vin', 'керамик', 'полировка', 'покраск', 'гарантия', 'слои', 'бренд']
        found_terms = sum(1 for term in technical_terms if term in text.lower())
        if found_terms >= 4:
            score += 1
        
        return min(5, max(1, score))
    
    def _create_smart_prompt(self, user_message: str, analysis: dict) -> str:
        """Создает умный промпт на основе анализа запроса"""
        themes_text = ", ".join(analysis['themes'][:8])  # Берем до 8 тем
        
        if analysis['questions_count'] > 0:
            questions_text = "\n".join([f"- {q}" for q in analysis['questions'][:5]])  # Берем до 5 вопросов
            prompt = f"""
Клиент задал сложный запрос с {analysis['questions_count']} вопросами. 
Основные темы: {themes_text}

Конкретные вопросы клиента:
{questions_text}

Ты ОБЯЗАН ответить на КАЖДЫЙ из этих вопросов! Структурируй ответ естественно, группируя похожие темы. 
Давай конкретные цифры, сроки, технологии. Не пропускай ни один вопрос!

Запрос клиента: {user_message}
"""
        else:
            prompt = f"""
Клиент задал развернутый запрос по темам: {themes_text}

Проанализируй ВЕСЬ текст и ответь на все поднятые темы. Давай развернутые ответы с конкретикой.
Используй цены из прайса, упоминай технологии и гарантии.

Запрос клиента: {user_message}
"""
        
        return prompt
    
    def _create_strict_prompt(self, user_message: str, analysis: dict) -> str:
        """Создает строгий промпт для повторной генерации, если ответ был неполным"""
        themes_text = ", ".join(analysis['themes'])
        
        return f"""
ВНИМАНИЕ: Предыдущий ответ был слишком кратким и не охватил все темы!

Клиент ждет ОТВЕТА НА ВСЕ ВОПРОСЫ. Ты пропустил некоторые темы. 

ОБЯЗАТЕЛЬНО ответь на ВСЕ эти темы: {themes_text}

Давай развернутые ответы с:
- Конкретными ценами из прайса
- Технологиями и материалами
- Сроками выполнения работ
- Гарантийными условиями
- Рекомендациями для клиента

Не пропускай ни одной темы! Клиент ждет экспертного ответа.

Запрос клиента: {user_message}
"""
    
    def _check_answer_completeness(self, answer: str, question: str) -> bool:
        """Проверяет, достаточно ли полный ответ на сложный запрос"""
        # Если ответ слишком короткий относительно вопроса
        if len(answer) < len(question) * 0.8:
            return False
        
        # Если в ответе меньше тем, чем в вопросе
        question_themes = len(self._extract_all_themes(question))
        answer_themes = len(self._extract_all_themes(answer))
        
        if answer_themes < question_themes * 0.7:
            return False
        
        return True
    
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
        if not text:
            return False
            
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
                logger.warning(f"⚠️ Обнаружена потенциальная утечка в ответе LLM: {pattern}")
                return False
        
        # Проверяем на наличие НАСТОЯЩИХ конфиденциальных данных (не публичных)
        truly_sensitive_data = [
            config.bot_token,
            config.yandex_api_key,
            config.webhook_secret,
        ]
        
        for data in truly_sensitive_data:
            if data and len(str(data)) > 10 and str(data) in text:
                logger.warning("❌ Обнаружена утечка НАСТОЯЩИХ конфиденциальных данных в ответе LLM")
                return False
        
        return True
    
    async def cleanup_queues(self):
        """Очищает старые очереди сообщений"""
        while True:
            await asyncio.sleep(300)  # Каждые 5 минут
            current_time = time.time()
            async with self.processing_lock:
                # Очищаем пустые очереди
                users_to_remove = []
                for user_id in self.user_message_queues:
                    if not self.user_message_queues[user_id]:
                        users_to_remove.append(user_id)
                
                for user_id in users_to_remove:
                    del self.user_message_queues[user_id]
                    logger.debug(f"Очищена пустая очередь пользователя {user_id}")
                
                # Очищаем завершенные задачи
                tasks_to_remove = []
                for user_id in self.user_processing_tasks:
                    if self.user_processing_tasks[user_id].done():
                        tasks_to_remove.append(user_id)
                
                for user_id in tasks_to_remove:
                    del self.user_processing_tasks[user_id]
                    logger.debug(f"Удалена завершенная задача пользователя {user_id}")

# Глобальный экземпляр менеджера состояния
user_state = UserStateManager()
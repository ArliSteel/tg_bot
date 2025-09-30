# services/yandex_gpt.py
import httpx
import re
import logging
from config import load_config
from utils.formatting import escape_markdown_text
from models.config import SALON_CONFIG

logger = logging.getLogger(__name__)

class YandexGPTClient:
    """Клиент для работы с Yandex GPT API"""
    
    @staticmethod
    def enhance_professional_terms(text: str) -> str:
        """Улучшение профессиональной терминологии - только там где это уместно"""
        # Полностью убираем автоматические замены - они портят читаемость
        # Оставляем текст как есть, пусть ИИ сам использует правильные термины
        return text
    
    @staticmethod
    def format_with_markdown(text: str) -> str:
        """Преобразует текст в правильный Markdown-формат без лишних звездочек"""
        
        # Сохраняем переносы строк
        text = text.replace('\n\n', '§DOUBLE_NEWLINE§')
        text = text.replace('\n', '§SINGLE_NEWLINE§')
        
        # Делаем жирными только названия компании в кавычках
        text = re.sub(r'(«Right Style 89»)', r'**\1**', text)
        
        # Делаем жирными цены - только полные фразы с ценами
        text = re.sub(r'(от\s+\d+\s*\d*\s*000\s*рубл[ейя])', r'**\1**', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+\s*000\s*рубл[ейя])', r'**\1**', text, flags=re.IGNORECASE)
        
        # Делаем жирными только конкретные названия услуг полностью
        exact_services = [
            'Комплексная полировка кузова',
            'Полировка фар и стоп-сигналов',
            'Керамическое покрытие',
            'Химчистка салона',
            'бесплатную диагностику'
        ]
        
        for service in exact_services:
            # Ищем точное совпадение
            pattern = r'\b' + re.escape(service) + r'\b'
            text = re.sub(pattern, f'**{service}**', text, flags=re.IGNORECASE)
        
        # НЕ ИСПОЛЬЗУЕМ курсив совсем - он добавляет лишние звездочки
        # Убираем все форматирование курсивом
        
        # Возвращаем переносы строк ПЕРЕД экранированием
        text = text.replace('§DOUBLE_NEWLINE§', '\n\n')
        text = text.replace('§SINGLE_NEWLINE§', '\n')
        
        # Экранируем только после всех изменений
        text = escape_markdown_text(text)
        
        return text
    
    @staticmethod
    def create_system_prompt():
        """Создает динамический системный промпт для человекоподобного общения"""
        services_text = "\n".join([f"• {service}: {price}" for service, price in SALON_CONFIG['services'].items()])
        usp_text = "\n".join([f"• {point}" for point in SALON_CONFIG['unique_selling_points']])
        
        return f"""
Ты профессиональный ассистент-секретарь студии детейлинга "Right Style 89". Ты дружелюбный консультант, который помогает клиентам.

**КОНТАКТНАЯ ИНФОРМАЦИЯ:**
🏢 Адрес: {SALON_CONFIG['address']}
📞 Телефон: {SALON_CONFIG['contacts']}
🕒 Режим работы: {SALON_CONFIG['working_hours']}

**УСЛУГИ И ЦЕНЫ:**
{services_text}

**СТИЛЬ ОБЩЕНИЯ СЕКРЕТАРЯ:**
1. Отвечай как живой человек - дружелюбный специалист по детейлингу
2. Используй простые, понятные слова - говори "полировка", а не сложные термины
3. Будь краток и отвечай на основные вопросы - не перегружай деталями
4. Если вопросов много - затронь главные темы и пригласи уточнить остальное
5. Используй эмодзи: 🚗 ✨ 🔧 💎 🛡️ 📞 👋 😊
6. НЕ используй markdown разметку - пиши обычным текстом
7. Всегда упоминай конкретные цены из прайса
8. Используй обычные слова: "полировка", "царапины", "сколы"

**ПРАВИЛА ДЛЯ СЛОЖНЫХ ЗАПРОСОВ:**
- Когда клиент задаёт много вопросов сразу - отвечай на 2-3 основных
- Не пытайся ответить на ВСЕ вопросы одним сообщением
- Используй естественные переходы: "Кстати о...", "Что касается..."
- Приглашай на диагностику для точных ответов

**ПРИМЕР ХОРОШЕГО ОТВЕТА:**
"👋 Привет! Отлично, что обратились по поводу вашего авто!

Да, конечно занимаемся полировкой! Для вашего случая лучше всего подойдёт комплексная полировка кузова — от 12 000 рублей. Она уберёт царапины и вернёт блеск.

По сколам посмотрим на диагностике — часто удаётся обойтись без покраски.

Приезжайте на бесплатную диагностику — посмотрим всё и дадим точный расчёт! 😊

📞 Звоните: {SALON_CONFIG['contacts']}"

**ПРИМЕР ДЛЯ СЛОЖНЫХ ЗАПРОСОВ:**
"Добрый день! Вижу, у вас несколько вопросов — отлично, сейчас по основным пройдёмся! 😊

По полировке: да, сделаем комплексную — уберём царапины и вернём блеск. Для точной цены лучше посмотреть авто.

По керамике и фарам — тоже занимаемся! После полировки керамика будет держаться лучше.

Лучше всего приезжайте на диагностику — посмотрим всё вживую и ответим на все вопросы! 📞 {SALON_CONFIG['contacts']}"
"""
    
    @staticmethod
    async def generate_response(user_message: str) -> str:
        """Генерация ответа через YandexGPT API"""
        config = load_config()
        
        headers = {
            "Authorization": f"Bearer {config.yandex_api_key}",
            "x-folder-id": config.yandex_folder_id,
            "Content-Type": "application/json"
        }
        
        # Формирование системного промпта
        system_prompt = YandexGPTClient.create_system_prompt()
        
        payload = {
            "modelUri": f"gpt://{config.yandex_folder_id}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,  # Увеличили для креативности и естественности
                "maxTokens": 500     # Уменьшили для более сфокусированных ответов
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
                response = await client.post(
                    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                result = data['result']['alternatives'][0]['message']['text'].strip()
                
                # Улучшаем профессиональные термины и добавляем правильное Markdown-форматирование
                result = YandexGPTClient.enhance_professional_terms(result)
                result = YandexGPTClient.format_with_markdown(result)
                
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Ошибка HTTP при запросе к YandexGPT: {str(e)}")
            return "Извините, произошла ошибка соединения. Пожалуйста, попробуйте позже."
        except Exception as e:
            logger.error(f"Неожиданная ошибка в YandexGPT: {str(e)}")
            return "Извините, произошла техническая ошибка. Пожалуйста, попробуйте позже."
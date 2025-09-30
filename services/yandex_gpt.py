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
        return text
    
    @staticmethod
    def format_with_markdown(text: str) -> str:
        if not text:
            return ""
            
        text = text.replace('\n\n', '§DOUBLE_NEWLINE§')
        text = text.replace('\n', '§SINGLE_NEWLINE§')
        
        # Минимальное форматирование
        text = re.sub(r'(«Right Style 89»)', r'**\1**', text)
        text = re.sub(r'(от\s+\d+\s*\d*\s*000\s*рубл[ейя])', r'**\1**', text, flags=re.IGNORECASE)
        
        text = text.replace('§DOUBLE_NEWLINE§', '\n\n')
        text = text.replace('§SINGLE_NEWLINE§', '\n')
        
        text = escape_markdown_text(text)
        
        return text
    
    @staticmethod
    def create_system_prompt():
        services_text = "\n".join([f"• {service}: {price}" for service, price in SALON_CONFIG['services'].items()])
        
        return f"""
Ты ассистент студии детейлинга "Right Style 89". Твоя работа - давать ПОЛНЫЕ ответы на ВСЕ вопросы клиентов.

**КОНТАКТЫ:**
📞 {SALON_CONFIG['contacts']}
🏢 {SALON_CONFIG['address']}
🕒 {SALON_CONFIG['working_hours']}

**УСЛУГИ:**
{services_text}

**ЖЕСТКИЕ ПРАВИЛА:**

1. **ОТВЕЧАЙ НА ВСЕ ВОПРОСЫ** - без исключений!
2. **ИСПОЛЬЗУЙ КОНКРЕТИКУ** - цены, сроки, технологии
3. **СТРУКТУРИРУЙ ОТВЕТ** - по темам или по порядку вопросов
4. **НЕ ПРОПУСКАЙ ТЕМЫ** - если клиент спросил про 5 вещей, ответь про все 5

**ПРИМЕР ХОРОШЕГО ОТВЕТА:**
"Добрый день! Отвечу на все ваши вопросы:

1. **Полировка:** Комплексная полировка кузова - 12 000 ₽, убирает царапины и возвращает блеск.

2. **Сколы:** Используем PDR технологию. Если глубокие - локальная покраска с подбором по VIN.

3. **Керамика:** Ceramic Pro, 2-4 слоя, защита 2-5 лет.

4. **Фары:** Полировка фар - 2 500 ₽, результат на 1-2 года.

5. **Химчистка:** Профессиональные средства для кожи, убираем пятна.

6. **Сроки:** Комплекс работ - 2-3 дня. Скидки при заказе нескольких услуг.

Приезжайте на бесплатную диагностику! 📞 {SALON_CONFIG['contacts']}"

**ЕСЛИ ЗАПУТАЕШЬСЯ - ДЕЛАЙ ПРОСТО:**
- Перечисли вопросы клиента
- Дай краткий ответ на каждый
- Упомяни цены и сроки
- Пригласи на диагностику

**НИКОГДА НЕ ДЕЛАЙ ТАК:**
"По некоторым вопросам..." ❌
"Основные моменты..." ❌  
"По полировке..." (и молчи про остальное) ❌
"""

    @staticmethod
    async def generate_response(user_message: str) -> str:
        config = load_config()
        
        headers = {
            "Authorization": f"Bearer {config.yandex_api_key}",
            "x-folder-id": config.yandex_folder_id,
            "Content-Type": "application/json"
        }
        
        system_prompt = YandexGPTClient.create_system_prompt()
        
        # Упрощаем параметры - фокус на полноту, а не креативность
        payload = {
            "modelUri": f"gpt://{config.yandex_folder_id}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,  # Низкая температура для предсказуемости
                "maxTokens": 1200
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt
                },
                {
                    "role": "user", 
                    "text": f"Клиент задал вопросы. ОТВЕТЬ НА ВСЕ без исключения: {user_message}"
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
                
                result = YandexGPTClient.enhance_professional_terms(result)
                result = YandexGPTClient.format_with_markdown(result)
                
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Ошибка HTTP при запросе к YandexGPT: {str(e)}")
            return "Извините, произошла ошибка соединения. Пожалуйста, попробуйте позже."
        except Exception as e:
            logger.error(f"Неожиданная ошибка в YandexGPT: {str(e)}")
            return "Извините, произошла техническая ошибка. Пожалуйста, попробуйте позже."
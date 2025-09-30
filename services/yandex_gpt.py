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
Ты ассистент студии детейлинга "Right Style 89". 

**УСЛУГИ И ЦЕНЫ:**
{services_text}

**КОНТАКТЫ:** {SALON_CONFIG['contacts']}

**ЖЕСТКИЕ ПРАВИЛА ОТВЕТА:**

1. **ОТВЕЧАЙ НА КАЖДЫЙ ВОПРОС** - без исключений!
2. **ИСПОЛЬЗУЙ ТОЧНЫЕ ЦИФРЫ** из прайса выше
3. **НЕ ПРОПУСКАЙ ТЕМЫ** - если клиент спросил про 6 вещей, ответь про все 6
4. **СТРУКТУРИРУЙ ОТВЕТ** четко по темам
5. **УПОМИНАЙ ВСЕ УСЛУГИ** которые есть в прайсе

**ПРИМЕР ИДЕАЛЬНОГО ОТВЕТА:**
"Добрый день! Отвечу на все вопросы:

🚗 **Полировка:** Комплексная полировка кузова - 12 000 ₽

🔧 **Сколы:** Технология PDR, если глубокие - локальная покраска

💎 **Керамика:** Ceramic Pro, 2-4 слоя, 15 000 ₽, защита 2-5 лет

💡 **Фары:** Полировка фар - 2 500 ₽, результат на 1-2 года

🧼 **Химчистка:** Профессиональные средства, 8 000 ₽

⏱ **Сроки:** 2-3 дня, скидки при комплексном заказе

Приезжайте на диагностику! 📞 {SALON_CONFIG['contacts']}"

**ВСЕГДА УПОМИНАЙ ЭТИ УСЛУГИ ЕСЛИ ОНИ ЕСТЬ В ЗАПРОСЕ:**
- Керамическое покрытие (15 000 ₽)
- Полировка фар (2 500 ₽) 
- Химчистка салона (8 000 ₽)
- Сроки работ (2-3 дня)
- Скидки (при комплексном заказе)

**НИКОГДА НЕ ПРОПУСКАЙ:** керамику, фары, химчистку, сроки, скидки!
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
        
        payload = {
            "modelUri": f"gpt://{config.yandex_folder_id}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.2,  # Очень низкая для максимальной предсказуемости
                "maxTokens": 1500
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt
                },
                {
                    "role": "user", 
                    "text": f"Клиент задал вопросы. ОТВЕТЬ НА ВСЕ ТЕМЫ без исключений: {user_message}"
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
import httpx
import re
import logging
from bot.config import load_config
from bot.utils.formatting import escape_markdown_text
from bot.models.config import SALON_CONFIG

logger = logging.getLogger(__name__)
config = load_config()

class YandexGPTClient:
    """Клиент для работы с Yandex GPT API"""
    
    @staticmethod
    def enhance_professional_terms(text: str) -> str:
        """Улучшение профессиональной терминологии в ответах"""
        term_mapping = {
            "покраска": "нанесение ЛКП",
            "царапина": "нарушение целостности ЛКП",
            "скол": " локальное повреждение ЛКП",
            "полировка": "восстановление глянца ЛКП",
            "покрытие": "защитное керамическое покрытие",
            "чистка": "профессиональная химчистка"
        }
        
        for common, professional in term_mapping.items():
            text = text.replace(common, professional)
        
        return text
    
    @staticmethod
    def format_with_markdown(text: str) -> str:
        """Преобразует текст в Markdown-формат для лучшего отображения"""
        # Сначала экранируем весь текст
        text = escape_markdown_text(text)
        
        # Затем добавляем форматирование
        text = re.sub(r'(\d+\.\s+)([^:\n]+:)', r'\1**\2**', text)
        text = re.sub(r'(\d+\.\s+)([^\n]+)', r'\1**\2**', text)
        
        # Добавляем жирный шрифт к подзаголовкам
        text = re.sub(r'([А-Яа-яA-Za-z]+:)', r'**\1**', text)
        
        # Улучшаем форматирование списков
        text = re.sub(r'^(\s*[-•*])\s+', r'• ', text, flags=re.MULTILINE)
        
        return text
    
    @staticmethod
    def create_system_prompt():
        """Создает динамический системный промпт"""
        services_text = "\n".join([f"• {service}: {price}" for service, price in SALON_CONFIG['services'].items()])
        usp_text = "\n".join([f"• {point}" for point in SALON_CONFIG['unique_selling_points']])
        
        return f"""
Ты профессиональный ассистент студии детейлинга "Right Style 89". Ты эксперт в области:
- Восстановления лакокрасочного покрытия (ЛКП)
- Удаления вмятин по технологии PDR
- Керамического покрытия и защитных составов
- Полировки и восстановления оптики
- Антихромирования и чернения деталей
- Химчистки салонов премиум-класса

**КОНТАКТНАЯ ИНФОРМАЦИЯ:**
🏢 Адрес: {SALON_CONFIG['address']}
📞 Телефон: {SALON_CONFIG['contacts']}
🕒 Режим работы: {SALON_CONFIG['working_hours']}
🌐 Соцсети: {', '.join(SALON_CONFIG['social_media'].values())}

**УСЛУГИ И ЦЕНЫ:**
{services_text}

**НАШИ ПРЕИМУЩЕСТВА:**
{usp_text}

**ПРАВИЛА ОБЩЕНИЯ:**
1. Отвечай как живой человек, а не как бот
2. Используй неформальный, но профессиональный стиль общения
3. Можешь использовать разговорные выражения, соответствующие стилю общения автосервиса
4. Иногда можешь делать небольшие опечатки для естественности
5. Отвечай так, как будто ты настоящий специалист по детейлингу
6. Всегда используй Markdown-разметку для форматирования ответов:
   - Заголовки выделяй **жирным текстом**
   - Важные моменты выделяй *курсивом**
   - Используй эмодзи для визуального оформления 🚗✨🔧
   - Списки оформляй с помощью цифр или пунктов

**ВАЖНО:**
- Всегда сохраняй профессиональный тон эксперта детейлинга
- Не придумывай несуществующие услуги или технологии
- При сложных случаях предлагай бесплатную диагностику
- Упоминай гарантию 12 месяцев на работы
- Подчеркивай использование профессиональных материалов
"""
    
    @staticmethod
    async def generate_response(user_message: str) -> str:
        """Генерация ответа через YandexGPT API"""
        headers = {
            "Authorization": f"Bearer {config.YANDEX_API_KEY}",
            "x-folder-id": config.YANDEX_FOLDER_ID,
            "Content-Type": "application/json"
        }
        
        # Формирование системного промпта
        system_prompt = YandexGPTClient.create_system_prompt()
        
        payload = {
            "modelUri": f"gpt://{config.YANDEX_FOLDER_ID}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": 300
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
                
                # Улучшаем профессиональные термины и добавляем Markdown-разметку
                result = YandexGPTClient.enhance_professional_terms(result)
                result = YandexGPTClient.format_with_markdown(result)
                
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Ошибка HTTP при запросе к YandexGPT: {str(e)}")
            return "Извините, произошла ошибка соединения. Пожалуйста, попробуйте позже."
        except Exception as e:
            logger.error(f"Неожиданная ошибка в YandexGPT: {str(e)}")
            return "Извините, произошла техническая ошибка. Пожалуйста, попробуйте позже."
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
        """Улучшение профессиональной терминологии в ответах - только в подходящем контексте"""
        # Более аккуратная замена терминов - только целых слов и в подходящем контексте
        replacements = [
            (r'\bполировк[ауеи]\b', 'восстановление глянца ЛКП'),
            (r'\bцарапин[ауыеи]\b', 'нарушения целостности ЛКП'),
            # Убираем проблематичную замену "скол" - она портит текст
        ]
        
        for pattern, replacement in replacements:
            # Заменяем только если это подходящий контекст
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def format_with_markdown(text: str) -> str:
        """Преобразует текст в правильный Markdown-формат с сохранением структуры"""
        
        # Сохраняем переносы строк и структуру
        text = text.replace('\n\n', '§DOUBLE_NEWLINE§')
        text = text.replace('\n', '§SINGLE_NEWLINE§')
        
        # Делаем жирными важные элементы
        text = re.sub(r'«([^»]+)»', r'**«\1»**', text)  # Названия в кавычках
        
        # Делаем жирными конкретные услуги (более точные паттерны)
        services_patterns = [
            r'(комплексн[ауюыой]\s+[^,\.!]{5,40})',
            r'(полировк[ауе]\s+фар[^,\.!]{5,40})',
            r'(керамическ[оие][емго]\s+покрыти[ея][^,\.!]{5,40})',
            r'(химчистк[ауе]\s+салон[аов][^,\.!]{5,40})'
        ]
        
        for pattern in services_patterns:
            text = re.sub(pattern, r'**\1**', text, flags=re.IGNORECASE)
        
        # Делаем жирными цены (более точный паттерн)
        text = re.sub(r'(от\s+\d+\s*\d*\s*рубл[ейя])', r'**\1**', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+\s*000\s*₽)', r'**\1**', text)
        
        # Делаем курсивными гарантии и важные моменты
        text = re.sub(r'(гарантия[^\.!]{10,50})', r'*\1*', text, flags=re.IGNORECASE)
        text = re.sub(r'(профессиональные материалы)', r'*\1*', text, flags=re.IGNORECASE)
        
        # Возвращаем переносы строк ПЕРЕД экранированием
        text = text.replace('§DOUBLE_NEWLINE§', '\n\n')
        text = text.replace('§SINGLE_NEWLINE§', '\n')
        
        # ВАЖНО: только ПОСЛЕ всех изменений экранируем
        text = escape_markdown_text(text)
        
        return text
    
    @staticmethod
    def create_system_prompt():
        """Создает динамический системный промпт"""
        services_text = "\n".join([f"• {service}: {price}" for service, price in SALON_CONFIG['services'].items()])
        usp_text = "\n".join([f"• {point}" for point in SALON_CONFIG['unique_selling_points']])
        
        return f"""
Ты профессиональный ассистент студии детейлинга "Right Style 89". Ты эксперт в области автомобильного детейлинга.

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
1. Отвечай как живой человек - специалист по детейлингу
2. Используй неформальный, дружелюбный стиль
3. Обязательно используй подходящие эмодзи в ответах: 🚗 ✨ 🔧 💎 🛡️ 📞 👋 😊
4. Структурируй ответ с абзацами и переносами строк для читабельности
5. НЕ используй никакой markdown разметки в ответе - пиши обычным текстом
6. Всегда упоминай конкретные цены из списка услуг
7. Подчеркивай профессионализм и качество

**ВАЖНЫЕ МОМЕНТЫ:**
- Гарантия 12 месяцев на все работы
- Бесплатная диагностика состояния автомобиля
- Используем профессиональные материалы Ceramic Pro, Koch Chemie
- Работаем с премиальными брендами

**СТИЛЬ ОТВЕТА:**
- Начинай дружелюбно с эмодзи
- Отвечай развернуто, но структурированно
- Используй абзацы для разделения информации
- Заканчивай призывом к действию с контактами
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
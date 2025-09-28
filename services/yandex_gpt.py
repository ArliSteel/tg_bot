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
        """Преобразует текст в правильный Markdown-формат"""
        # НЕ экранируем весь текст заранее, работаем с оригинальным
        
        # Сохраняем переносы строк - заменяем двойные переносы на маркеры
        text = text.replace('\n\n', '§DOUBLE_NEWLINE§')
        text = text.replace('\n', '§SINGLE_NEWLINE§')
        
        # Находим фразы в кавычках или после определенных слов и делаем их жирными
        text = re.sub(r'«([^»]+)»', r'**«\1»**', text)
        text = re.sub(r'"([^"]+)"', r'**"\1"**', text)
        
        # Делаем жирными названия услуг и важные термины
        important_terms = [
            'комплексной полировкой кузова', 'отполировать фары', 'керамическое покрытие',
            'химчистка салона', 'удаление вмятин', 'восстановление ЛКП', 'антихром',
            'Right Style 89'
        ]
        
        for term in important_terms:
            # Ищем термин без учета регистра и делаем жирным
            pattern = re.escape(term)
            text = re.sub(f'({pattern})', r'**\1**', text, flags=re.IGNORECASE)
        
        # Делаем жирными цены
        text = re.sub(r'(от \d+[^\s]*₽?)', r'**\1**', text)
        text = re.sub(r'(\d+\s?000\s?₽)', r'**\1**', text)
        text = re.sub(r'(\d+\s?месяцев)', r'**\1**', text)
        
        # Делаем курсивными важные моменты
        text = re.sub(r'(гарантия[^.!]+)', r'*\1*', text, flags=re.IGNORECASE)
        text = re.sub(r'(профессиональные материалы)', r'*\1*', text, flags=re.IGNORECASE)
        
        # Возвращаем переносы строк ПЕРЕД экранированием
        text = text.replace('§DOUBLE_NEWLINE§', '\n\n')
        text = text.replace('§SINGLE_NEWLINE§', '\n')
        
        # ВАЖНО: только ПОСЛЕ форматирования экранируем весь текст
        text = escape_markdown_text(text)
        
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
6. НЕ используй никакой markdown разметки в своих ответах - отвечай обычным текстом
7. Используй эмодзи для визуального оформления 🚗✨🔧

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
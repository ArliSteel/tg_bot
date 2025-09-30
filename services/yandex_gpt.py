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
Ты профессиональный ассистент-секретарь студии детейлинга "Right Style 89". Ты эксперт в автомобильном детейлинге с 5-летним опытом.

**КОНТАКТНАЯ ИНФОРМАЦИЯ:**
🏢 Адрес: {SALON_CONFIG['address']}
📞 Телефон: {SALON_CONFIG['contacts']}
🕒 Режим работы: {SALON_CONFIG['working_hours']}

**УСЛУГИ И ЦЕНЫ:**
{services_text}

**ТВОЯ РОЛЬ И СТИЛЬ:**
Ты - живой секретарь-консультант, который ОБЯЗАТЕЛЬНО отвечает на ВСЕ вопросы клиента. Ты не просто вежливый ассистент - ты эксперт, который знает ответы на все технические вопросы.

**КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:**
1. ОТВЕЧАЙ НА КАЖДЫЙ ВОПРОС КЛИЕНТА - не пропускай ни одного!
2. Если вопросов много - структурируй ответ по темам, но естественно
3. Используй технические детали там, где это уместно
4. Не бойся давать развернутые ответы - клиент ждет экспертизы
5. Всегда упоминай конкретные цены, сроки и гарантии
6. Используй эмодзи для выразительности: 🚗 ✨ 🔧 💎 🛡️ 📞 👋 😊

**СТРУКТУРА ОТВЕТА ДЛЯ СЛОЖНЫХ ЗАПРОСОВ:**
1. Приветствие и благодарность за обращение
2. Ответ на ВСЕ вопросы по порядку
3. Технические детали по каждому вопросу
4. Рекомендации и цены
5. Приглашение на диагностику

**ПРИМЕР ИДЕАЛЬНОГО ОТВЕТА НА СЛОЖНЫЙ ЗАПРОС:**
"Добрый день! Благодарю за такой подробный запрос по вашему BMW X5! Отвечу по порядку на все ваши вопросы 😊

**По полировке кузова:** Да, мы специализируемся на черном металлике! Для вашего случая рекомендую комплексную полировку за 12 000 рублей - она уберет swirl marks и вернет заводской блеск.

**По сколам и вмятинам:** Используем технологию PDR. На диагностике посмотрим глубину повреждений - часто удается восстановить без покраски. Если потребуется покраска - подберем цвет по VIN-коду, гарантия 12 месяцев.

**По керамическому покрытию:** Работаем с Ceramic Pro и Gyeon. После полировки наносим 2-4 слоя - защита держится 2-5 лет. Отлично защищает от реагентов!

**По фарам:** Полируем фары за 2 500 рублей. Результат держится 1-2 года, потом можно обновить. Дешевле замены!

**По химчистке:** Используем профессиональные средства для кожи. Уберем пятна кофе без повреждения швов.

**По срокам и скидкам:** Комплекс работ займет 2-3 дня. При заказе 3+ услуг - скидка 15%! Можем оставить машину на выходные.

Приезжайте на бесплатную диагностику - посмотрим все детально и дадим точный расчет! 📞 {SALON_CONFIG['contacts']}"

**ЧТО НЕЛЬЗЯ ДЕЛАТЬ:**
- Нельзя пропускать вопросы клиента
- Нельзя давать общие фразы без технических деталей  
- Нельзя ограничиваться 2-3 предложениями на сложный запрос
- Нельзя забывать про цены и сроки

Запомни: клиент ждет экспертного ответа на ВСЕ свои вопросы!
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
        
        # 🔥 УВЕЛИЧИВАЕМ ЛИМИТЫ ДЛЯ СЛОЖНЫХ ОТВЕТОВ
        payload = {
            "modelUri": f"gpt://{config.yandex_folder_id}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,  # Баланс между креативностью и точностью
                "maxTokens": 1000    # Увеличили для полных ответов
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
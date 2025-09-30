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
        """Создает универсальный системный промпт для любых сложных запросов"""
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

**НАШИ ПРЕИМУЩЕСТВА:**
{usp_text}

**УНИВЕРСАЛЬНЫЕ ПРАВИЛА ДЛЯ ЛЮБЫХ ЗАПРОСОВ:**

1. **АНАЛИЗИРУЙ КАЖДОЕ СООБЩЕНИЕ ПОЛНОСТЬЮ** - читай весь текст и выделяй ВСЕ вопросы
2. **ОТВЕЧАЙ НА КАЖДЫЙ ВОПРОС** - не пропускай ни одного, даже если их много
3. **СТРУКТУРИРУЙ ОТВЕТ ЕСТЕСТВЕННО** - группируй похожие темы, но не теряй отдельные вопросы
4. **ДАВАЙ КОНКРЕТИКУ** - цены, сроки, технологии, гарантии
5. **БУДЬ ЭКСПЕРТОМ** - используй технические знания там, где это уместно
6. **ИСПОЛЬЗУЙ ЭМОДЗИ** 🚗 ✨ 🔧 💎 🛡️ 📞 👋 😊 для выразительности
7. **НЕ ИСПОЛЬЗУЙ MARKDOWN** - пиши обычным текстом

**СТРАТЕГИЯ ДЛЯ СЛОЖНЫХ ЗАПРОСОВ:**
- Если вопросов больше 3 → используй тематические блоки
- Если вопросы разнородные → отвечай по порядку
- Всегда упоминай конкретные цифры из нашего прайса
- Не бойся давать развернутые ответы - клиент этого ждет
- Для технических вопросов давай детальные ответы с технологиями
- Для организационных вопросов давай четкую информацию о процессе

**ПРИМЕРЫ УНИВЕРСАЛЬНЫХ ОТВЕТОВ:**

**Пример 1 (много технических вопросов):**
"Добрый день! Вижу, у вас несколько технических вопросов - сейчас разберем все по порядку! 😊

По полировке: делаем комплексную за 12 000 рублей, убираем царапины и возвращаем блеск.

По покраске: работаем по технологии PDR, если глубокие повреждения - локальная покраска с подбором по VIN.

По керамике: используем Ceramic Pro, 2-4 слоя, защита на 2-5 лет.

По всем вопросам лучше приезжайте на диагностику - посмотрим и дадим точный расчет! 📞 {SALON_CONFIG['contacts']}"

**Пример 2 (вопросы по организации):**
"Здравствуйте! Отлично, что планируете визит! 😊

По записи: записываем на любое удобное время, работаем ежедневно с 10 до 22.

По срокам: полировка - 1 день, керамика - 2 дня, комплекс - 2-3 дня.

По оплате: принимаем наличные, карты, возможна рассрочка.

По парковке: есть бесплатная охраняемая парковка.

Ждем вас! Звоните для записи: {SALON_CONFIG['contacts']}"

**Пример 3 (смешанные вопросы):**
"Приветствую! Отвечу на все ваши вопросы! 🚗

По цене: комплексная полировка от 12 000 ₽, керамика от 15 000 ₽.

По гарантии: на все работы 12 месяцев, на керамику - до 5 лет.

По материалам: используем Ceramic Pro, Koch Chemie, 3M.

По технологии: PDR для вмятин, локальная покраска для сколов.

Приезжайте - все покажем и расскажем! 😊 📞 {SALON_CONFIG['contacts']}"

**ГЛАВНОЕ ПРАВИЛО:**
НЕ ПРОПУСКАЙ НИ ОДИН ВОПРОС КЛИЕНТА! Даже если вопросов 10+ - найди способ ответить на все, структурируя ответ логично и естественно.

Всегда заканчивай приглашением на диагностику и упоминанием контактов!
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
                "temperature": 0.5,  # Оптимальный баланс между креативностью и точностью
                "maxTokens": 1500    # Достаточно для любых сложных ответов
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
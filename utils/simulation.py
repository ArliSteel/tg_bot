import random
import time
import asyncio

# Не загружаем конфиг на уровне модуля, чтобы избежать ошибок при импорте
# Вместо этого будем загружать внутри функций при необходимости

HUMAN_SIMULATION = {
    "min_typing_delay": 2,
    "max_typing_delay": 8,
    "chars_per_second": 10,
    "typing_variation": 0.3,
    "error_probability": 0.05,
}

def get_config():
    """Ленивая загрузка конфигурации"""
    from config import load_config
    return load_config()

async def simulate_typing(chat_id, context, text_length):
    """Симуляция печатания человека с учетом длины текста"""
    # Расчет времени печатания на основе длины текста
    base_typing_time = text_length / HUMAN_SIMULATION['chars_per_second']
    
    # Добавление вариативности
    variation = base_typing_time * HUMAN_SIMULATION['typing_variation']
    typing_time = base_typing_time + random.uniform(-variation, variation)
    
    # Ограничение минимального и максимального времени
    typing_time = max(HUMAN_SIMULATION['min_typing_delay'], 
                     min(typing_time, HUMAN_SIMULATION['max_typing_delay']))
    
    # Симуляция печатания с обновлением статуса
    start_time = time.time()
    while time.time() - start_time < typing_time:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(4.5)  # Обновляем статус каждые 4.5 секунд (Telegram скрывает через 5)
    
    return typing_time

async def simulate_human_typing_mistakes(text):
    """Добавление случайных опечаток для естественности"""
    if random.random() > HUMAN_SIMULATION['error_probability']:
        return text
    
    # Случайные опечатки
    mistakes = [
        (("о", "а"), 0.3),  # замена о на а и наоборот
        (("е", "и"), 0.2),  # замена е на и и наоборот
        (("с", 'ш'), 0.1),  # замена с на ш и наоборот
        (("."), 0.05),      # пропуск точки
        ((","), 0.05),      # пропуск запятой
    ]
    
    words = text.split()
    if len(words) > 3:
        # Выбираем случайное слово для ошибки (не первое и не последнее)
        word_idx = random.randint(1, len(words) - 2)
        word = words[word_idx]
        
        for chars, prob in mistakes:
            if random.random() < prob and any(c in word for c in chars):
                if len(chars) == 1:
                    # Пропуск символа
                    if chars[0] in word:
                        words[word_idx] = word.replace(chars[0], "", 1)
                        break
                else:
                    # Замена символа
                    from_char, to_char = chars
                    if from_char in word:
                        words[word_idx] = word.replace(from_char, to_char, 1)
                        break
                break
    
    return " ".join(words)

async def simulate_typing_with_errors(chat_id, context, text):
    """Полная симуляция печатания с возможными ошибками и исправлениями"""
    # Первая попытка "печатания"
    typing_time = await simulate_typing(chat_id, context, len(text))
    
    # Случайная "ошибка" и перепечатывание
    if random.random() < HUMAN_SIMULATION['error_probability']:
        await asyncio.sleep(0.5)
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(1.5)
        
        # "Исправление" ошибки
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(1.0)
        
        typing_time += 3.0  # Добавляем время на исправление
    
    return typing_time
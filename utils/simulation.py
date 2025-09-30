import random
import time
import asyncio
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Усовершенствованные настройки человеческого поведения
HUMAN_SIMULATION = {
    # Основные настройки печатания
    "min_typing_delay": 1.5,           # Минимальное время печатания
    "max_typing_delay": 25,            # Максимальное время печатания  
    "base_chars_per_second": 8,        # Базовая скорость печатания
    "expert_chars_per_second": 15,     # Скорость для опытного пользователя
    "thinking_variation": 0.4,         # Вариативность размышлений
    
    # Паузы и перерывы
    "micro_pause_chance": 0.15,        # Вероятность микро-паузы
    "micro_pause_range": (0.3, 1.2),   # Длительность микро-пауз
    "thinking_break_chance": 0.08,     # Вероятность паузы на размышление
    "thinking_break_range": (2, 6),    # Длительность пауз на размышление
    "sentence_break_range": (1, 3),    # Пауза между предложениями
    
    # Опечатки и исправления
    "error_probability": 0.07,         # Вероятность опечатки
    "correction_delay_range": (1, 3),  # Время на исправление ошибки
    
    # Паттерны печатания
    "burst_typing_chance": 0.3,        # Вероятность быстрого набора
    "burst_speed_multiplier": 1.8,     # Множитель скорости в режиме быстрого набора
    "slow_typing_chance": 0.2,         # Вероятность медленного набора
    "slow_speed_multiplier": 0.6,      # Множитель скорости в медленном режиме
}

class HumanTypingSimulator:
    """Продвинутый симулятор человеческого печатания"""
    
    def __init__(self):
        self.config = HUMAN_SIMULATION
    
    def calculate_typing_time(self, text: str) -> float:
        """Рассчитывает реалистичное время печатания на основе текста"""
        if not text:
            return self.config["min_typing_delay"]
        
        # Учитываем сложность текста
        complexity_score = self._calculate_text_complexity(text)
        
        # Базовая скорость с учетом сложности
        base_speed = self.config["base_chars_per_second"] * (1 - complexity_score * 0.3)
        
        # Случайные вариации скорости пользователя
        user_speed_variation = random.uniform(0.8, 1.2)
        effective_speed = base_speed * user_speed_variation
        
        # Время набора без пауз
        base_time = len(text) / effective_speed
        
        # Добавляем время на паузы
        pause_time = self._calculate_pause_time(text, base_time)
        
        total_time = base_time + pause_time
        
        # Ограничиваем минимальное и максимальное время
        return max(
            self.config["min_typing_delay"], 
            min(total_time, self.config["max_typing_delay"])
        )
    
    def _calculate_text_complexity(self, text: str) -> float:
        """Рассчитывает сложность текста (0-1)"""
        complexity = 0.0
        
        # Длинные слова увеличивают сложность
        words = text.split()
        if words:
            avg_word_len = sum(len(word) for word in words) / len(words)
            complexity += min(0.3, (avg_word_len - 5) * 0.1)
        
        # Специальные символы и цифры
        special_chars = sum(1 for char in text if not char.isalnum() and not char.isspace())
        if len(text) > 0:
            complexity += min(0.3, special_chars / len(text) * 10)
        
        # Длинные предложения
        sentences = text.split('.')
        if len(sentences) > 1:
            avg_sentence_len = sum(len(sent) for sent in sentences) / len(sentences)
            complexity += min(0.4, avg_sentence_len / 100)
        
        return min(1.0, complexity)
    
    def _calculate_pause_time(self, text: str, base_time: float) -> float:
        """Рассчитывает время пауз на основе текста"""
        pause_time = 0.0
        
        # Паузы между предложениями
        sentences = [s for s in text.split('.') if s.strip()]
        sentence_pauses = max(0, len(sentences) - 1) * random.uniform(*self.config["sentence_break_range"])
        pause_time += sentence_pauses
        
        # Случайные паузы на размышление
        thinking_pauses = base_time * self.config["thinking_variation"] * random.random()
        pause_time += thinking_pauses
        
        # Микро-паузы (чем длиннее текст, тем больше пауз)
        micro_pauses = (len(text) // 50) * random.uniform(*self.config["micro_pause_range"])
        pause_time += micro_pauses
        
        return pause_time
    
    async def simulate_typing_session(self, chat_id, context, text: str) -> float:
        """Реалистичная симуляция сессии печатания с обновлением статуса"""
        total_time = self.calculate_typing_time(text)
        logger.info(f"Симуляция печатания: {len(text)} символов, {total_time:.2f} секунд")
        
        start_time = time.time()
        elapsed = 0
        
        # Разбиваем текст на логические блоки для симуляции
        typing_blocks = self._split_into_typing_blocks(text)
        
        for i, block in enumerate(typing_blocks):
            block_time = total_time * (len(block) / len(text))
            
            # Симуляция печатания блока
            await self._simulate_typing_block(chat_id, context, block, block_time, i, len(typing_blocks))
            
            elapsed = time.time() - start_time
        
        # Добавляем случайную финальную паузу
        if random.random() < 0.3:
            final_pause = random.uniform(0.5, 2.0)
            await asyncio.sleep(final_pause)
            elapsed += final_pause
        
        return elapsed
    
    def _split_into_typing_blocks(self, text: str) -> List[str]:
        """Разбивает текст на блоки для симуляции печатания"""
        blocks = []
        current_block = ""
        
        # Разбиваем по предложениям и запятым для естественности
        for char in text:
            current_block += char
            
            # Естественные точки разрыва
            if char in '.!?' and len(current_block) > 20:
                blocks.append(current_block)
                current_block = ""
            elif char == ',' and len(current_block) > 15:
                if random.random() < 0.3:  # 30% шанс разрыва на запятой
                    blocks.append(current_block)
                    current_block = ""
        
        # Добавляем остаток
        if current_block:
            blocks.append(current_block)
        
        # Если текст без знаков препинания, разбиваем на равные части
        if len(blocks) == 1 and len(text) > 50:
            chunk_size = max(20, len(text) // random.randint(2, 4))
            blocks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        
        return blocks
    
    async def _simulate_typing_block(self, chat_id, context, block: str, block_time: float, 
                                   block_index: int, total_blocks: int):
        """Симуляция печатания одного блока текста"""
        block_start = time.time()
        
        # Определяем режим печатания для этого блока
        typing_mode = self._get_typing_mode()
        speed_multiplier = self._get_speed_multiplier(typing_mode)
        
        adjusted_block_time = block_time / speed_multiplier
        
        while time.time() - block_start < adjusted_block_time:
            # Показываем статус "печатает"
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            
            # Случайная длительность показа статуса (1-4 секунды)
            status_duration = random.uniform(1, 4)
            
            # Корректируем, если выходим за время блока
            time_left = adjusted_block_time - (time.time() - block_start)
            if status_duration > time_left:
                status_duration = time_left
            
            await asyncio.sleep(status_duration)
            
            # Случайная пауза между показами статуса
            if random.random() < self.config["micro_pause_chance"] and block_index < total_blocks - 1:
                pause_time = random.uniform(*self.config["micro_pause_range"])
                time_left = adjusted_block_time - (time.time() - block_start)
                if pause_time < time_left:
                    await asyncio.sleep(pause_time)
            
            # Пауза на размышление (особенно в середине длинного текста)
            if (random.random() < self.config["thinking_break_chance"] and 
                block_index > 0 and block_index < total_blocks - 1):
                think_time = random.uniform(*self.config["thinking_break_range"])
                time_left = adjusted_block_time - (time.time() - block_start)
                if think_time < time_left:
                    await asyncio.sleep(think_time)
    
    def _get_typing_mode(self) -> str:
        """Определяет режим печатания"""
        rand = random.random()
        if rand < self.config["burst_typing_chance"]:
            return "burst"
        elif rand < self.config["burst_typing_chance"] + self.config["slow_typing_chance"]:
            return "slow"
        else:
            return "normal"
    
    def _get_speed_multiplier(self, mode: str) -> float:
        """Возвращает множитель скорости для режима"""
        multipliers = {
            "burst": self.config["burst_speed_multiplier"],
            "slow": self.config["slow_speed_multiplier"],
            "normal": 1.0
        }
        return multipliers[mode]

# Глобальный экземпляр симулятора
typing_simulator = HumanTypingSimulator()

async def simulate_typing(chat_id, context, text_length: int) -> float:
    """Упрощенная функция для обратной совместимости"""
    # Создаем фиктивный текст нужной длины для расчета времени
    dummy_text = "x" * text_length
    return await typing_simulator.simulate_typing_session(chat_id, context, dummy_text)

async def simulate_human_typing_mistakes(text: str) -> str:
    """Улучшенная симуляция человеческих опечаток"""
    if random.random() > HUMAN_SIMULATION["error_probability"]:
        return text
    
    words = text.split()
    if len(words) < 2:
        return text
    
    # Разные типы опечаток
    mistake_type = random.choice(["substitution", "omission", "transposition", "addition"])
    
    try:
        if mistake_type == "substitution" and len(words) > 3:
            # Замена буквы в случайном слове (не первом и не последнем)
            word_idx = random.randint(1, len(words) - 2)
            word = words[word_idx]
            if len(word) > 2:
                char_idx = random.randint(1, len(word) - 2)
                replacements = {
                    'о': 'а', 'а': 'о', 'е': 'и', 'и': 'е', 
                    'с': 'ш', 'ш': 'с', 'т': 'п', 'п': 'т'
                }
                if word[char_idx] in replacements:
                    new_word = word[:char_idx] + replacements[word[char_idx]] + word[char_idx + 1:]
                    words[word_idx] = new_word
        
        elif mistake_type == "omission" and len(words) > 2:
            # Пропуск символа
            word_idx = random.randint(1, len(words) - 2)
            word = words[word_idx]
            if len(word) > 3:
                char_idx = random.randint(1, len(word) - 2)
                words[word_idx] = word[:char_idx] + word[char_idx + 1:]
        
        elif mistake_type == "transposition" and len(words) > 3:
            # Перестановка соседних букв
            word_idx = random.randint(1, len(words) - 2)
            word = words[word_idx]
            if len(word) > 3:
                char_idx = random.randint(1, len(word) - 2)
                words[word_idx] = word[:char_idx] + word[char_idx + 1] + word[char_idx] + word[char_idx + 2:]
        
        elif mistake_type == "addition" and len(words) > 2:
            # Добавление лишней буквы
            word_idx = random.randint(1, len(words) - 2)
            word = words[word_idx]
            if len(word) > 2:
                char_idx = random.randint(1, len(word) - 1)
                extra_chars = ['е', 'и', 'о', 'а', 'с', 'т']
                words[word_idx] = word[:char_idx] + random.choice(extra_chars) + word[char_idx:]
    
    except Exception as e:
        logger.error(f"Ошибка при симуляции опечатки: {e}")
        # В случае ошибки возвращаем оригинальный текст
    
    return " ".join(words)

async def simulate_typing_with_errors(chat_id, context, text: str) -> float:
    """Полная симуляция печатания с возможными ошибками и исправлениями"""
    # Основное печатание
    typing_time = await typing_simulator.simulate_typing_session(chat_id, context, text)
    
    # Случайное "исправление ошибки"
    if random.random() < HUMAN_SIMULATION["error_probability"]:
        logger.info("Симуляция исправления ошибки...")
        
        # Короткая пауза перед исправлением
        await asyncio.sleep(0.8)
        
        # Показываем "печатает" для исправления
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        correction_time = random.uniform(*HUMAN_SIMULATION["correction_delay_range"])
        await asyncio.sleep(correction_time)
        
        typing_time += 0.8 + correction_time
    
    return typing_time

# Сохраняем старые функции для обратной совместимости
async def simulate_typing_old(chat_id, context, text_length):
    """Старая функция для обратной совместимости"""
    return await simulate_typing(chat_id, context, text_length)
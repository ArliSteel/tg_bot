import re

def escape_markdown_text(text: str) -> str:
    """Экранирует специальные символы MarkdownV2, НО сохраняет форматирование и эмодзи"""
    if not text:
        return ""
    
    # Сначала защищаем уже существующее форматирование
    # Заменяем существующие ** и * на временные маркеры
    text = text.replace('**', '§BOLD§')
    text = text.replace('*', '§ITALIC§')
    
    # Защищаем эмодзи и специальные символы, которые НЕ нужно экранировать
    # Находим и заменяем эмодзи на временные маркеры
    emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]'
    emojis = re.findall(emoji_pattern, text)
    emoji_markers = {}
    
    for i, emoji in enumerate(emojis):
        marker = f'§EMOJI{i}§'
        emoji_markers[marker] = emoji
        text = text.replace(emoji, marker, 1)
    
    # Экранируем только действительно опасные символы для MarkdownV2
    # НО оставляем переносы строк и некоторые другие символы
    escape_chars = r'_[]()~`>+-=|{}!'
    text = re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    
    # Возвращаем обратно форматирование
    text = text.replace('§BOLD§', '**')
    text = text.replace('§ITALIC§', '*')
    
    # Возвращаем эмодзи
    for marker, emoji in emoji_markers.items():
        text = text.replace(marker, emoji)
    
    return text
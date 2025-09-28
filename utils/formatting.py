import re

def escape_markdown_text(text: str) -> str:
    """Экранирует специальные символы MarkdownV2 с максимальной надежностью"""
    if not text:
        return ""
    
    # Сначала защищаем уже существующее форматирование
    text = text.replace('**', '§BOLD§')
    text = text.replace('*', '§ITALIC§')
    
    # Защищаем эмодзи
    emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]'
    emojis = re.findall(emoji_pattern, text)
    emoji_markers = {}
    
    for i, emoji in enumerate(emojis):
        marker = f'§EMOJI{i}§'
        emoji_markers[marker] = emoji
        text = text.replace(emoji, marker, 1)
    
    # Экранируем ВСЕ специальные символы MarkdownV2 по одному
    # Это самый надежный способ
    special_chars = {
        '_': r'\_',
        '[': r'\[',
        ']': r'\]',
        '(': r'\(',
        ')': r'\)',
        '~': r'\~',
        '`': r'\`',
        '>': r'\>',
        '#': r'\#',
        '+': r'\+',
        '-': r'\-',
        '=': r'\=',
        '|': r'\|',
        '{': r'\{',
        '}': r'\}',
        '.': r'\.',
        '!': r'\!'
    }
    
    for char, escaped in special_chars.items():
        text = text.replace(char, escaped)
    
    # Возвращаем форматирование
    text = text.replace('§BOLD§', '**')
    text = text.replace('§ITALIC§', '*')
    
    # Возвращаем эмодзи
    for marker, emoji in emoji_markers.items():
        text = text.replace(marker, emoji)
    
    return text

def validate_markdown(text: str) -> bool:
    """Проверяет, является ли текст корректным MarkdownV2"""
    try:
        # Проверяем основные правила MarkdownV2
        
        # 1. Проверяем парность жирного текста
        bold_matches = re.findall(r'\*\*', text)
        if len(bold_matches) % 2 != 0:
            return False
            
        # 2. Проверяем парность курсива
        italic_matches = re.findall(r'(?<!\*)\*(?!\*)', text)
        if len(italic_matches) % 2 != 0:
            return False
            
        # 3. Проверяем что все спецсимволы экранированы
        unescaped_chars = re.findall(r'(?<!\\)[_\[\]()~`>#+=|{}.!-]', text)
        if unescaped_chars:
            return False
            
        return True
    except:
        return False
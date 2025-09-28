import re

def escape_markdown_text(text: str) -> str:
    """Экранирует специальные символы MarkdownV2 с сохранением эмодзи и структуры"""
    if not text:
        return ""
    
    # Защищаем форматирование
    text = text.replace('**', '§BOLD§')
    text = text.replace('*', '§ITALIC§')
    
    # Защищаем эмодзи более простым способом - они не содержат специальных символов MarkdownV2
    # Поэтому просто не будем их трогать
    
    # Защищаем номера телефонов от неправильного экранирования
    phone_pattern = r'\+7\s?\(\d{3}\)\s?\d{3}-\d{2}-\d{2}'
    phones = re.findall(phone_pattern, text)
    phone_markers = {}
    for i, phone in enumerate(phones):
        marker = f'§PHONE{i}§'
        phone_markers[marker] = phone
        text = text.replace(phone, marker)
    
    # Экранируем только действительно проблемные символы для MarkdownV2
    # Делаем это аккуратно, чтобы не сломать структуру
    replacements = [
        ('_', r'\_'),
        ('[', r'\['),
        (']', r'\]'),
        ('(', r'\('),
        (')', r'\)'),
        ('~', r'\~'),
        ('`', r'\`'),
        ('>', r'\>'),
        ('#', r'\#'),
        ('+', r'\+'),
        ('-', r'\-'),
        ('=', r'\='),
        ('|', r'\|'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('.', r'\.'),
        ('!', r'\!')
    ]
    
    for old, new in replacements:
        text = text.replace(old, new)
    
    # Возвращаем форматирование
    text = text.replace('§BOLD§', '**')
    text = text.replace('§ITALIC§', '*')
    
    # Возвращаем телефоны
    for marker, phone in phone_markers.items():
        text = text.replace(marker, phone)
    
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
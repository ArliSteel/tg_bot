import re

def escape_markdown_text(text: str) -> str:
    """Экранирует специальные символы MarkdownV2, НО сохраняет форматирование"""
    if not text:
        return ""
    
    # Сначала защищаем уже существующее форматирование
    # Заменяем существующие ** и * на временные маркеры
    text = text.replace('**', '§BOLD§')
    text = text.replace('*', '§ITALIC§')
    
    # Экранируем все остальные специальные символы MarkdownV2
    # НО исключаем * которые мы уже обработали
    escape_chars = r'_[]()~`>#+-=|{}.!'
    text = re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    
    # Возвращаем обратно форматирование
    text = text.replace('§BOLD§', '**')
    text = text.replace('§ITALIC§', '*')
    
    return text
import re

def escape_markdown_text(text: str) -> str:
    """Экранирует специальные символы MarkdownV2"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
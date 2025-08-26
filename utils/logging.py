import logging
import sys

def setup_logging(environment="staging"):
    """Настройка логирования для приложения"""
    level = logging.INFO
    
    # Формат логов с указанием окружения
    format_str = f'%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - {environment.upper()} - %(message)s'
    
    # Базовая настройка логирования
    logging.basicConfig(
        level=level,
        format=format_str,
        stream=sys.stdout
    )
    
    # Для продакшена уменьшаем уровень логирования для некоторых библиотек
    if environment == "production":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
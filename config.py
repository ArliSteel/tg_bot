import os
import logging

logger = logging.getLogger(__name__)

class Settings:
    """Настройки приложения из переменных окружения"""
    
    def __init__(self):
        # Читаем переменные окружения напрямую
        self.environment = os.getenv("ENVIRONMENT", "staging")
        self.bot_token = os.getenv("TELEGRAM_TOKEN")
        self.webhook_url = os.getenv("WEBHOOK_URL")
        self.webhook_secret = os.getenv("WEBHOOK_SECRET", "default_secret_token")
        self.yandex_api_key = os.getenv("YANDEX_API_KEY")
        self.yandex_folder_id = os.getenv("YANDEX_FOLDER_ID")
        self.max_requests_per_minute = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "50"))
        self.max_text_length = int(os.getenv("MAX_TEXT_LENGTH", "1000"))
        self.block_duration = int(os.getenv("BLOCK_DURATION", "600"))
        self.warning_threshold = int(os.getenv("WARNING_THRESHOLD", "2"))

def load_config():
    """Загрузка и проверка конфигурации"""
    try:
        config = Settings()
        
        # Отладочная информация
        logger.info("Проверка переменных окружения:")
        logger.info(f"ENVIRONMENT: {config.environment}")
        logger.info(f"TELEGRAM_TOKEN установлен: {bool(config.bot_token)}")
        logger.info(f"WEBHOOK_URL: {config.webhook_url}")
        logger.info(f"WEBHOOK_SECRET установлен: {bool(config.webhook_secret)}")
        logger.info(f"YANDEX_API_KEY установлен: {bool(config.yandex_api_key)}")
        logger.info(f"YANDEX_FOLDER_ID установлен: {bool(config.yandex_folder_id)}")
        
        # Проверка обязательных переменных
        required_vars = [
            ('TELEGRAM_TOKEN', config.bot_token),
            ('YANDEX_API_KEY', config.yandex_api_key),
            ('YANDEX_FOLDER_ID', config.yandex_folder_id)
        ]
        
        missing_vars = [name for name, value in required_vars if not value]
        
        if missing_vars:
            logger.critical(f"Отсутствуют обязательные переменные окружения: {missing_vars}")
            logger.critical("Пожалуйста, установите следующие переменные окружения в Render:")
            logger.critical(" - TELEGRAM_TOKEN: Токен вашего Telegram бота")
            logger.critical(" - YANDEX_API_KEY: API ключ Yandex Cloud")
            logger.critical(" - YANDEX_FOLDER_ID: ID папки Yandex Cloud")
            
            # Дополнительная диагностика
            all_env_vars = dict(os.environ)
            logger.critical("Все переменные окружения:")
            for key, value in all_env_vars.items():
                if any(secret in key.lower() for secret in ['token', 'key', 'secret']):
                    logger.critical(f"  {key}: [СКРЫТО]")
                else:
                    logger.critical(f"  {key}: {value}")
            
            exit(1)
        
        # Маскируем чувствительные данные в логах
        masked_config = {
            'environment': config.environment,
            'bot_token': config.bot_token[:10] + '...' if config.bot_token else None,
            'webhook_url': config.webhook_url,
            'webhook_secret': config.webhook_secret[:10] + '...' if config.webhook_secret else None,
            'yandex_api_key': config.yandex_api_key[:10] + '...' if config.yandex_api_key else None,
            'yandex_folder_id': config.yandex_folder_id,
            'max_requests_per_minute': config.max_requests_per_minute,
            'max_text_length': config.max_text_length,
            'block_duration': config.block_duration,
            'warning_threshold': config.warning_threshold
        }
        
        logger.info(f"Загружена конфигурация: {masked_config}")
        return config
        
    except Exception as e:
        logger.critical(f"Ошибка загрузки конфигурации: {e}")
        logger.critical("Убедитесь, что все обязательные переменные окружения установлены в Render:")
        logger.critical("TELEGRAM_TOKEN, YANDEX_API_KEY, YANDEX_FOLDER_ID")
        exit(1)
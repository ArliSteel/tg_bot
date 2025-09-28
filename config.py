import os
import logging
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""
    
    environment: str = Field("staging", env="ENVIRONMENT")
    bot_token: str = Field(..., env="TELEGRAM_TOKEN")
    webhook_url: str = Field(..., env="WEBHOOK_URL")
    webhook_secret: str = Field("default_secret_token", env="WEBHOOK_SECRET")
    yandex_api_key: str = Field(..., env="YANDEX_API_KEY")
    yandex_folder_id: str = Field(..., env="YANDEX_FOLDER_ID")
    max_requests_per_minute: int = Field(200, env="MAX_REQUESTS_PER_MINUTE")
    max_text_length: int = Field(4000, env="MAX_TEXT_LENGTH")
    block_duration: int = Field(3600, env="BLOCK_DURATION")
    warning_threshold: int = Field(5, env="WARNING_THRESHOLD")
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Игнорировать лишние переменные

def load_config():
    """Загрузка и проверка конфигурации"""
    try:
        config = Settings()
        
        # Проверка обязательных переменных
        required_vars = ['bot_token', 'yandex_api_key', 'yandex_folder_id']
        missing_vars = [key for key in required_vars if not getattr(config, key)]
        
        if missing_vars:
            logger.critical(f"Отсутствуют обязательные переменные окружения: {missing_vars}")
            logger.critical("Пожалуйста, установите следующие переменные окружения:")
            logger.critical(" - TELEGRAM_TOKEN: Токен вашего Telegram бота")
            logger.critical(" - YANDEX_API_KEY: API ключ Yandex Cloud")
            logger.critical(" - YANDEX_FOLDER_ID: ID папки Yandex Cloud")
            exit(1)
        
        # Маскируем чувствительные данные в логах
        masked_config = config.dict()
        for key in ['bot_token', 'yandex_api_key', 'webhook_secret']:
            if masked_config[key]:
                masked_config[key] = masked_config[key][:10] + '...'
        
        logger.info(f"Загружена конфигурация: {masked_config}")
        return config
        
    except Exception as e:
        logger.critical(f"Ошибка загрузки конфигурации: {e}")
        logger.critical("Убедитесь, что все обязательные переменные окружения установлены:")
        logger.critical("TELEGRAM_TOKEN, YANDEX_API_KEY, YANDEX_FOLDER_ID")
        exit(1)
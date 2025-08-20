# Используем официальный Python образ на основе Alpine для минимального размера
FROM python:3.11-alpine3.18

# Устанавливаем метаданные
LABEL maintainer="Your Name <your.email@example.com>"
LABEL description="Telegram Bot for Car Detailing Studio"
LABEL version="1.0"

# Устанавливаем системные зависимости (минимальный набор)
RUN apk update && \
    apk add --no-cache \
    ffmpeg \
    libffi \
    libsndfile \
    # Временные зависимости для сборки
    build-base \
    libffi-dev \
    alsa-lib-dev \
    && rm -rf /var/cache/apk/*

# Создаем непривилегированного пользователя для безопасности
RUN adduser -D -u 1000 botuser

# Работа в директории /app
WORKDIR /app

# Сначала копируем только requirements.txt для лучшего кэширования
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Удаляем временные зависимости сборки
    apk del build-base libffi-dev alsa-lib-dev

# Копируем исходный код
COPY --chown=botuser:botuser . .

# Переключаемся на непривилегированного пользователя
USER botuser

# Экспонируем порт 10000
EXPOSE 10000

# Переменные окружения для оптимизации Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Используем более эффективный менеджер процессов для production
CMD ["python", "-u", "bot.py"]
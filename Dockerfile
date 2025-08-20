FROM python:3.11-alpine3.18

# Устанавливаем только необходимые системные зависимости
RUN apk update && \
    apk add --no-cache \
    ffmpeg \
    libsndfile \
    # Временные зависимости для сборки
    build-base \
    libffi-dev \
    alsa-lib-dev \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Копируем и устанавливаем зависимости сначала для лучшего кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Удаляем временные зависимости сборки
    apk del build-base libffi-dev alsa-lib-dev

# Копируем исходный код
COPY . .

# Создаем непривилегированного пользователя
RUN adduser -D -u 1000 botuser
USER botuser

EXPOSE 10000

# Оптимизация для Python в контейнере
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

CMD ["python", "-u", "bot.py"]
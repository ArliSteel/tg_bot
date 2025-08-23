FROM python:3.11-slim-bullseye

# Устанавливаем системные зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем непривилегированного пользователя и группу заранее
RUN groupadd -r botuser && useradd -r -g botuser -d /app -s /sbin/nologin botuser

WORKDIR /app

# Копируем и устанавливаем зависимости сначала для лучшего кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Меняем владельца файлов
RUN chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

EXPOSE 10000

# Оптимизация для Python в контейнере
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    PYTHONTRACEMALLOC=0 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    ENVIRONMENT=production

# Здоровье контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:10000/health || exit 1

# Используем exec форму для корректной обработки сигналов
CMD ["python", "-u", "bot.py"]
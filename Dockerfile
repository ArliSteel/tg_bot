FROM python:3.11-slim-bullseye

# Устанавливаем системные зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем зависимости сначала для лучшего кэширования
COPY requirements.txt .

# Показываем содержимое requirements.txt для отладки
RUN echo "=== Requirements.txt content ===" && \
    cat requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Проверяем структуру проекта
RUN echo "=== Project structure ===" && \
    find . -name "*.py" | head -20

EXPOSE 10000

# Оптимизация для Python в контейнере
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Здоровье контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:10000/health || exit 1

# Запускаем main.py напрямую
CMD ["python", "-u", "main.py"]
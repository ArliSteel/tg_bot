FROM python:3.11-slim-bullseye

# Устанавливаем системные зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем зависимости сначала для лучшего кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Проверяем структуру проекта (для отладки)
RUN echo "=== Project structure ===" && \
    find . -name "*.py" | sort && \
    echo "=== Bot directory ===" && \
    ls -la bot/ && \
    echo "=== Bot main.py ===" && \
    test -f bot/main.py && echo "✅ Bot main.py exists" || echo "❌ Bot main.py missing"

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

# Используем exec форму для корректной обработки сигналов
CMD ["python", "-u", "app.py"]
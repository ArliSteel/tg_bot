FROM python:3.11-slim

# Установка зависимостей ОС
RUN apt-get update && \
    apt-get install -y ffmpeg gcc libffi-dev libsndfile1 && \
    apt-get clean

# Установка зависимостей Python
WORKDIR /app
COPY . .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Экспонируем порт (Render ожидает, что слушается 10000)
EXPOSE 10000

# ⬇️ Важно: запуск именно aiohttp-сервера
CMD ["python", "bot.py"]

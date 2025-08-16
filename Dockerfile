FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && \
    apt-get install -y ffmpeg gcc libffi-dev libsndfile1 && \
    apt-get clean

# Работаем в директории /app
WORKDIR /app
COPY . .

# Установка Python-зависимостей
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Экспонируем порт Render (10000)
EXPOSE 10000

# Запуск бота
CMD ["python", "bot.py"]

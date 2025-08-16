FROM python:3.11-slim

# Установка зависимостей ОС
RUN apt-get update && \
    apt-get install -y ffmpeg gcc libffi-dev libsndfile1 && \
    apt-get clean

# Работа в директории /app
WORKDIR /app
COPY . .

# Установка зависимостей Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Экспонируем порт 10000 (Render ожидает именно этот порт)
EXPOSE 10000

# Запуск бота
CMD ["python", "bot.py"]

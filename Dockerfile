# Используем официальный Python-образ
FROM python:3.11-slim

# Устанавливаем зависимости системы, включая ffmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg gcc libffi-dev libsndfile1 && \
    apt-get clean

# Создаём рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Устанавливаем Python-зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Указываем порт, который будет слушать приложение
EXPOSE 10000

# Команда для запуска бота
CMD ["python", "bot.py"]

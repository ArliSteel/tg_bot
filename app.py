#!/usr/bin/env python3
"""
Главный файл приложения для запуска бота
"""
import os
import sys

# Добавляем текущую директорию в путь поиска модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Для отладки - выводим информацию о путях
print(f"Current directory: {current_dir}")
print(f"Python path: {sys.path}")

try:
    # Проверяем существование модуля
    if not os.path.exists(os.path.join(current_dir, 'bot')):
        raise ImportError("Bot directory not found")
    
    if not os.path.exists(os.path.join(current_dir, 'bot', 'main.py')):
        raise ImportError("Bot main.py not found")
    
    # Импортируем и запускаем основное приложение
    from bot.main import main
    print("✅ Bot module imported successfully")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📁 Files in current directory:")
    for file in os.listdir(current_dir):
        print(f"   - {file}")
    if os.path.exists(os.path.join(current_dir, 'bot')):
        print("📁 Files in bot directory:")
        for file in os.listdir(os.path.join(current_dir, 'bot')):
            print(f"   - {file}")
    sys.exit(1)

if __name__ == "__main__":
    main()
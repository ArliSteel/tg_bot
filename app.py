#!/usr/bin/env python3
"""
Главный файл приложения для запуска бота
"""
import os
import sys

# Добавляем текущую директорию в путь поиска модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print(f"Current directory: {current_dir}")
print(f"Python path: {sys.path}")
print("Files in current directory:", os.listdir('.'))

try:
    # Проверяем существование основных модулей
    required_dirs = ['handlers', 'models', 'services', 'utils']
    for dir_name in required_dirs:
        if not os.path.exists(os.path.join(current_dir, dir_name)):
            raise ImportError(f"Directory {dir_name} not found")
    
    # Импортируем и запускаем основное приложение из main.py
    from main import main
    print("✅ Main module imported successfully")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📁 Detailed directory structure:")
    for root, dirs, files in os.walk('.'):
        level = root.replace('.', '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            if file.endswith('.py'):
                print(f"{subindent}{file}")
    sys.exit(1)

if __name__ == "__main__":
    main()
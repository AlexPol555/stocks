#!/usr/bin/env python3
"""Load environment variables from .env file."""

import os
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ Файл .env не найден!")
        print("Создайте файл .env в корне проекта с содержимым:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        print("TELEGRAM_CHAT_ID=your_chat_id_here")
        return False
    
    print("✅ Файл .env найден")
    
    # Load .env file
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                print(f"✅ Загружено: {key}")
    
    return True

if __name__ == "__main__":
    print("🔧 Загрузка переменных окружения из .env файла")
    print("=" * 50)
    
    if load_env_file():
        print("\n✅ Переменные окружения загружены!")
        
        # Check if required variables are set
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        print(f"\nBot Token: {'✅ Установлен' if bot_token else '❌ Не установлен'}")
        print(f"Chat ID: {'✅ Установлен' if chat_id else '❌ Не установлен'}")
        
        if bot_token and chat_id:
            print("\n🎉 Все готово! Теперь можно тестировать Telegram Bot")
        else:
            print("\n⚠️ Установите TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в файле .env")
    else:
        print("\n❌ Не удалось загрузить переменные окружения")

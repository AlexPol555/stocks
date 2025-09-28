#!/usr/bin/env python3
"""Test script for Telegram Bot setup."""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_env_file():
    """Load environment variables from .env file."""
    env_file = Path(".env")
    
    if env_file.exists():
        print("📁 Загружаем переменные из .env файла...")
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Переменные из .env загружены")
        return True
    else:
        print("⚠️ Файл .env не найден, используем системные переменные")
        return False

async def test_telegram_setup():
    """Test Telegram Bot setup."""
    print("🤖 Testing Telegram Bot Setup")
    print("=" * 50)
    
    # Check environment variables
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    print(f"Bot Token: {'✅ Set' if bot_token else '❌ Not set'}")
    print(f"Chat ID: {'✅ Set' if chat_id else '❌ Not set'}")
    
    if not bot_token:
        print("\n❌ TELEGRAM_BOT_TOKEN not found!")
        print("Please set it using:")
        print("  Windows: $env:TELEGRAM_BOT_TOKEN=\"your_token\"")
        print("  Linux/Mac: export TELEGRAM_BOT_TOKEN=\"your_token\"")
        return False
    
    if not chat_id:
        print("\n❌ TELEGRAM_CHAT_ID not found!")
        print("Please set it using:")
        print("  Windows: $env:TELEGRAM_CHAT_ID=\"your_chat_id\"")
        print("  Linux/Mac: export TELEGRAM_CHAT_ID=\"your_chat_id\"")
        return False
    
    # Test Telegram notifier
    try:
        from core.notifications import TelegramNotifier
        
        print("\n🔧 Creating TelegramNotifier...")
        notifier = TelegramNotifier()
        
        if not notifier.enabled:
            print("❌ TelegramNotifier is disabled!")
            print("Check your bot token and chat ID")
            return False
        
        print("✅ TelegramNotifier created successfully")
        
        # Test connection
        print("\n🔍 Testing connection...")
        success = await notifier.test_connection()
        
        if success:
            print("✅ Telegram connection test successful!")
            print("🎉 Your Telegram Bot is working correctly!")
            return True
        else:
            print("❌ Telegram connection test failed!")
            print("Check your bot token and chat ID")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install dependencies: pip install python-telegram-bot aiohttp")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def show_setup_instructions():
    """Show setup instructions."""
    print("\n📋 Setup Instructions:")
    print("=" * 50)
    print("1. Create a bot with @BotFather")
    print("2. Get your Chat ID from @userinfobot")
    print("3. Set environment variables:")
    print("   Windows: $env:TELEGRAM_BOT_TOKEN=\"your_token\"")
    print("   Linux/Mac: export TELEGRAM_BOT_TOKEN=\"your_token\"")
    print("4. Run this script again to test")

async def main():
    """Main function."""
    # Load .env file first
    load_env_file()
    
    success = await test_telegram_setup()
    
    if not success:
        show_setup_instructions()
        sys.exit(1)
    else:
        print("\n✨ Telegram Bot is ready to use!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())

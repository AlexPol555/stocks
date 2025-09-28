@echo off
echo Installing Telegram Bot dependencies...
pip install python-telegram-bot aiohttp psutil
echo.
echo Dependencies installed!
echo.
echo Now set your environment variables:
echo   set TELEGRAM_BOT_TOKEN=your_bot_token_here
echo   set TELEGRAM_CHAT_ID=your_chat_id_here
echo.
echo Then run: python test_telegram_setup.py
pause

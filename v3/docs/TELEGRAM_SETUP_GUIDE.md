# Полное руководство по настройке Telegram Bot

## 📋 Пошаговая инструкция

### Шаг 1: Создание бота в Telegram

1. **Откройте Telegram** и найдите [@BotFather](https://t.me/BotFather)
2. **Отправьте команду** `/newbot`
3. **Введите имя бота** (например: "Stock Trading Notifications")
4. **Введите username бота** (например: "stock_trading_bot")
5. **Скопируйте токен** - он выглядит так: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### Шаг 2: Получение Chat ID

1. **Найдите [@userinfobot](https://t.me/userinfobot)** в Telegram
2. **Отправьте ему любое сообщение** (например: "Hello")
3. **Скопируйте ваш Chat ID** - это число вида `123456789`

### Шаг 3: Создание файла .env

Создайте файл `.env` в корне проекта (рядом с `app.py`) со следующим содержимым:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
TELEGRAM_CHAT_ID=ваш_chat_id_от_userinfobot

# Другие настройки (опционально)
STOCKS_DB_PATH=stock_data.db
STOCKS_ENV=development
```

**Пример:**
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

### Шаг 4: Установка зависимостей

Установите необходимые библиотеки:

```bash
pip install python-telegram-bot aiohttp psutil
```

Или используйте готовый скрипт:
```bash
python install_telegram_deps.bat
```

### Шаг 5: Тестирование настройки

Запустите тестовый скрипт:

```bash
python test_telegram_setup.py
```

Если все настроено правильно, вы увидите:
```
🤖 Testing Telegram Bot Setup
==================================================
📁 Загружаем переменные из .env файла...
✅ Переменные из .env загружены
Bot Token: ✅ Set
Chat ID: ✅ Set
🔧 Creating TelegramNotifier...
✅ TelegramNotifier created successfully
🔍 Testing connection...
✅ Telegram connection test successful!
🎉 Your Telegram Bot is working correctly!
✨ Telegram Bot is ready to use!
```

## 🔧 Альтернативные способы настройки

### Способ 1: Переменные окружения системы

Вместо файла `.env` можно установить переменные в системе:

**Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN="ваш_токен"
$env:TELEGRAM_CHAT_ID="ваш_chat_id"
```

**Windows (Command Prompt):**
```cmd
set TELEGRAM_BOT_TOKEN=ваш_токен
set TELEGRAM_CHAT_ID=ваш_chat_id
```

**Linux/Mac:**
```bash
export TELEGRAM_BOT_TOKEN="ваш_токен"
export TELEGRAM_CHAT_ID="ваш_chat_id"
```

### Способ 2: Через конфигурационный файл

Можно настроить через `config/notifications.yml`:

```yaml
telegram:
  enabled: true
  bot_token: "ваш_токен"
  chat_id: "ваш_chat_id"
```

## 🧪 Тестирование в приложении

После настройки:

1. **Запустите приложение:**
   ```bash
   streamlit run app.py
   ```

2. **Откройте страницу "14_🔍_System_Monitoring"**

3. **Нажмите "🔔 Тест уведомлений"**

4. **Проверьте статус** в разделе "Уведомления"

## 📱 Примеры уведомлений

После настройки вы получите уведомления такого вида:

### Сигнал торговли:
```
📊 Сигнал Adaptive Buy
🟠 14:30:25 | 15.01.2024

🟢 AAPL: ПОКУПКА по цене 150.25

📋 Детали:
• ticker: AAPL
• signal_type: Adaptive Buy
• price: 150.25
• signal_value: 1
```

### Ошибка системы:
```
❌ Ошибка в Database
🟡 14:31:10 | 15.01.2024

Database Error: Connection failed

📋 Детали:
• error_type: Database Error
• component: Database
• error_message: Connection failed
```

### Критическое событие:
```
🚨 КРИТИЧЕСКОЕ СОБЫТИЕ: System Failure
🔴 14:32:00 | 15.01.2024

Database is down

📋 Детали:
• critical_type: System Failure
```

## ❓ Устранение неполадок

### Проблема: "Bot Token: ❌ Not set"
**Решение:**
- Проверьте, что файл `.env` создан в корне проекта
- Убедитесь, что в файле есть строка `TELEGRAM_BOT_TOKEN=ваш_токен`
- Проверьте, что токен скопирован полностью

### Проблема: "Chat ID: ❌ Not set"
**Решение:**
- Получите Chat ID через @userinfobot
- Добавьте в `.env` файл: `TELEGRAM_CHAT_ID=ваш_chat_id`

### Проблема: "Telegram connection test failed"
**Решение:**
- Проверьте интернет-соединение
- Убедитесь, что токен правильный
- Проверьте, что Chat ID правильный
- Убедитесь, что бот не заблокирован

### Проблема: "ImportError: No module named 'telegram'"
**Решение:**
```bash
pip install python-telegram-bot aiohttp psutil
```

### Проблема: "Failed to send Telegram notification"
**Решение:**
- Проверьте, что бот добавлен в чат
- Убедитесь, что Chat ID правильный
- Проверьте права бота на отправку сообщений

## 🔒 Безопасность

- **Никогда не публикуйте** токен бота в открытом доступе
- **Добавьте `.env` в `.gitignore`** (уже добавлен)
- **Используйте переменные окружения** в продакшене
- **Регулярно обновляйте** токен бота при необходимости

## 📚 Дополнительные ресурсы

- [Документация python-telegram-bot](https://python-telegram-bot.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [@BotFather](https://t.me/BotFather) - создание ботов
- [@userinfobot](https://t.me/userinfobot) - получение Chat ID

## ✅ Проверочный список

- [ ] Создан бот через @BotFather
- [ ] Получен токен бота
- [ ] Получен Chat ID через @userinfobot
- [ ] Создан файл `.env` с правильными значениями
- [ ] Установлены зависимости (`python-telegram-bot`, `aiohttp`, `psutil`)
- [ ] Запущен тест `python test_telegram_setup.py`
- [ ] Тест прошел успешно
- [ ] Проверен статус в приложении

После выполнения всех пунктов ваш Telegram Bot будет готов к работе! 🎉

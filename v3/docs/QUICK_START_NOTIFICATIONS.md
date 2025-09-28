# Быстрый старт: Система уведомлений

## Установка

### 1. Установите зависимости
```bash
pip install python-telegram-bot aiohttp psutil
```

### 2. Настройте Telegram Bot (опционально)
```bash
# Создайте бота через @BotFather в Telegram
# Получите токен и Chat ID
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

## Использование

### Базовые уведомления

```python
from core.notifications import notify_signal, notify_error, notify_critical

# Уведомление о сигнале
await notify_signal(
    ticker="AAPL",
    signal_type="Adaptive Buy", 
    price=150.25,
    signal_value=1
)

# Уведомление об ошибке
await notify_error(
    error_type="Database Error",
    error_message="Connection failed",
    component="Database"
)

# Критическое уведомление
await notify_critical(
    critical_type="System Failure",
    message="Database is down"
)
```

### Dashboard уведомления

```python
from core.notifications import dashboard_alerts

# Добавить уведомление в dashboard
dashboard_alerts.add_signal_alert(
    ticker="AAPL",
    signal_type="Buy Signal",
    price=150.25,
    signal_value=1
)

# Получить статистику
stats = dashboard_alerts.get_notification_stats()
print(f"Уведомлений: {stats['total']}, непрочитанных: {stats['unread']}")
```

### Мониторинг системы

```python
from core.notifications import notification_manager

# Запустить health checks
health_results = await notification_manager.run_health_checks()

# Собрать метрики
metrics = await notification_manager.collect_and_analyze_metrics()

# Получить статус
status = notification_manager.get_status()
```

## Интерфейс

### Страницы в приложении:
- **Dashboard** - бейдж уведомлений в сайдбаре
- **13_🔔_Notifications** - управление уведомлениями
- **14_🔍_System_Monitoring** - мониторинг системы

### Типы уведомлений:
1. **Сигналы торговли** - уведомления о торговых сигналах
2. **Ошибки системы** - уведомления об ошибках
3. **Критические события** - критические алерты
4. **Выполненные сделки** - уведомления о сделках
5. **Ежедневные отчеты** - ежедневные сводки
6. **Health checks** - проверки состояния системы

## Конфигурация

Настройте `config/notifications.yml`:

```yaml
telegram:
  enabled: true
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${TELEGRAM_CHAT_ID}"

dashboard:
  enabled: true
  max_notifications: 100

health_checks:
  enabled: true
  interval_minutes: 5
```

## Тестирование

Запустите пример:
```bash
python examples/notifications_example.py
```

Или протестируйте в приложении:
1. Откройте страницу "14_🔍_System_Monitoring"
2. Нажмите "🔔 Тест уведомлений"
3. Проверьте страницу "13_🔔_Notifications"

## Устранение неполадок

### Telegram не работает
- Проверьте токен бота и Chat ID
- Убедитесь, что бот добавлен в чат
- Проверьте интернет-соединение

### Dashboard уведомления не отображаются
- Убедитесь, что `dashboard_alerts` импортирован
- Проверьте, что уведомления добавляются в session state

### Health checks не работают
- Проверьте права доступа к файлам
- Убедитесь, что psutil установлен
- Проверьте подключение к базе данных

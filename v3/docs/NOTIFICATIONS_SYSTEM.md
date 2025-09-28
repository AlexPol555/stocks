# Система уведомлений и мониторинга

## Обзор

Система уведомлений предоставляет многоуровневую систему уведомлений и мониторинга состояния системы, включающую:

- **Telegram Bot** - уведомления через Telegram
- **Dashboard Alerts** - визуальные уведомления в интерфейсе
- **System Monitoring** - health checks и метрики производительности
- **Message Formatting** - унифицированное форматирование сообщений

## Архитектура

```
core/notifications/
├── __init__.py              # Основной модуль
├── message_formatter.py     # Форматирование сообщений
├── telegram_bot.py         # Telegram Bot
├── dashboard_alerts.py     # Dashboard уведомления
├── integration.py          # Интеграция с системой
└── monitoring/             # Мониторинг системы
    ├── __init__.py
    ├── health_checks.py    # Health checks
    └── metrics.py          # Сбор метрик
```

## Установка и настройка

### 1. Установка зависимостей

```bash
pip install python-telegram-bot aiohttp psutil
```

### 2. Настройка Telegram Bot

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен бота
3. Узнайте Chat ID (можно использовать [@userinfobot](https://t.me/userinfobot))
4. Установите переменные окружения:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

### 3. Конфигурация

Настройте файл `config/notifications.yml`:

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

## Использование

### Базовое использование

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

### Расширенное использование

```python
from core.notifications import notification_manager

# Получить статус системы
status = notification_manager.get_status()

# Запустить health checks
health_results = await notification_manager.run_health_checks()

# Собрать метрики
metrics = await notification_manager.collect_and_analyze_metrics()

# Отправить ежедневный отчет
report_data = {
    "total_signals": 15,
    "trades_executed": 3,
    "profit_loss": 1250.50,
    "active_positions": 5
}
await notification_manager.send_daily_report(report_data)
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

# Очистить старые уведомления
dashboard_alerts.cleanup_old_notifications(hours=24)
```

## Типы уведомлений

### 1. Сигналы торговли
- **Тип**: `NotificationType.SIGNAL`
- **Приоритет**: Высокий (3)
- **Каналы**: Dashboard, Telegram
- **Данные**: тикер, тип сигнала, цена, значение сигнала

### 2. Ошибки системы
- **Тип**: `NotificationType.ERROR`
- **Приоритет**: Средний (2)
- **Каналы**: Dashboard, Telegram
- **Данные**: тип ошибки, сообщение, компонент

### 3. Критические события
- **Тип**: `NotificationType.CRITICAL`
- **Приоритет**: Критический (4)
- **Каналы**: Dashboard, Telegram
- **Особенности**: обходит rate limiting

### 4. Выполненные сделки
- **Тип**: `NotificationType.TRADE_EXECUTED`
- **Приоритет**: Высокий (3)
- **Каналы**: Dashboard, Telegram
- **Данные**: тикер, сторона, количество, цена, сумма

### 5. Ежедневные отчеты
- **Тип**: `NotificationType.DAILY_REPORT`
- **Приоритет**: Низкий (1)
- **Каналы**: Dashboard, Telegram
- **Расписание**: 09:00 ежедневно

### 6. Health checks
- **Тип**: `NotificationType.HEALTH_CHECK`
- **Приоритет**: Низкий (1) / Средний (2)
- **Каналы**: Dashboard, Telegram
- **Особенности**: только при проблемах

## Health Checks

Система автоматически проверяет состояние компонентов:

### 1. База данных
- Подключение к БД
- Выполнение тестовых запросов
- Проверка существования таблиц
- Размер файла БД

### 2. Дисковое пространство
- Доступное место на диске
- Пороги предупреждения (85%) и критический (95%)

### 3. Память
- Использование оперативной памяти
- Пороги предупреждения (85%) и критический (95%)

### 4. Процесс
- Статус процесса
- Использование CPU
- Использование памяти процессом
- Количество потоков

## Метрики системы

### Собираемые метрики

1. **Системные метрики**:
   - CPU usage (%)
   - Memory usage (%)
   - Disk usage (%)
   - Process metrics

2. **Метрики приложения**:
   - Размер базы данных
   - Количество активных сигналов
   - Количество сделок за день
   - Использование памяти процессом

### Алерты на основе метрик

- **CPU > 90%**: Критический алерт
- **CPU > 80%**: Предупреждение
- **Memory > 95%**: Критический алерт
- **Memory > 85%**: Предупреждение
- **Disk > 95%**: Критический алерт
- **Disk > 85%**: Предупреждение
- **Process Memory > 1GB**: Предупреждение

## Интерфейс пользователя

### Dashboard
- Бейдж уведомлений в сайдбаре
- Панель уведомлений в основном интерфейсе
- Отображение последних 5 уведомлений

### Страница уведомлений (`pages/13_🔔_Notifications.py`)
- Полный список уведомлений
- Фильтрация по типу и статусу
- Массовые операции (отметить все, очистить)
- Статистика уведомлений

### Страница мониторинга (`pages/14_🔍_System_Monitoring.py`)
- Health checks
- Метрики системы
- Тестирование уведомлений
- Статус системы

## Интеграция с существующей системой

### Автоматические уведомления

Система автоматически интегрируется с:

1. **Торговыми сигналами** - уведомления при генерации сигналов
2. **Выполнением сделок** - уведомления о сделках в демо-режиме
3. **Ошибками системы** - уведомления об ошибках в компонентах
4. **Health checks** - периодические проверки состояния

### Ручная интеграция

```python
# В коде анализатора
from core.notifications import notify_signal

# При генерации сигнала
if signal_generated:
    await notify_signal(
        ticker=ticker,
        signal_type="Adaptive Buy",
        price=current_price,
        signal_value=1
    )

# В коде торговли
from core.notifications import notify_trade

# При выполнении сделки
await notify_trade(
    ticker=ticker,
    side="BUY",
    quantity=quantity,
    price=execution_price,
    total_value=total_value
)
```

## Мониторинг и отладка

### Логирование

Система ведет подробные логи:

```python
import logging
logger = logging.getLogger('core.notifications')
```

### Тестирование

```python
# Тест всех каналов
results = await notification_manager.test_all_channels()

# Тест конкретного канала
success = await telegram_notifier.test_connection()
```

### Статус системы

```python
# Получить статус
status = notification_manager.get_status()

# Статистика уведомлений
stats = dashboard_alerts.get_notification_stats()

# Сводка health checks
summary = health_checker.get_summary()
```

## Производительность

### Rate Limiting
- Telegram: минимум 1 секунда между сообщениями
- Dashboard: без ограничений

### Очереди сообщений
- Максимум 50 сообщений в очереди Telegram
- Автоматическая очистка старых уведомлений (24 часа)

### Оптимизация
- Асинхронная отправка уведомлений
- Батчинг сообщений
- Кэширование результатов health checks

## Безопасность

### Telegram Bot
- Токен бота хранится в переменных окружения
- Chat ID проверяется при инициализации
- Rate limiting предотвращает спам

### Dashboard
- Уведомления хранятся в session state
- Автоматическая очистка старых данных
- Валидация входных данных

## Расширение системы

### Добавление новых типов уведомлений

1. Добавьте тип в `NotificationType` enum
2. Создайте метод форматирования в `MessageFormatter`
3. Добавьте обработку в `NotificationManager`
4. Обновите конфигурацию

### Добавление новых каналов

1. Создайте класс уведомлений (например, `EmailNotifier`)
2. Реализуйте интерфейс отправки
3. Добавьте в `NotificationManager`
4. Обновите конфигурацию

### Кастомные health checks

1. Наследуйтесь от `HealthCheck`
2. Реализуйте метод `_perform_check()`
3. Добавьте в `SystemHealthChecker`

## Устранение неполадок

### Telegram не работает
1. Проверьте токен бота
2. Проверьте Chat ID
3. Убедитесь, что бот добавлен в чат
4. Проверьте интернет-соединение

### Dashboard уведомления не отображаются
1. Проверьте, что `dashboard_alerts` импортирован
2. Убедитесь, что уведомления добавляются в session state
3. Проверьте, что страница обновляется

### Health checks не работают
1. Проверьте права доступа к файлам
2. Убедитесь, что psutil установлен
3. Проверьте подключение к базе данных

### Метрики не собираются
1. Проверьте, что сбор метрик запущен
2. Убедитесь, что нет ошибок в логах
3. Проверьте доступ к системным ресурсам

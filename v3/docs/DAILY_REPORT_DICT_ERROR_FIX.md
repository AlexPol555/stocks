# Исправление ошибки AttributeError в send_daily_report

## Проблема

**Ошибка**: `AttributeError: 'dict' object has no attribute 'type'`

**Место**: `core/notifications/integration.py` в методе `send_daily_report`

**Причина**: В методе `send_daily_report` использовался неправильный метод форматирования:

```python
# Неправильно - возвращает словарь
notification = formatter.format_daily_report(report_data)
dashboard_alerts.add_notification(notification)  # Передает словарь
```

**Результат**: Метод `add_notification` ожидал объект `NotificationData`, но получал словарь.

## Решение

### Исправлен метод `send_daily_report`

**Было**:
```python
# Send to dashboard
from .message_formatter import MessageFormatter
formatter = MessageFormatter()
notification = formatter.format_daily_report(report_data)  # Возвращает словарь
dashboard_alerts.add_notification(notification)
```

**Стало**:
```python
# Send to dashboard
from .message_formatter import MessageFormatter
formatter = MessageFormatter()
notification = formatter.format_daily_report_notification(report_data)  # Возвращает NotificationData
dashboard_alerts.add_notification(notification)
```

## Архитектура исправления

### Правильный поток данных для daily report:

1. **Создание уведомления**: `format_daily_report_notification()` → `NotificationData` объект
2. **Добавление в dashboard**: `add_notification(NotificationData)` 
3. **Форматирование для dashboard**: `format_dashboard(NotificationData)` → словарь
4. **Сохранение в session_state**: словарь

### Методы форматирования в MessageFormatter:

- ✅ `format_daily_report_notification()` - возвращает `NotificationData` (для integration)
- ✅ `format_daily_report()` - возвращает словарь (для dashboard compatibility)

## Результат

✅ **Ошибка `AttributeError: 'dict' object has no attribute 'type'` в send_daily_report исправлена**
✅ **Правильный поток данных: NotificationData → format_dashboard → словарь**
✅ **Все методы уведомлений теперь работают единообразно**

Теперь тест "📈 Тест отчета" должен работать корректно! 🎉

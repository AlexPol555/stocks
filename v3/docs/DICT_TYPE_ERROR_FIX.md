# Исправление ошибки AttributeError: 'dict' object has no attribute 'type'

## Проблема

**Ошибка**: `AttributeError: 'dict' object has no attribute 'type'`

**Причина**: В методе `add_trade_alert` в `dashboard_alerts.py` происходило двойное форматирование:
1. Сначала создавался объект `NotificationData` 
2. Затем он форматировался в словарь через `format_dashboard()`
3. Затем этот словарь передавался в `add_notification()`
4. В `add_notification()` снова вызывался `format_dashboard()` на словаре

**Результат**: Метод `format_dashboard()` ожидал объект `NotificationData`, но получал словарь.

## Решение

### 1. Исправлен метод `add_trade_alert`

**Было**:
```python
# Create NotificationData object first
notification_data = self.formatter.format_trade_executed_notification(...)
# Then format for dashboard
notification = self.formatter.format_dashboard(notification_data)
self.add_notification(notification)  # Передаем словарь
```

**Стало**:
```python
# Create NotificationData object
notification_data = self.formatter.format_trade_executed_notification(...)
# Add directly to dashboard (format_dashboard will be called in add_notification)
self.add_notification(notification_data)  # Передаем объект NotificationData
```

### 2. Исправлен метод `add_health_check_alert`

**Было**:
```python
notification = self.formatter.format_health_check(...)  # Возвращает словарь
self.add_notification(notification)
```

**Стало**:
```python
# Create NotificationData object
notification_data = self.formatter.format_health_check_notification(...)
# Add directly to dashboard (format_dashboard will be called in add_notification)
self.add_notification(notification_data)  # Передаем объект NotificationData
```

### 3. Добавлен импорт Union

```python
from typing import Dict, List, Optional, Any, Union
```

## Архитектура исправления

### Правильный поток данных:

1. **Создание уведомления**: `format_*_notification()` → `NotificationData` объект
2. **Добавление в dashboard**: `add_notification(NotificationData)` 
3. **Форматирование для dashboard**: `format_dashboard(NotificationData)` → словарь
4. **Сохранение в session_state**: словарь

### Методы, которые работают правильно:

- ✅ `add_signal_alert()` - уже использовал `format_signal_notification()`
- ✅ `add_error_alert()` - уже использовал `format_error_notification()`
- ✅ `add_critical_alert()` - уже использовал `format_critical_notification()`

### Методы, которые были исправлены:

- ✅ `add_trade_alert()` - исправлен
- ✅ `add_health_check_alert()` - исправлен

## Результат

✅ **Ошибка `AttributeError: 'dict' object has no attribute 'type'` исправлена**
✅ **Все методы `add_*_alert` теперь работают единообразно**
✅ **Правильный поток данных: NotificationData → format_dashboard → словарь**
✅ **Нет дублирования форматирования**

Теперь все уведомления должны корректно добавляться в dashboard! 🎉

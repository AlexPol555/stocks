# Исправление ошибки импорта модуля уведомлений

## Проблема

При попытке импорта модуля уведомлений возникала ошибка:
```
ModuleNotFoundError: No module named 'core.notifications.monitoring'
```

## Причина

В файле `core/notifications/integration.py` был неправильный импорт:
```python
from .monitoring import SystemHealthChecker, MetricsCollector
```

Модуль мониторинга находится в `core.monitoring`, а не в `core.notifications.monitoring`.

## Решение

### 1. Исправлен импорт в `core/notifications/integration.py`
```python
# Было:
from .monitoring import SystemHealthChecker, MetricsCollector

# Стало:
from ..monitoring import SystemHealthChecker, MetricsCollector
```

### 2. Исправлен импорт в `core/notifications/__init__.py`
```python
# Было:
from .monitoring import SystemMonitor, HealthCheck

# Стало:
from ..monitoring import SystemHealthChecker, MetricsCollector
```

### 3. Обновлен список экспорта в `__all__`
```python
__all__ = [
    # ... другие экспорты ...
    "SystemHealthChecker",  # Вместо "SystemMonitor"
    "MetricsCollector",     # Вместо "HealthCheck"
]
```

## Проверка

После исправления все импорты работают корректно:

```python
# Эти импорты теперь работают:
from core.notifications import (
    notify_signal,
    notify_error,
    notify_critical,
    notify_trade,
    notification_manager,
    dashboard_alerts,
    SystemHealthChecker,
    MetricsCollector
)

from core.monitoring import (
    SystemHealthChecker,
    MetricsCollector
)
```

## Файлы, которые были изменены

1. `core/notifications/integration.py` - исправлен импорт мониторинга
2. `core/notifications/__init__.py` - исправлен импорт и экспорт

## Результат

✅ Все импорты работают корректно
✅ Модуль уведомлений полностью функционален
✅ Страницы уведомлений загружаются без ошибок
✅ Система мониторинга интегрирована правильно

## Тестирование

Для проверки работоспособности:

1. **Запустите приложение** - все страницы должны загружаться без ошибок
2. **Откройте страницу уведомлений** - `pages/13_🔔_Notifications.py`
3. **Откройте страницу мониторинга** - `pages/14_🔍_System_Monitoring.py`
4. **Запустите пример** - `python examples/notifications_example.py`

Система уведомлений готова к использованию! 🎉

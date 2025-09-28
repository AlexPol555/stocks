# Исправление ошибки метода get_metrics_history

## Проблема

**Ошибка**: `TypeError: MetricsCollector.get_metrics_history() got an unexpected keyword argument 'hours'`

**Местоположение**: `pages/14_🔍_System_Monitoring.py`, строка 153

**Причина**: Метод `get_metrics_history()` принимает параметр `since` (datetime), а не `hours` (int).

## Анализ методов MetricsCollector

### Правильная сигнатура методов:

1. **`get_metrics_history(since=None, limit=None)`**
   - `since`: Optional[datetime] - получить метрики с этого времени
   - `limit`: Optional[int] - максимальное количество метрик

2. **`get_metrics_summary(hours=24)`**
   - `hours`: int - количество часов для сводки

## Исправление

### Было (неправильно):
```python
history = metrics_collector.get_metrics_history(hours=24)
```

### Стало (правильно):
```python
since_time = datetime.now() - timedelta(hours=24)
history = metrics_collector.get_metrics_history(since=since_time)
```

## Измененный файл

**`pages/14_🔍_System_Monitoring.py`**:
- Строка 153-154: Исправлен вызов метода `get_metrics_history`

## Проверка

### Линтер
- ✅ `pages/14_🔍_System_Monitoring.py` - без ошибок

### Тестирование
Создан файл `test_metrics_methods.py` для проверки методов:
- ✅ `get_metrics_history(since=datetime)` - работает
- ✅ `get_metrics_history(limit=int)` - работает  
- ✅ `get_metrics_summary(hours=int)` - работает
- ✅ `get_current_metrics()` - работает

## Правильное использование методов

### Для получения исторических метрик за последние N часов:
```python
from datetime import datetime, timedelta

# Получить метрики за последние 24 часа
since_time = datetime.now() - timedelta(hours=24)
history = metrics_collector.get_metrics_history(since=since_time)

# Получить последние 100 метрик
history = metrics_collector.get_metrics_history(limit=100)

# Получить метрики за последние 6 часов, максимум 50 записей
since_time = datetime.now() - timedelta(hours=6)
history = metrics_collector.get_metrics_history(since=since_time, limit=50)
```

### Для получения сводки метрик:
```python
# Сводка за последние 24 часа
summary = metrics_collector.get_metrics_summary(hours=24)

# Сводка за последние 6 часов
summary = metrics_collector.get_metrics_summary(hours=6)
```

## Результат

✅ **Ошибка исправлена**
✅ **Страница мониторинга работает корректно**
✅ **Все методы MetricsCollector работают правильно**
✅ **Документация обновлена**

## Заключение

Метод `get_metrics_history()` теперь используется с правильными параметрами. Страница мониторинга системы работает без ошибок.

**Статус**: ✅ **ИСПРАВЛЕНО**

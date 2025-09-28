# Task Scheduler Module

Модуль планировщика задач для автоматизированной торговой системы.

## Описание

Этот модуль предоставляет возможности для планирования и выполнения регулярных задач, включая:
- Обновление рыночных данных
- Получение новостей
- Расчет технических индикаторов
- Генерация торговых сигналов
- Отправка уведомлений

## Структура модуля

```
core/scheduler/
├── __init__.py          # Экспорт основных классов
├── scheduler.py         # Основной класс планировщика
├── trading_calendar.py  # Торговый календарь
├── integration.py       # Интеграция с существующими модулями
├── example.py          # Пример использования
└── README.md           # Документация
```

## Основные компоненты

### TaskScheduler

Основной класс планировщика, который управляет выполнением задач.

**Основные возможности:**
- Добавление/удаление задач
- Управление приоритетами
- Обработка зависимостей между задачами
- Автоматический повтор при ошибках
- Асинхронное выполнение

### TradingCalendar

Класс для работы с торговым календарем.

**Основные возможности:**
- Определение торговых сессий
- Проверка торговых дней
- Исключение праздничных дней
- Определение оптимального времени для задач

### SchedulerIntegration

Класс для интеграции планировщика с существующими модулями.

**Основные возможности:**
- Настройка задач для обновления данных
- Настройка задач для работы с новостями
- Настройка задач для анализа
- Управление уведомлениями

## Использование

### Базовое использование

```python
from core.scheduler import TaskScheduler, TradingCalendar
from core.scheduler.integration import SchedulerIntegration

# Создание планировщика
trading_calendar = TradingCalendar()
scheduler = TaskScheduler(trading_calendar)

# Создание интеграции
integration = SchedulerIntegration(scheduler, trading_calendar)

# Настройка задач
integration.setup_all_tasks(
    data_loader_func=your_data_loader_function,
    news_fetch_func=your_news_fetch_function,
    news_process_func=your_news_process_function,
    indicators_func=your_indicators_function,
    signals_func=your_signals_function,
    notification_func=your_notification_function
)

# Запуск планировщика
integration.start_scheduler()
```

### Настройка отдельных задач

```python
# Добавление задачи обновления рыночных данных
scheduler.add_task(
    name="update_market_data",
    func=update_market_data_function,
    interval=timedelta(hours=1),
    priority=10,
    dependencies=[],
    max_errors=3
)

# Добавление задачи получения новостей
scheduler.add_task(
    name="fetch_news",
    func=fetch_news_function,
    interval=timedelta(minutes=30),
    priority=5,
    dependencies=[],
    max_errors=5
)
```

### Управление задачами

```python
# Включение/отключение задач
integration.enable_task("update_market_data")
integration.disable_task("fetch_news")

# Получение статуса
status = integration.get_task_status()
print(f"Всего задач: {status['total_tasks']}")
print(f"Активных задач: {status['enabled_tasks']}")

# Получение времени следующего запуска
next_runs = integration.get_next_run_times()
for task_name, next_run in next_runs.items():
    print(f"{task_name}: {next_run}")
```

## Конфигурация задач

### Приоритеты

Задачи выполняются в порядке приоритета (высший приоритет = большее число):
- 10: Критически важные задачи (обновление данных)
- 8-9: Важные задачи (расчет индикаторов, уведомления)
- 5-7: Обычные задачи (генерация сигналов)
- 1-4: Фоновые задачи (логирование, очистка)

### Интервалы выполнения

- **Обновление рыночных данных**: каждый час в торговые дни
- **Получение новостей**: каждые 30 минут
- **Обработка новостей**: каждые 2 часа
- **Расчет индикаторов**: после обновления данных
- **Генерация сигналов**: после расчета индикаторов
- **Уведомления**: при критических событиях

### Зависимости

Задачи могут зависеть от других задач:
- `calculate_indicators` зависит от `update_market_data`
- `generate_signals` зависит от `calculate_indicators`
- `process_news_pipeline` зависит от `fetch_news`

## Торговый календарь

### Поддерживаемые рынки

- **MOEX** (Московская биржа): Пн-Пт, 10:00-18:45 MSK
- **NYSE** (Нью-Йоркская биржа): Пн-Пт, 9:30-16:00 EST
- **NASDAQ**: Пн-Пт, 9:30-16:00 EST

### Проверка торговых условий

```python
# Проверка торгового дня
if trading_calendar.is_trading_day():
    print("Сегодня торговый день")

# Проверка открытия рынка
if trading_calendar.is_market_open(Market.MOEX):
    print("Московская биржа открыта")

# Получение следующего торгового дня
next_trading_day = trading_calendar.get_next_trading_day()
print(f"Следующий торговый день: {next_trading_day}")
```

## Обработка ошибок

### Автоматический повтор

При ошибке выполнения задачи:
1. Увеличивается счетчик ошибок
2. Задача планируется на повтор с экспоненциальной задержкой
3. При превышении максимального количества ошибок задача отключается

### Логирование

Все события планировщика записываются в лог:
- Запуск/остановка задач
- Успешное выполнение
- Ошибки выполнения
- Изменение статуса задач

## Мониторинг

### Статус планировщика

```python
status = integration.get_task_status()
print(f"Планировщик работает: {status['running']}")
print(f"Всего задач: {status['total_tasks']}")
print(f"Активных задач: {status['enabled_tasks']}")
print(f"Выполняющихся задач: {status['running_tasks']}")
print(f"Задач с ошибками: {status['failed_tasks']}")
```

### Статус отдельных задач

```python
for task_name, task_info in status['tasks'].items():
    print(f"{task_name}:")
    print(f"  Статус: {task_info['status']}")
    print(f"  Последний запуск: {task_info['last_run']}")
    print(f"  Следующий запуск: {task_info['next_run']}")
    print(f"  Количество ошибок: {task_info['error_count']}")
    print(f"  Активна: {task_info['enabled']}")
```

## Примеры интеграции

### С модулем data_loader

```python
from core.data_loader import load_csv_data

async def update_market_data():
    """Обновление рыночных данных."""
    data = load_csv_data("data/")
    # Обработка данных...
    logger.info("Рыночные данные обновлены")

integration.setup_market_data_tasks(update_market_data)
```

### С модулем news

```python
from core.news import run_fetch_job, build_summary

async def fetch_news():
    """Получение новостей."""
    result = run_fetch_job()
    logger.info(f"Новости получены: {result}")

async def process_news():
    """Обработка новостей."""
    summary = build_summary()
    logger.info(f"Новости обработаны: {summary}")

integration.setup_news_tasks(fetch_news, process_news)
```

### С модулем analyzer

```python
from core.analyzer import StockAnalyzer

async def calculate_indicators():
    """Расчет технических индикаторов."""
    analyzer = StockAnalyzer(api_key="your_key")
    # Расчет индикаторов...
    logger.info("Индикаторы рассчитаны")

integration.setup_analysis_tasks(calculate_indicators, generate_signals)
```

## Требования

- Python 3.8+
- asyncio
- datetime
- logging

## Установка

Модуль автоматически устанавливается при установке основного приложения.

## Лицензия

См. основной файл лицензии проекта.

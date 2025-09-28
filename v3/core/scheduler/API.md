# Task Scheduler API Documentation

## Overview

The Task Scheduler module provides a comprehensive solution for scheduling and executing automated tasks in the trading system. It includes intelligent scheduling based on trading calendars, task dependencies, error handling, and monitoring capabilities.

## Core Classes

### TaskScheduler

The main scheduler class that manages task execution.

#### Constructor

```python
TaskScheduler(trading_calendar: Optional[TradingCalendar] = None)
```

**Parameters:**
- `trading_calendar`: Optional trading calendar for market-aware scheduling

#### Methods

##### add_task

```python
add_task(
    name: str,
    func: Callable,
    interval: timedelta,
    priority: int = 0,
    dependencies: List[str] = None,
    max_errors: int = 3,
    enabled: bool = True
) -> None
```

Add a new task to the scheduler.

**Parameters:**
- `name`: Unique task name
- `func`: Function to execute
- `interval`: Time interval between executions
- `priority`: Task priority (higher = more important)
- `dependencies`: List of task names this task depends on
- `max_errors`: Maximum consecutive errors before disabling
- `enabled`: Whether task is enabled by default

**Raises:**
- `ValueError`: If task name already exists

##### remove_task

```python
remove_task(name: str) -> None
```

Remove a task from the scheduler.

**Parameters:**
- `name`: Task name to remove

##### enable_task

```python
enable_task(name: str) -> None
```

Enable a task.

**Parameters:**
- `name`: Task name to enable

##### disable_task

```python
disable_task(name: str) -> None
```

Disable a task.

**Parameters:**
- `name`: Task name to disable

##### get_task_status

```python
get_task_status(name: str) -> Optional[TaskStatus]
```

Get task status.

**Parameters:**
- `name`: Task name

**Returns:**
- Task status or None if task not found

##### get_next_run_time

```python
get_next_run_time(name: str) -> Optional[datetime]
```

Get next scheduled run time for a task.

**Parameters:**
- `name`: Task name

**Returns:**
- Next run time or None if task not found

##### start

```python
async start() -> None
```

Start the task scheduler.

##### stop

```python
async stop() -> None
```

Stop the task scheduler.

##### get_status

```python
get_status() -> Dict[str, Any]
```

Get scheduler status information.

**Returns:**
- Dictionary with scheduler status

### TradingCalendar

Class for working with trading calendar and market hours.

#### Constructor

```python
TradingCalendar()
```

#### Methods

##### is_trading_day

```python
is_trading_day(date: Optional[datetime] = None) -> bool
```

Check if a date is a trading day.

**Parameters:**
- `date`: Date to check (defaults to today)

**Returns:**
- True if it's a trading day

##### is_market_open

```python
is_market_open(market: Market, date: Optional[datetime] = None) -> bool
```

Check if a market is open at a specific time.

**Parameters:**
- `market`: Market to check
- `date`: Date/time to check (defaults to now)

**Returns:**
- True if market is open

##### get_next_trading_day

```python
get_next_trading_day(date: Optional[datetime] = None) -> datetime
```

Get the next trading day.

**Parameters:**
- `date`: Starting date (defaults to today)

**Returns:**
- Next trading day

##### get_trading_sessions

```python
get_trading_sessions(market: Optional[Market] = None) -> List[TradingSession]
```

Get trading sessions.

**Parameters:**
- `market`: Filter by market (optional)

**Returns:**
- List of trading sessions

##### get_market_hours

```python
get_market_hours(market: Market) -> Optional[tuple]
```

Get market trading hours.

**Parameters:**
- `market`: Market to get hours for

**Returns:**
- Tuple of (start_time, end_time) or None if not found

##### should_run_task

```python
should_run_task(task_name: str, market: Optional[Market] = None) -> bool
```

Determine if a task should run based on market conditions.

**Parameters:**
- `task_name`: Name of the task
- `market`: Market to check (optional)

**Returns:**
- True if task should run

##### get_optimal_run_time

```python
get_optimal_run_time(task_name: str, market: Optional[Market] = None) -> datetime
```

Get optimal time to run a task.

**Parameters:**
- `task_name`: Name of the task
- `market`: Market to consider (optional)

**Returns:**
- Optimal run time

### SchedulerIntegration

Class for integrating the scheduler with existing system components.

#### Constructor

```python
SchedulerIntegration(scheduler: TaskScheduler, trading_calendar: TradingCalendar)
```

**Parameters:**
- `scheduler`: Task scheduler instance
- `trading_calendar`: Trading calendar instance

#### Methods

##### setup_market_data_tasks

```python
setup_market_data_tasks(data_loader_func: callable) -> None
```

Setup market data update tasks.

**Parameters:**
- `data_loader_func`: Function to load market data

##### setup_news_tasks

```python
setup_news_tasks(news_fetch_func: callable, news_process_func: callable) -> None
```

Setup news-related tasks.

**Parameters:**
- `news_fetch_func`: Function to fetch news
- `news_process_func`: Function to process news pipeline

##### setup_analysis_tasks

```python
setup_analysis_tasks(indicators_func: callable, signals_func: callable) -> None
```

Setup analysis tasks.

**Parameters:**
- `indicators_func`: Function to calculate indicators
- `signals_func`: Function to generate signals

##### setup_notification_tasks

```python
setup_notification_tasks(notification_func: callable) -> None
```

Setup notification tasks.

**Parameters:**
- `notification_func`: Function to send notifications

##### setup_all_tasks

```python
setup_all_tasks(
    data_loader_func: callable,
    news_fetch_func: callable,
    news_process_func: callable,
    indicators_func: callable,
    signals_func: callable,
    notification_func: callable
) -> None
```

Setup all tasks at once.

**Parameters:**
- `data_loader_func`: Function to load market data
- `news_fetch_func`: Function to fetch news
- `news_process_func`: Function to process news pipeline
- `indicators_func`: Function to calculate indicators
- `signals_func`: Function to generate signals
- `notification_func`: Function to send notifications

##### get_task_status

```python
get_task_status() -> Dict[str, Any]
```

Get status of all tasks.

**Returns:**
- Dictionary with task status information

##### start_scheduler

```python
start_scheduler() -> None
```

Start the task scheduler.

##### stop_scheduler

```python
stop_scheduler() -> None
```

Stop the task scheduler.

##### enable_task

```python
enable_task(task_name: str) -> None
```

Enable a specific task.

**Parameters:**
- `task_name`: Name of task to enable

##### disable_task

```python
disable_task(task_name: str) -> None
```

Disable a specific task.

**Parameters:**
- `task_name`: Name of task to disable

##### get_next_run_times

```python
get_next_run_times() -> Dict[str, Optional[datetime]]
```

Get next run times for all tasks.

**Returns:**
- Dictionary mapping task names to next run times

## Enums

### TaskStatus

```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### Market

```python
class Market(Enum):
    MOEX = "moex"  # Moscow Exchange
    NYSE = "nyse"  # New York Stock Exchange
    NASDAQ = "nasdaq"  # NASDAQ
```

## Data Classes

### Task

```python
@dataclass
class Task:
    name: str
    func: Callable
    interval: timedelta
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    error_count: int = 0
    max_errors: int = 3
    enabled: bool = True
    priority: int = 0
    dependencies: List[str] = None
```

### TradingSession

```python
@dataclass
class TradingSession:
    market: Market
    start_time: time
    end_time: time
    timezone: str
    weekdays: Set[int]  # 0=Monday, 6=Sunday
```

## Configuration

### Task Intervals

```python
TASK_INTERVALS = {
    "update_market_data": timedelta(hours=1),
    "fetch_news": timedelta(minutes=30),
    "process_news_pipeline": timedelta(hours=2),
    "calculate_indicators": timedelta(hours=1),
    "generate_signals": timedelta(hours=1),
    "send_notifications": timedelta(minutes=15),
}
```

### Task Priorities

```python
TASK_PRIORITIES = {
    "update_market_data": 10,
    "send_notifications": 9,
    "calculate_indicators": 8,
    "generate_signals": 7,
    "fetch_news": 5,
    "process_news_pipeline": 3,
}
```

### Task Dependencies

```python
TASK_DEPENDENCIES = {
    "calculate_indicators": ["update_market_data"],
    "generate_signals": ["calculate_indicators"],
    "process_news_pipeline": ["fetch_news"],
}
```

## Utility Functions

### retry_on_failure

```python
@retry_on_failure(max_retries: int = 3, delay: float = 1.0, exponential: bool = True)
def your_function():
    # Your function code
    pass
```

Decorator to retry a function on failure.

**Parameters:**
- `max_retries`: Maximum number of retries
- `delay`: Initial delay between retries in seconds
- `exponential`: Whether to use exponential backoff

### format_duration

```python
format_duration(duration: timedelta) -> str
```

Format a duration in a human-readable format.

**Parameters:**
- `duration`: Duration to format

**Returns:**
- Formatted duration string

### get_task_summary

```python
get_task_summary(tasks: Dict[str, Any]) -> Dict[str, Any]
```

Get a summary of task statuses.

**Parameters:**
- `tasks`: Dictionary of task information

**Returns:**
- Summary dictionary

### get_health_status

```python
get_health_status(tasks: Dict[str, Any]) -> str
```

Get overall health status of the scheduler.

**Parameters:**
- `tasks`: Dictionary of task information

**Returns:**
- Health status string ("healthy", "unhealthy", "running", "idle")

## Examples

### Basic Usage

```python
from core.scheduler import TaskScheduler
from datetime import timedelta

# Create scheduler
scheduler = TaskScheduler()

# Add a task
async def my_task():
    print("Task executed")

scheduler.add_task(
    name="my_task",
    func=my_task,
    interval=timedelta(minutes=5)
)

# Start scheduler
await scheduler.start()
```

### With Trading Calendar

```python
from core.scheduler import TaskScheduler, TradingCalendar
from core.scheduler.trading_calendar import Market

# Create trading calendar and scheduler
trading_calendar = TradingCalendar()
scheduler = TaskScheduler(trading_calendar)

# Add market-aware task
async def market_task():
    if trading_calendar.is_market_open(Market.MOEX):
        print("Market is open, executing task")
    else:
        print("Market is closed, skipping task")

scheduler.add_task(
    name="market_task",
    func=market_task,
    interval=timedelta(minutes=1)
)

# Start scheduler
await scheduler.start()
```

### With Dependencies

```python
# Add tasks with dependencies
scheduler.add_task(
    name="collect_data",
    func=collect_data_func,
    interval=timedelta(minutes=10),
    priority=10
)

scheduler.add_task(
    name="process_data",
    func=process_data_func,
    interval=timedelta(minutes=10),
    priority=8,
    dependencies=["collect_data"]
)
```

### With Error Handling

```python
from core.scheduler.utils import retry_on_failure

@retry_on_failure(max_retries=3, delay=1.0, exponential=True)
async def unreliable_task():
    # Your task code that might fail
    pass

scheduler.add_task(
    name="unreliable_task",
    func=unreliable_task,
    interval=timedelta(minutes=5),
    max_errors=5
)
```

## Error Handling

The scheduler includes comprehensive error handling:

1. **Task Execution Errors**: Tasks that fail are retried with exponential backoff
2. **Dependency Errors**: Tasks with unmet dependencies are skipped
3. **Scheduler Errors**: Scheduler errors are logged and the scheduler continues running
4. **Configuration Errors**: Invalid configurations are validated and errors are reported

## Monitoring

The scheduler provides monitoring capabilities:

1. **Task Status**: Track individual task status and execution times
2. **Health Status**: Monitor overall scheduler health
3. **Performance Metrics**: Track task execution times and error rates
4. **Next Run Times**: See when tasks are scheduled to run next

## Best Practices

1. **Task Design**: Keep tasks focused and atomic
2. **Error Handling**: Use retry decorators for unreliable operations
3. **Dependencies**: Design clear task dependencies
4. **Monitoring**: Regularly check scheduler status and health
5. **Configuration**: Use configuration files for task settings
6. **Testing**: Test tasks thoroughly before adding to production scheduler

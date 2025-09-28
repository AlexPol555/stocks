"""Utility functions for the task scheduler.

This module provides utility functions for working with the task scheduler,
including time calculations, task management, and monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, exponential: bool = True):
    """Decorator to retry a function on failure.
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        exponential: Whether to use exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                        if exponential:
                            current_delay *= 2
                        await asyncio.sleep(current_delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                        raise last_exception
                        
        return wrapper
    return decorator


def calculate_next_run_time(
    last_run: Optional[datetime],
    interval: timedelta,
    now: Optional[datetime] = None
) -> datetime:
    """Calculate the next run time for a task.
    
    Args:
        last_run: Last time the task was run
        interval: Interval between runs
        now: Current time (defaults to now)
        
    Returns:
        Next run time
    """
    if now is None:
        now = datetime.now()
        
    if last_run is None:
        return now + interval
        
    return last_run + interval


def is_time_to_run(
    last_run: Optional[datetime],
    interval: timedelta,
    now: Optional[datetime] = None
) -> bool:
    """Check if it's time to run a task.
    
    Args:
        last_run: Last time the task was run
        interval: Interval between runs
        now: Current time (defaults to now)
        
    Returns:
        True if it's time to run the task
    """
    if now is None:
        now = datetime.now()
        
    if last_run is None:
        return True
        
    return now >= last_run + interval


def format_duration(duration: timedelta) -> str:
    """Format a duration in a human-readable format.
    
    Args:
        duration: Duration to format
        
    Returns:
        Formatted duration string
    """
    total_seconds = int(duration.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        return f"{days}d {hours}h"


def format_datetime(dt: datetime) -> str:
    """Format a datetime in a human-readable format.
    
    Args:
        dt: Datetime to format
        
    Returns:
        Formatted datetime string
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_task_summary(tasks: Dict[str, Any]) -> Dict[str, Any]:
    """Get a summary of task statuses.
    
    Args:
        tasks: Dictionary of task information
        
    Returns:
        Summary dictionary
    """
    summary = {
        "total": len(tasks),
        "enabled": 0,
        "disabled": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "pending": 0,
        "cancelled": 0,
    }
    
    for task_info in tasks.values():
        status = task_info.get("status", "pending")
        enabled = task_info.get("enabled", True)
        
        if enabled:
            summary["enabled"] += 1
        else:
            summary["disabled"] += 1
            
        if status == "running":
            summary["running"] += 1
        elif status == "completed":
            summary["completed"] += 1
        elif status == "failed":
            summary["failed"] += 1
        elif status == "pending":
            summary["pending"] += 1
        elif status == "cancelled":
            summary["cancelled"] += 1
            
    return summary


def get_health_status(tasks: Dict[str, Any]) -> str:
    """Get overall health status of the scheduler.
    
    Args:
        tasks: Dictionary of task information
        
    Returns:
        Health status string
    """
    summary = get_task_summary(tasks)
    
    if summary["failed"] > 0:
        return "unhealthy"
    elif summary["running"] > 0:
        return "running"
    elif summary["enabled"] > 0:
        return "healthy"
    else:
        return "idle"


def calculate_task_load(tasks: Dict[str, Any]) -> float:
    """Calculate the current task load.
    
    Args:
        tasks: Dictionary of task information
        
    Returns:
        Task load as a percentage (0-100)
    """
    if not tasks:
        return 0.0
        
    running_tasks = sum(1 for t in tasks.values() if t.get("status") == "running")
    total_tasks = len(tasks)
    
    return (running_tasks / total_tasks) * 100


def get_next_scheduled_tasks(tasks: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """Get the next scheduled tasks.
    
    Args:
        tasks: Dictionary of task information
        limit: Maximum number of tasks to return
        
    Returns:
        List of next scheduled tasks
    """
    scheduled_tasks = []
    
    for name, task_info in tasks.items():
        if not task_info.get("enabled", True):
            continue
            
        next_run = task_info.get("next_run")
        if next_run:
            scheduled_tasks.append({
                "name": name,
                "next_run": next_run,
                "status": task_info.get("status", "pending")
            })
            
    # Sort by next run time
    scheduled_tasks.sort(key=lambda x: x["next_run"])
    
    return scheduled_tasks[:limit]


def estimate_completion_time(tasks: Dict[str, Any]) -> Optional[datetime]:
    """Estimate when all current tasks will complete.
    
    Args:
        tasks: Dictionary of task information
        
    Returns:
        Estimated completion time or None if no running tasks
    """
    running_tasks = [
        t for t in tasks.values() 
        if t.get("status") == "running"
    ]
    
    if not running_tasks:
        return None
        
    # This is a simplified estimation
    # In reality, you would need to track task execution times
    now = datetime.now()
    max_estimated_time = now + timedelta(minutes=30)  # Default estimate
    
    return max_estimated_time


def get_task_metrics(tasks: Dict[str, Any]) -> Dict[str, Any]:
    """Get performance metrics for tasks.
    
    Args:
        tasks: Dictionary of task information
        
    Returns:
        Dictionary with performance metrics
    """
    metrics = {
        "total_tasks": len(tasks),
        "enabled_tasks": sum(1 for t in tasks.values() if t.get("enabled", True)),
        "running_tasks": sum(1 for t in tasks.values() if t.get("status") == "running"),
        "failed_tasks": sum(1 for t in tasks.values() if t.get("status") == "failed"),
        "average_error_count": 0,
        "health_status": get_health_status(tasks),
        "task_load": calculate_task_load(tasks),
    }
    
    # Calculate average error count
    error_counts = [t.get("error_count", 0) for t in tasks.values()]
    if error_counts:
        metrics["average_error_count"] = sum(error_counts) / len(error_counts)
        
    return metrics


def validate_task_config(config: Dict[str, Any]) -> List[str]:
    """Validate task configuration.
    
    Args:
        config: Task configuration to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Check required fields
    required_fields = ["name", "func", "interval"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
            
    # Validate interval
    if "interval" in config:
        if not isinstance(config["interval"], timedelta):
            errors.append("Interval must be a timedelta object")
        elif config["interval"].total_seconds() <= 0:
            errors.append("Interval must be positive")
            
    # Validate priority
    if "priority" in config:
        if not isinstance(config["priority"], int):
            errors.append("Priority must be an integer")
        elif config["priority"] < 0:
            errors.append("Priority must be non-negative")
            
    # Validate dependencies
    if "dependencies" in config:
        if not isinstance(config["dependencies"], list):
            errors.append("Dependencies must be a list")
        else:
            for dep in config["dependencies"]:
                if not isinstance(dep, str):
                    errors.append("Dependencies must be strings")
                    
    # Validate max_errors
    if "max_errors" in config:
        if not isinstance(config["max_errors"], int):
            errors.append("Max errors must be an integer")
        elif config["max_errors"] < 0:
            errors.append("Max errors must be non-negative")
            
    return errors


def create_task_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a task from configuration.
    
    Args:
        config: Task configuration
        
    Returns:
        Task dictionary
    """
    # Validate configuration
    errors = validate_task_config(config)
    if errors:
        raise ValueError(f"Invalid task configuration: {', '.join(errors)}")
        
    # Create task with defaults
    task = {
        "name": config["name"],
        "func": config["func"],
        "interval": config["interval"],
        "priority": config.get("priority", 0),
        "dependencies": config.get("dependencies", []),
        "max_errors": config.get("max_errors", 3),
        "enabled": config.get("enabled", True),
        "last_run": None,
        "next_run": None,
        "status": "pending",
        "error_count": 0,
    }
    
    # Set next run time
    if task["next_run"] is None:
        task["next_run"] = datetime.now() + task["interval"]
        
    return task

"""Task scheduler implementation for automated trading system.

This module provides the main TaskScheduler class that manages
scheduled tasks for market data updates, news fetching, and analysis.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .trading_calendar import TradingCalendar

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a scheduled task."""
    name: str
    func: Callable
    interval: timedelta
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    error_count: int = 0
    max_errors: int = 3
    enabled: bool = True
    priority: int = 0  # Higher number = higher priority
    dependencies: List[str] = None  # List of task names this task depends on
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.next_run is None:
            self.next_run = datetime.now() + self.interval


class TaskScheduler:
    """Main task scheduler for automated trading system.
    
    Manages scheduled tasks including:
    - Market data updates
    - News fetching
    - Technical analysis calculations
    - Signal generation
    - Notifications
    """
    
    def __init__(self, trading_calendar: Optional[TradingCalendar] = None):
        """Initialize the task scheduler.
        
        Args:
            trading_calendar: Optional trading calendar for market-aware scheduling
        """
        self.trading_calendar = trading_calendar or TradingCalendar()
        self.tasks: Dict[str, Task] = {}
        self.running = False
        self._stop_event = asyncio.Event()
        
    def add_task(
        self,
        name: str,
        func: Callable,
        interval: timedelta,
        priority: int = 0,
        dependencies: List[str] = None,
        max_errors: int = 3,
        enabled: bool = True
    ) -> None:
        """Add a new task to the scheduler.
        
        Args:
            name: Unique task name
            func: Function to execute
            interval: Time interval between executions
            priority: Task priority (higher = more important)
            dependencies: List of task names this task depends on
            max_errors: Maximum consecutive errors before disabling
            enabled: Whether task is enabled by default
        """
        if name in self.tasks:
            raise ValueError(f"Task '{name}' already exists")
            
        task = Task(
            name=name,
            func=func,
            interval=interval,
            priority=priority,
            dependencies=dependencies or [],
            max_errors=max_errors,
            enabled=enabled
        )
        
        self.tasks[name] = task
        logger.info(f"Added task '{name}' with interval {interval}")
        
    def remove_task(self, name: str) -> None:
        """Remove a task from the scheduler.
        
        Args:
            name: Task name to remove
        """
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Removed task '{name}'")
        else:
            logger.warning(f"Task '{name}' not found")
            
    def enable_task(self, name: str) -> None:
        """Enable a task.
        
        Args:
            name: Task name to enable
        """
        if name in self.tasks:
            self.tasks[name].enabled = True
            logger.info(f"Enabled task '{name}'")
            
    def disable_task(self, name: str) -> None:
        """Disable a task.
        
        Args:
            name: Task name to disable
        """
        if name in self.tasks:
            self.tasks[name].enabled = False
            logger.info(f"Disabled task '{name}'")
            
    def get_task_status(self, name: str) -> Optional[TaskStatus]:
        """Get task status.
        
        Args:
            name: Task name
            
        Returns:
            Task status or None if task not found
        """
        task = self.tasks.get(name)
        return task.status if task else None
        
    def get_next_run_time(self, name: str) -> Optional[datetime]:
        """Get next scheduled run time for a task.
        
        Args:
            name: Task name
            
        Returns:
            Next run time or None if task not found
        """
        task = self.tasks.get(name)
        return task.next_run if task else None
        
    async def start(self) -> None:
        """Start the task scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        self.running = True
        self._stop_event.clear()
        logger.info("Starting task scheduler")
        
        try:
            await self._run_scheduler()
        except Exception as e:
            logger.exception("Scheduler error: %s", e)
        finally:
            self.running = False
            logger.info("Task scheduler stopped")
            
    async def stop(self) -> None:
        """Stop the task scheduler."""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
            
        logger.info("Stopping task scheduler")
        self._stop_event.set()
        
    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            try:
                # Get tasks ready to run
                ready_tasks = self._get_ready_tasks()
                
                if ready_tasks:
                    # Execute tasks in priority order
                    ready_tasks.sort(key=lambda t: t.priority, reverse=True)
                    
                    # Run tasks concurrently
                    await asyncio.gather(
                        *[self._execute_task(task) for task in ready_tasks],
                        return_exceptions=True
                    )
                
                # Wait before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.exception("Error in scheduler loop: %s", e)
                await asyncio.sleep(5)  # Wait before retrying
                
    def _get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to run.
        
        Returns:
            List of tasks ready for execution
        """
        ready_tasks = []
        now = datetime.now()
        
        for task in self.tasks.values():
            if not task.enabled or task.status == TaskStatus.RUNNING:
                continue
                
            # Check if task is ready to run
            if task.next_run and task.next_run <= now:
                # Check dependencies
                if self._check_dependencies(task):
                    ready_tasks.append(task)
                    
        return ready_tasks
        
    def _check_dependencies(self, task: Task) -> bool:
        """Check if task dependencies are satisfied.
        
        Args:
            task: Task to check dependencies for
            
        Returns:
            True if all dependencies are satisfied
        """
        for dep_name in task.dependencies:
            dep_task = self.tasks.get(dep_name)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
        
    async def _execute_task(self, task: Task) -> None:
        """Execute a single task.
        
        Args:
            task: Task to execute
        """
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        
        try:
            logger.info(f"Executing task '{task.name}'")
            
            # Execute the task function
            if asyncio.iscoroutinefunction(task.func):
                await task.func()
            else:
                task.func()
                
            # Task completed successfully
            task.status = TaskStatus.COMPLETED
            task.error_count = 0
            task.next_run = datetime.now() + task.interval
            
            logger.info(f"Task '{task.name}' completed successfully")
            
        except Exception as e:
            # Task failed
            task.status = TaskStatus.FAILED
            task.error_count += 1
            
            logger.error(f"Task '{task.name}' failed: {e}")
            
            # Disable task if max errors exceeded
            if task.error_count >= task.max_errors:
                task.enabled = False
                logger.error(f"Task '{task.name}' disabled after {task.max_errors} failures")
                
            # Schedule retry with exponential backoff
            retry_delay = min(task.interval.total_seconds() * (2 ** task.error_count), 3600)
            task.next_run = datetime.now() + timedelta(seconds=retry_delay)
            
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status information.
        
        Returns:
            Dictionary with scheduler status
        """
        return {
            "running": self.running,
            "total_tasks": len(self.tasks),
            "enabled_tasks": sum(1 for t in self.tasks.values() if t.enabled),
            "running_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
            "tasks": {
                name: {
                    "status": task.status.value,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "error_count": task.error_count,
                    "enabled": task.enabled
                }
                for name, task in self.tasks.items()
            }
        }

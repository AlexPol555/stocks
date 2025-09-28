"""Integration module for connecting scheduler with existing components.

This module provides integration functions that connect the task scheduler
with existing modules like data_loader, news, analyzer, and indicators.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import asyncio

from .scheduler import TaskScheduler
from .trading_calendar import TradingCalendar, Market

logger = logging.getLogger(__name__)


class SchedulerIntegration:
    """Integration class for connecting scheduler with existing components."""
    
    def __init__(self, scheduler: TaskScheduler, trading_calendar: TradingCalendar):
        """Initialize integration.
        
        Args:
            scheduler: Task scheduler instance
            trading_calendar: Trading calendar instance
        """
        self.scheduler = scheduler
        self.trading_calendar = trading_calendar
        
    def setup_market_data_tasks(self, data_loader_func: callable) -> None:
        """Setup market data update tasks.
        
        Args:
            data_loader_func: Function to load market data
        """
        # Market data update - every hour during trading days
        self.scheduler.add_task(
            name="update_market_data",
            func=data_loader_func,
            interval=timedelta(hours=1),
            priority=10,  # High priority
            dependencies=[],
            max_errors=3
        )
        
        logger.info("Market data update task configured")
        
    def setup_news_tasks(self, news_fetch_func: callable, news_process_func: callable) -> None:
        """Setup news-related tasks.
        
        Args:
            news_fetch_func: Function to fetch news
            news_process_func: Function to process news pipeline
        """
        # News fetching - every 30 minutes
        self.scheduler.add_task(
            name="fetch_news",
            func=news_fetch_func,
            interval=timedelta(minutes=30),
            priority=5,
            dependencies=[],
            max_errors=5
        )
        
        # News processing - every 2 hours
        self.scheduler.add_task(
            name="process_news_pipeline",
            func=news_process_func,
            interval=timedelta(hours=2),
            priority=3,
            dependencies=["fetch_news"],
            max_errors=3
        )
        
        logger.info("News tasks configured")
        
    def setup_analysis_tasks(self, indicators_func: callable, signals_func: callable) -> None:
        """Setup analysis tasks.
        
        Args:
            indicators_func: Function to calculate indicators
            signals_func: Function to generate signals
        """
        # Technical indicators calculation - after market data update
        self.scheduler.add_task(
            name="calculate_indicators",
            func=indicators_func,
            interval=timedelta(hours=1),
            priority=8,
            dependencies=["update_market_data"],
            max_errors=3
        )
        
        # Signal generation - after indicators calculation
        self.scheduler.add_task(
            name="generate_signals",
            func=signals_func,
            interval=timedelta(hours=1),
            priority=7,
            dependencies=["calculate_indicators"],
            max_errors=3
        )
        
        logger.info("Analysis tasks configured")
        
    def setup_notification_tasks(self, notification_func: callable) -> None:
        """Setup notification tasks.
        
        Args:
            notification_func: Function to send notifications
        """
        # Notifications - on critical events
        self.scheduler.add_task(
            name="send_notifications",
            func=notification_func,
            interval=timedelta(minutes=15),
            priority=9,  # High priority for notifications
            dependencies=[],
            max_errors=5
        )
        
        logger.info("Notification tasks configured")
        
    def setup_all_tasks(
        self,
        data_loader_func: callable,
        news_fetch_func: callable,
        news_process_func: callable,
        indicators_func: callable,
        signals_func: callable,
        notification_func: callable
    ) -> None:
        """Setup all tasks at once.
        
        Args:
            data_loader_func: Function to load market data
            news_fetch_func: Function to fetch news
            news_process_func: Function to process news pipeline
            indicators_func: Function to calculate indicators
            signals_func: Function to generate signals
            notification_func: Function to send notifications
        """
        self.setup_market_data_tasks(data_loader_func)
        self.setup_news_tasks(news_fetch_func, news_process_func)
        self.setup_analysis_tasks(indicators_func, signals_func)
        self.setup_notification_tasks(notification_func)
        
        logger.info("All tasks configured")
        
    def get_task_status(self) -> Dict[str, Any]:
        """Get status of all tasks.
        
        Returns:
            Dictionary with task status information
        """
        return self.scheduler.get_status()
        
    def start_scheduler(self) -> None:
        """Start the task scheduler."""
        if not self.scheduler.running:
            asyncio.create_task(self.scheduler.start())
            logger.info("Scheduler started")
        else:
            logger.warning("Scheduler is already running")
            
    def stop_scheduler(self) -> None:
        """Stop the task scheduler."""
        if self.scheduler.running:
            asyncio.create_task(self.scheduler.stop())
            logger.info("Scheduler stopped")
        else:
            logger.warning("Scheduler is not running")
            
    def enable_task(self, task_name: str) -> None:
        """Enable a specific task.
        
        Args:
            task_name: Name of task to enable
        """
        self.scheduler.enable_task(task_name)
        logger.info(f"Task '{task_name}' enabled")
        
    def disable_task(self, task_name: str) -> None:
        """Disable a specific task.
        
        Args:
            task_name: Name of task to disable
        """
        self.scheduler.disable_task(task_name)
        logger.info(f"Task '{task_name}' disabled")
        
    def get_next_run_times(self) -> Dict[str, Optional[datetime]]:
        """Get next run times for all tasks.
        
        Returns:
            Dictionary mapping task names to next run times
        """
        return {
            name: self.scheduler.get_next_run_time(name)
            for name in self.scheduler.tasks.keys()
        }

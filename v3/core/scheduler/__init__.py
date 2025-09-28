"""Scheduler module for automated task management.

This module provides task scheduling capabilities including:
- Market data updates
- News fetching
- Technical analysis calculations
- Signal generation
- Notifications
"""

from .scheduler import TaskScheduler, TaskStatus
from .trading_calendar import TradingCalendar, Market
from .integration import SchedulerIntegration
from .real_integration import RealSchedulerIntegration

__all__ = [
    "TaskScheduler", 
    "TaskStatus", 
    "TradingCalendar", 
    "Market",
    "SchedulerIntegration",
    "RealSchedulerIntegration"
]

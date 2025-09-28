"""Notifications module for the stock trading system.

This module provides comprehensive notification capabilities including:
- Telegram bot notifications
- Dashboard alerts
- System monitoring
- Message formatting
"""

from .telegram_bot import TelegramNotifier
from .message_formatter import MessageFormatter, NotificationType
from .dashboard_alerts import DashboardAlerts, dashboard_alerts
from .integration import (
    NotificationManager, 
    notification_manager,
    notify_signal,
    notify_error,
    notify_critical,
    notify_trade,
    # ML Notifications
    notify_ml_signal,
    notify_ml_prediction,
    notify_ml_sentiment,
    notify_ml_alert,
    notify_ml_analysis
)
from ..monitoring import SystemHealthChecker, MetricsCollector

__all__ = [
    "TelegramNotifier",
    "MessageFormatter", 
    "NotificationType",
    "DashboardAlerts",
    "dashboard_alerts",
    "NotificationManager",
    "notification_manager",
    "notify_signal",
    "notify_error", 
    "notify_critical",
    "notify_trade",
    # ML Notifications
    "notify_ml_signal",
    "notify_ml_prediction",
    "notify_ml_sentiment",
    "notify_ml_alert",
    "notify_ml_analysis",
    "SystemHealthChecker",
    "MetricsCollector",
]

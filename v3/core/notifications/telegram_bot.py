"""Telegram bot for sending notifications."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import json

try:
    import aiohttp
    import telegram
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Bot = None
    TelegramError = Exception

from .message_formatter import MessageFormatter, NotificationData, NotificationType


logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram bot for sending notifications."""
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        enabled: bool = True
    ):
        """Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token (if None, will try to get from env)
            chat_id: Chat ID to send messages to (if None, will try to get from env)
            enabled: Whether notifications are enabled
        """
        self.enabled = enabled and TELEGRAM_AVAILABLE
        
        if not TELEGRAM_AVAILABLE:
            logger.warning("Telegram dependencies not available. Install with: pip install python-telegram-bot aiohttp")
            self.enabled = False
            return
        
        # Get credentials from environment or parameters
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not found. Telegram notifications disabled.")
            self.enabled = False
            return
            
        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not found. Telegram notifications disabled.")
            self.enabled = False
            return
        
        # Initialize bot and formatter
        self.bot = Bot(token=self.bot_token)
        self.formatter = MessageFormatter()
        
        # Rate limiting
        self.last_message_time = {}
        self.min_interval = timedelta(seconds=1)  # Minimum interval between messages
        
        # Message queue for batching
        self.message_queue: List[NotificationData] = []
        self.max_queue_size = 50
        
        logger.info(f"Telegram notifier initialized. Chat ID: {self.chat_id}")
    
    async def send_notification(
        self,
        notification: NotificationData,
        force: bool = False
    ) -> bool:
        """Send a single notification.
        
        Args:
            notification: Notification to send
            force: Whether to bypass rate limiting
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Telegram notifications disabled")
            return False
        
        try:
            # Check rate limiting
            if not force and not self._can_send_message(notification.type):
                logger.debug(f"Rate limited for {notification.type.value}")
                return False
            
            # Format message
            message_text = self.formatter.format_telegram(notification)
            
            # Send message with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=message_text,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                    
                    # Update rate limiting
                    self.last_message_time[notification.type.value] = datetime.now()
                    
                    logger.info(f"Telegram notification sent: {notification.type.value}")
                    return True
                    
                except TelegramError as e:
                    if "parse entities" in str(e).lower():
                        # Try without Markdown parsing
                        try:
                            await self.bot.send_message(
                                chat_id=self.chat_id,
                                text=message_text.replace('*', '').replace('`', '').replace('_', ''),
                                disable_web_page_preview=True
                            )
                            self.last_message_time[notification.type.value] = datetime.now()
                            logger.info(f"Telegram notification sent (no Markdown): {notification.type.value}")
                            return True
                        except Exception as e2:
                            logger.error(f"Failed to send without Markdown: {e2}")
                            if attempt == max_retries - 1:
                                raise e
                    elif "event loop is closed" in str(e).lower():
                        logger.error(f"Event loop closed, skipping notification: {e}")
                        return False
                    else:
                        if attempt == max_retries - 1:
                            raise e
                        await asyncio.sleep(1)  # Wait before retry
                        
        except TelegramError as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram notification: {e}")
            return False
    
    async def send_signal_notification(
        self,
        ticker: str,
        signal_type: str,
        price: float,
        signal_value: int,
        additional_data: Optional[Dict] = None
    ) -> bool:
        """Send a trading signal notification.
        
        Args:
            ticker: Stock ticker
            signal_type: Type of signal (e.g., "Adaptive Buy")
            price: Stock price
            signal_value: Signal value (1 for buy, -1 for sell)
            additional_data: Additional data to include
            
        Returns:
            True if sent successfully, False otherwise
        """
        notification = self.formatter.format_signal_notification(
            ticker=ticker,
            signal_type=signal_type,
            price=price,
            signal_value=signal_value,
            additional_data=additional_data
        )
        
        return await self.send_notification(notification)
    
    async def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        component: str,
        additional_data: Optional[Dict] = None
    ) -> bool:
        """Send an error notification.
        
        Args:
            error_type: Type of error
            error_message: Error message
            component: Component where error occurred
            additional_data: Additional data to include
            
        Returns:
            True if sent successfully, False otherwise
        """
        notification = self.formatter.format_error_notification(
            error_type=error_type,
            error_message=error_message,
            component=component,
            additional_data=additional_data
        )
        
        return await self.send_notification(notification)
    
    async def send_critical_notification(
        self,
        critical_type: str,
        message: str,
        additional_data: Optional[Dict] = None
    ) -> bool:
        """Send a critical notification.
        
        Args:
            critical_type: Type of critical event
            message: Critical message
            additional_data: Additional data to include
            
        Returns:
            True if sent successfully, False otherwise
        """
        notification = self.formatter.format_critical_notification(
            critical_type=critical_type,
            message=message,
            additional_data=additional_data
        )
        
        return await self.send_notification(notification, force=True)
    
    async def send_daily_report(
        self,
        report_data: Dict,
        additional_data: Optional[Dict] = None
    ) -> bool:
        """Send a daily report notification.
        
        Args:
            report_data: Report data dictionary
            additional_data: Additional data to include
            
        Returns:
            True if sent successfully, False otherwise
        """
        notification = self.formatter.format_daily_report_notification(
            report_data=report_data,
            additional_data=additional_data
        )
        
        return await self.send_notification(notification)
    
    async def send_trade_executed(
        self,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
        total_value: float,
        additional_data: Optional[Dict] = None
    ) -> bool:
        """Send a trade execution notification.
        
        Args:
            ticker: Stock ticker
            side: Trade side (BUY/SELL)
            quantity: Quantity traded
            price: Execution price
            total_value: Total trade value
            additional_data: Additional data to include
            
        Returns:
            True if sent successfully, False otherwise
        """
        notification = self.formatter.format_trade_executed_notification(
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price,
            total_value=total_value,
            additional_data=additional_data
        )
        
        return await self.send_notification(notification)
    
    async def send_health_check(
        self,
        component: str,
        status: str,
        details: Optional[Dict] = None,
        additional_data: Optional[Dict] = None
    ) -> bool:
        """Send a health check notification.
        
        Args:
            component: Component name
            status: Health status
            details: Health check details
            additional_data: Additional data to include
            
        Returns:
            True if sent successfully, False otherwise
        """
        notification = self.formatter.format_health_check_notification(
            component=component,
            status=status,
            details=details,
            additional_data=additional_data
        )
        
        return await self.send_notification(notification)
    
    def queue_notification(self, notification: NotificationData) -> None:
        """Queue a notification for batch sending.
        
        Args:
            notification: Notification to queue
        """
        if not self.enabled:
            return
        
        self.message_queue.append(notification)
        
        # Limit queue size
        if len(self.message_queue) > self.max_queue_size:
            self.message_queue = self.message_queue[-self.max_queue_size:]
    
    async def flush_queue(self) -> int:
        """Send all queued notifications.
        
        Returns:
            Number of notifications sent successfully
        """
        if not self.enabled or not self.message_queue:
            return 0
        
        sent_count = 0
        for notification in self.message_queue:
            if await self.send_notification(notification):
                sent_count += 1
        
        self.message_queue.clear()
        return sent_count
    
    def _can_send_message(self, notification_type: NotificationType) -> bool:
        """Check if we can send a message based on rate limiting.
        
        Args:
            notification_type: Type of notification
            
        Returns:
            True if we can send the message, False otherwise
        """
        now = datetime.now()
        last_time = self.last_message_time.get(notification_type.value)
        
        if last_time is None:
            return True
        
        return now - last_time >= self.min_interval
    
    async def test_connection(self) -> bool:
        """Test Telegram bot connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Send a test message
            test_notification = NotificationData(
                type=NotificationType.SYSTEM_ALERT,
                title="Тест подключения",
                message="Telegram бот успешно подключен!",
                timestamp=datetime.now(),
                priority=1
            )
            
            return await self.send_notification(test_notification, force=True)
            
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Union[bool, str, int]]:
        """Get notifier status.
        
        Returns:
            Status dictionary
        """
        return {
            "enabled": self.enabled,
            "telegram_available": TELEGRAM_AVAILABLE,
            "bot_token_configured": bool(self.bot_token),
            "chat_id_configured": bool(self.chat_id),
            "queue_size": len(self.message_queue),
            "last_message_times": {
                k: v.isoformat() if v else None
                for k, v in self.last_message_time.items()
            }
        }


# Convenience functions for easy usage
async def send_signal_alert(
    ticker: str,
    signal_type: str,
    price: float,
    signal_value: int,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None
) -> bool:
    """Convenience function to send a signal alert.
    
    Args:
        ticker: Stock ticker
        signal_type: Type of signal
        price: Stock price
        signal_value: Signal value (1 for buy, -1 for sell)
        bot_token: Telegram bot token (optional)
        chat_id: Telegram chat ID (optional)
        
    Returns:
        True if sent successfully, False otherwise
    """
    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
    return await notifier.send_signal_notification(
        ticker=ticker,
        signal_type=signal_type,
        price=price,
        signal_value=signal_value
    )


async def send_error_alert(
    error_type: str,
    error_message: str,
    component: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None
) -> bool:
    """Convenience function to send an error alert.
    
    Args:
        error_type: Type of error
        error_message: Error message
        component: Component where error occurred
        bot_token: Telegram bot token (optional)
        chat_id: Telegram chat ID (optional)
        
    Returns:
        True if sent successfully, False otherwise
    """
    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
    return await notifier.send_error_notification(
        error_type=error_type,
        error_message=error_message,
        component=component
    )

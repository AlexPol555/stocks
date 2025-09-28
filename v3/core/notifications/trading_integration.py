"""Integration of notifications with trading system."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .integration import notification_manager


logger = logging.getLogger(__name__)


class TradingNotificationIntegration:
    """Integrates notifications with trading system components."""
    
    def __init__(self):
        """Initialize trading notification integration."""
        self.enabled = True
    
    async def on_signal_generated(
        self,
        ticker: str,
        signal_type: str,
        price: float,
        signal_value: int,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle signal generation notification.
        
        Args:
            ticker: Stock ticker
            signal_type: Type of signal
            price: Stock price
            signal_value: Signal value (1 for buy, -1 for sell)
            additional_data: Additional data
        """
        if not self.enabled:
            return
        
        try:
            await notification_manager.send_signal_notification(
                ticker=ticker,
                signal_type=signal_type,
                price=price,
                signal_value=signal_value,
                additional_data=additional_data
            )
            logger.info(f"Signal notification sent for {ticker} {signal_type}")
        except Exception as e:
            logger.error(f"Failed to send signal notification: {e}")
    
    async def on_trade_executed(
        self,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
        total_value: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle trade execution notification.
        
        Args:
            ticker: Stock ticker
            side: Trade side (BUY/SELL)
            quantity: Quantity traded
            price: Execution price
            total_value: Total trade value
            additional_data: Additional data
        """
        if not self.enabled:
            return
        
        try:
            await notification_manager.send_trade_notification(
                ticker=ticker,
                side=side,
                quantity=quantity,
                price=price,
                total_value=total_value,
                additional_data=additional_data
            )
            logger.info(f"Trade notification sent for {ticker} {side} {quantity}")
        except Exception as e:
            logger.error(f"Failed to send trade notification: {e}")
    
    async def on_error_occurred(
        self,
        error_type: str,
        error_message: str,
        component: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle error notification.
        
        Args:
            error_type: Type of error
            error_message: Error message
            component: Component where error occurred
            additional_data: Additional data
        """
        if not self.enabled:
            return
        
        try:
            await notification_manager.send_error_notification(
                error_type=error_type,
                error_message=error_message,
                component=component,
                additional_data=additional_data
            )
            logger.info(f"Error notification sent for {component}: {error_type}")
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    async def on_critical_event(
        self,
        critical_type: str,
        message: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle critical event notification.
        
        Args:
            critical_type: Type of critical event
            message: Critical message
            additional_data: Additional data
        """
        if not self.enabled:
            return
        
        try:
            await notification_manager.send_critical_notification(
                critical_type=critical_type,
                message=message,
                additional_data=additional_data
            )
            logger.info(f"Critical notification sent: {critical_type}")
        except Exception as e:
            logger.error(f"Failed to send critical notification: {e}")
    
    async def on_daily_report(
        self,
        report_data: Dict[str, Any]
    ) -> None:
        """Handle daily report notification.
        
        Args:
            report_data: Report data dictionary
        """
        if not self.enabled:
            return
        
        try:
            await notification_manager.send_daily_report(report_data)
            logger.info("Daily report notification sent")
        except Exception as e:
            logger.error(f"Failed to send daily report notification: {e}")
    
    def enable(self) -> None:
        """Enable notifications."""
        self.enabled = True
        logger.info("Trading notifications enabled")
    
    def disable(self) -> None:
        """Disable notifications."""
        self.enabled = False
        logger.info("Trading notifications disabled")
    
    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self.enabled


# Global instance
trading_notifications = TradingNotificationIntegration()


# Decorator for automatic error notifications
def notify_errors(component: str):
    """Decorator to automatically send error notifications.
    
    Args:
        component: Component name for error notifications
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Send error notification
                await trading_notifications.on_error_occurred(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    component=component,
                    additional_data={
                        "function": func.__name__,
                        "args": str(args)[:100],  # Truncate long args
                        "kwargs": str(kwargs)[:100]
                    }
                )
                raise
        return wrapper
    return decorator


# Example usage in trading functions
async def example_trading_function_with_notifications():
    """Example of how to use notifications in trading functions."""
    
    # Signal generation
    await trading_notifications.on_signal_generated(
        ticker="AAPL",
        signal_type="Adaptive Buy",
        price=150.25,
        signal_value=1,
        additional_data={"rsi": 30, "atr": 2.5}
    )
    
    # Trade execution
    await trading_notifications.on_trade_executed(
        ticker="AAPL",
        side="BUY",
        quantity=10,
        price=150.30,
        total_value=1503.0,
        additional_data={"commission": 1.50}
    )
    
    # Error handling
    try:
        # Some trading operation that might fail
        result = await some_risky_operation()
    except Exception as e:
        await trading_notifications.on_error_occurred(
            error_type="Trading Error",
            error_message=str(e),
            component="Trading Engine"
        )
        raise
    
    # Critical event
    if some_critical_condition():
        await trading_notifications.on_critical_event(
            critical_type="Risk Limit Exceeded",
            message="Portfolio risk limit exceeded",
            additional_data={"current_risk": 0.15, "limit": 0.10}
        )


# Example of using the decorator
@notify_errors("Signal Generator")
async def generate_trading_signal(ticker: str, data: Dict[str, Any]) -> int:
    """Generate trading signal with automatic error notifications."""
    # This function will automatically send error notifications if it fails
    # Implementation here...
    return 1  # Buy signal

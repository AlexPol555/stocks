"""Integration module for notifications with the trading system."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd

from .telegram_bot import TelegramNotifier
from .dashboard_alerts import dashboard_alerts
from .message_formatter import NotificationType, MessageFormatter
from ..monitoring import SystemHealthChecker, MetricsCollector


logger = logging.getLogger(__name__)


def load_env_file():
    """Load environment variables from .env file."""
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value


class NotificationManager:
    """Manages all notification channels and integrations."""
    
    def __init__(self, telegram_enabled: bool = True):
        """Initialize notification manager.
        
        Args:
            telegram_enabled: Whether to enable Telegram notifications
        """
        # Load .env file first
        load_env_file()
        
        self.telegram_enabled = telegram_enabled
        self.telegram_notifier = None
        self.health_checker = SystemHealthChecker()
        self.metrics_collector = MetricsCollector()
        
        # Initialize Telegram if enabled
        if telegram_enabled:
            try:
                self.telegram_notifier = TelegramNotifier()
                if not self.telegram_notifier.enabled:
                    logger.warning("Telegram notifier disabled due to missing configuration")
                    self.telegram_notifier = None
            except Exception as e:
                logger.error(f"Failed to initialize Telegram notifier: {e}")
                self.telegram_notifier = None
    
    async def send_signal_notification(
        self,
        ticker: str,
        signal_type: str,
        price: float,
        signal_value: int,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send signal notification to all channels.
        
        Args:
            ticker: Stock ticker
            signal_type: Type of signal
            price: Stock price
            signal_value: Signal value (1 for buy, -1 for sell)
            additional_data: Additional data
        """
        # Send to dashboard
        dashboard_alerts.add_signal_alert(
            ticker=ticker,
            signal_type=signal_type,
            price=price,
            signal_value=signal_value,
            additional_data=additional_data
        )
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_signal_notification(
                    ticker=ticker,
                    signal_type=signal_type,
                    price=price,
                    signal_value=signal_value,
                    additional_data=additional_data
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram signal notification: {e}")
    
    async def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        component: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send error notification to all channels.
        
        Args:
            error_type: Type of error
            error_message: Error message
            component: Component where error occurred
            additional_data: Additional data
        """
        # Send to dashboard
        dashboard_alerts.add_error_alert(
            error_type=error_type,
            error_message=error_message,
            component=component,
            additional_data=additional_data
        )
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_error_notification(
                    error_type=error_type,
                    error_message=error_message,
                    component=component,
                    additional_data=additional_data
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram error notification: {e}")
    
    async def send_critical_notification(
        self,
        critical_type: str,
        message: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send critical notification to all channels.
        
        Args:
            critical_type: Type of critical event
            message: Critical message
            additional_data: Additional data
        """
        # Send to dashboard
        dashboard_alerts.add_critical_alert(
            critical_type=critical_type,
            message=message,
            additional_data=additional_data
        )
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_critical_notification(
                    critical_type=critical_type,
                    message=message,
                    additional_data=additional_data
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram critical notification: {e}")
    
    async def send_trade_notification(
        self,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
        total_value: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send trade execution notification to all channels.
        
        Args:
            ticker: Stock ticker
            side: Trade side (BUY/SELL)
            quantity: Quantity traded
            price: Execution price
            total_value: Total trade value
            additional_data: Additional data
        """
        # Send to dashboard
        dashboard_alerts.add_trade_alert(
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price,
            total_value=total_value,
            additional_data=additional_data
        )
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_trade_executed(
                    ticker=ticker,
                    side=side,
                    quantity=quantity,
                    price=price,
                    total_value=total_value,
                    additional_data=additional_data
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram trade notification: {e}")
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run system health checks and send notifications.
        
        Returns:
            Health check results
        """
        try:
            # Run health checks
            results = await self.health_checker.run_all_checks()
            
            # Check for critical issues
            critical_components = self.health_checker.get_critical_components()
            if critical_components:
                await self.send_critical_notification(
                    critical_type="System Health",
                    message=f"Critical issues detected in: {', '.join(critical_components)}",
                    additional_data={"critical_components": critical_components}
                )
            
            # Check for warnings
            unhealthy_components = self.health_checker.get_unhealthy_components()
            if unhealthy_components:
                await self.send_error_notification(
                    error_type="System Warning",
                    error_message=f"Unhealthy components: {', '.join(unhealthy_components)}",
                    component="Health Checker",
                    additional_data={"unhealthy_components": unhealthy_components}
                )
            
            return self.health_checker.get_summary()
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            await self.send_error_notification(
                error_type="Health Check Error",
                error_message=str(e),
                component="Health Checker"
            )
            return {"error": str(e)}
    
    async def collect_and_analyze_metrics(self) -> Dict[str, Any]:
        """Collect system metrics and analyze for alerts.
        
        Returns:
            Metrics summary
        """
        try:
            # Collect metrics
            await self.metrics_collector.collect_metrics()
            
            # Get alerts from metrics
            alerts = self.metrics_collector.get_alerts()
            
            # Send alerts
            for alert in alerts:
                if alert["type"] == "critical":
                    await self.send_critical_notification(
                        critical_type=f"Metrics: {alert['component']}",
                        message=alert["message"],
                        additional_data=alert
                    )
                elif alert["type"] == "warning":
                    await self.send_error_notification(
                        error_type=f"Metrics Warning: {alert['component']}",
                        error_message=alert["message"],
                        component="Metrics Collector",
                        additional_data=alert
                    )
            
            return self.metrics_collector.get_metrics_summary()
            
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            await self.send_error_notification(
                error_type="Metrics Collection Error",
                error_message=str(e),
                component="Metrics Collector"
            )
            return {"error": str(e)}
    
    async def send_daily_report(self, report_data: Dict[str, Any]) -> None:
        """Send daily report to all channels.
        
        Args:
            report_data: Report data dictionary
        """
        # Send to dashboard
        from .message_formatter import MessageFormatter
        formatter = MessageFormatter()
        notification = formatter.format_daily_report_notification(report_data)
        dashboard_alerts.add_notification(notification)
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_daily_report(report_data)
            except Exception as e:
                logger.error(f"Failed to send Telegram daily report: {e}")
    
    async def send_health_check_notification(
        self,
        component: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send health check notification to all channels.
        
        Args:
            component: Component name
            status: Health status
            details: Health check details
            additional_data: Additional data
        """
        # Send to dashboard
        dashboard_alerts.add_health_check_alert(
            component=component,
            status=status,
            details=details,
            additional_data=additional_data
        )
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_health_check(
                    component=component,
                    status=status,
                    details=details,
                    additional_data=additional_data
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram health check notification: {e}")
    
    async def send_test_message(self) -> None:
        """Send a test message to all channels.
        
        This is useful for testing the notification system.
        """
        # Send to dashboard
        dashboard_alerts.add_signal_alert(
            ticker="TEST_MSG",
            signal_type="Test Message",
            price=100.0,
            signal_value=1,
            additional_data={"test_message": True}
        )
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_message("🧪 Тестовое сообщение системы уведомлений")
            except Exception as e:
                logger.error(f"Failed to send Telegram test message: {e}")
                raise
    
    # ML Notification Methods
    async def send_ml_signal_notification(
        self,
        symbol: str,
        signal_type: str,
        confidence: float,
        price_prediction: Optional[float] = None,
        sentiment: Optional[str] = None,
        risk_level: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send ML signal notification to all channels.
        
        Args:
            symbol: Stock symbol
            signal_type: Type of ML signal (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
            confidence: ML confidence level (0-1)
            price_prediction: Predicted price (optional)
            sentiment: Market sentiment (optional)
            risk_level: Risk level (optional)
            additional_data: Additional data
        """
        formatter = MessageFormatter()
        notification = formatter.format_ml_signal_notification(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            price_prediction=price_prediction,
            sentiment=sentiment,
            risk_level=risk_level,
            additional_data=additional_data
        )
        
        # Send to dashboard
        dashboard_alerts.add_notification(notification)
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_ml_signal(
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    price_prediction=price_prediction,
                    sentiment=sentiment,
                    risk_level=risk_level,
                    additional_data=additional_data
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram ML signal notification: {e}")
    
    async def send_ml_prediction_notification(
        self,
        symbol: str,
        current_price: float,
        predicted_price: float,
        confidence: float,
        direction: str,
        time_horizon: str = "1 day",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send ML prediction notification to all channels.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            predicted_price: ML predicted price
            confidence: ML confidence level (0-1)
            direction: Price direction (up/down)
            time_horizon: Prediction time horizon
            additional_data: Additional data
        """
        formatter = MessageFormatter()
        notification = formatter.format_ml_prediction_notification(
            symbol=symbol,
            current_price=current_price,
            predicted_price=predicted_price,
            confidence=confidence,
            direction=direction,
            time_horizon=time_horizon,
            additional_data=additional_data
        )
        
        # Send to dashboard
        dashboard_alerts.add_notification(notification)
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_ml_prediction(
                    symbol=symbol,
                    current_price=current_price,
                    predicted_price=predicted_price,
                    confidence=confidence,
                    direction=direction,
                    time_horizon=time_horizon,
                    additional_data=additional_data
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram ML prediction notification: {e}")
    
    async def send_ml_sentiment_notification(
        self,
        symbol: str,
        sentiment: str,
        confidence: float,
        news_count: int,
        sentiment_score: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send ML sentiment notification to all channels.
        
        Args:
            symbol: Stock symbol
            sentiment: Market sentiment (positive/negative/neutral)
            confidence: ML confidence level (0-1)
            news_count: Number of news articles analyzed
            sentiment_score: Sentiment score (-1 to 1)
            additional_data: Additional data
        """
        formatter = MessageFormatter()
        notification = formatter.format_ml_sentiment_notification(
            symbol=symbol,
            sentiment=sentiment,
            confidence=confidence,
            news_count=news_count,
            sentiment_score=sentiment_score,
            additional_data=additional_data
        )
        
        # Send to dashboard
        dashboard_alerts.add_notification(notification)
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_ml_sentiment(
                    symbol=symbol,
                    sentiment=sentiment,
                    confidence=confidence,
                    news_count=news_count,
                    sentiment_score=sentiment_score,
                    additional_data=additional_data
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram ML sentiment notification: {e}")
    
    async def send_ml_alert_notification(
        self,
        alert_type: str,
        message: str,
        symbols: Optional[List[str]] = None,
        severity: str = "medium",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send ML alert notification to all channels.
        
        Args:
            alert_type: Type of ML alert
            message: Alert message
            symbols: Affected symbols (optional)
            severity: Alert severity (low/medium/high/critical)
            additional_data: Additional data
        """
        formatter = MessageFormatter()
        notification = formatter.format_ml_alert_notification(
            alert_type=alert_type,
            message=message,
            symbols=symbols,
            severity=severity,
            additional_data=additional_data
        )
        
        # Send to dashboard
        dashboard_alerts.add_notification(notification)
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_ml_alert(
                    alert_type=alert_type,
                    message=message,
                    symbols=symbols,
                    severity=severity,
                    additional_data=additional_data
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram ML alert notification: {e}")
    
    async def send_ml_analysis_notification(
        self,
        analysis_type: str,
        summary: str,
        key_findings: List[str],
        recommendations: Optional[List[str]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send ML analysis notification to all channels.
        
        Args:
            analysis_type: Type of ML analysis
            summary: Analysis summary
            key_findings: Key findings list
            recommendations: Recommendations list (optional)
            additional_data: Additional data
        """
        formatter = MessageFormatter()
        notification = formatter.format_ml_analysis_notification(
            analysis_type=analysis_type,
            summary=summary,
            key_findings=key_findings,
            recommendations=recommendations,
            additional_data=additional_data
        )
        
        # Send to dashboard
        dashboard_alerts.add_notification(notification)
        
        # Send to Telegram
        if self.telegram_notifier:
            try:
                await self.telegram_notifier.send_ml_analysis(
                    analysis_type=analysis_type,
                    summary=summary,
                    key_findings=key_findings,
                    recommendations=recommendations,
                    additional_data=additional_data
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram ML analysis notification: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get notification manager status.
        
        Returns:
            Status dictionary
        """
        status = {
            "telegram_enabled": self.telegram_enabled,
            "telegram_configured": self.telegram_notifier is not None and self.telegram_notifier.enabled,
            "health_checker_available": True,
            "metrics_collector_available": True,
        }
        
        if self.telegram_notifier:
            status["telegram_status"] = self.telegram_notifier.get_status()
        
        return status
    
    async def test_all_channels(self) -> Dict[str, bool]:
        """Test all notification channels.
        
        Returns:
            Dictionary with test results for each channel
        """
        results = {}
        
        # Test dashboard
        try:
            dashboard_alerts.add_signal_alert(
                ticker="TEST",
                signal_type="Test Signal",
                price=100.0,
                signal_value=1,
                additional_data={"test": True}
            )
            results["dashboard"] = True
        except Exception as e:
            logger.error(f"Dashboard test failed: {e}")
            results["dashboard"] = False
        
        # Test Telegram
        if self.telegram_notifier:
            try:
                results["telegram"] = await self.telegram_notifier.test_connection()
            except Exception as e:
                logger.error(f"Telegram test failed: {e}")
                results["telegram"] = False
        else:
            results["telegram"] = False
        
        return results


# Global notification manager instance
notification_manager = NotificationManager()


# Convenience functions for easy integration
async def notify_signal(
    ticker: str,
    signal_type: str,
    price: float,
    signal_value: int,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function to send signal notification.
    
    Args:
        ticker: Stock ticker
        signal_type: Type of signal
        price: Stock price
        signal_value: Signal value (1 for buy, -1 for sell)
        additional_data: Additional data
    """
    await notification_manager.send_signal_notification(
        ticker=ticker,
        signal_type=signal_type,
        price=price,
        signal_value=signal_value,
        additional_data=additional_data
    )


async def notify_error(
    error_type: str,
    error_message: str,
    component: str,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function to send error notification.
    
    Args:
        error_type: Type of error
        error_message: Error message
        component: Component where error occurred
        additional_data: Additional data
    """
    await notification_manager.send_error_notification(
        error_type=error_type,
        error_message=error_message,
        component=component,
        additional_data=additional_data
    )


async def notify_critical(
    critical_type: str,
    message: str,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function to send critical notification.
    
    Args:
        critical_type: Type of critical event
        message: Critical message
        additional_data: Additional data
    """
    await notification_manager.send_critical_notification(
        critical_type=critical_type,
        message=message,
        additional_data=additional_data
    )


async def notify_trade(
    ticker: str,
    side: str,
    quantity: int,
    price: float,
    total_value: float,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function to send trade notification.
    
    Args:
        ticker: Stock ticker
        side: Trade side (BUY/SELL)
        quantity: Quantity traded
        price: Execution price
        total_value: Total trade value
        additional_data: Additional data
    """
    await notification_manager.send_trade_notification(
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        total_value=total_value,
        additional_data=additional_data
    )


# ML Notification Convenience Functions
async def notify_ml_signal(
    symbol: str,
    signal_type: str,
    confidence: float,
    price_prediction: Optional[float] = None,
    sentiment: Optional[str] = None,
    risk_level: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function to send ML signal notification.
    
    Args:
        symbol: Stock symbol
        signal_type: Type of ML signal (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
        confidence: ML confidence level (0-1)
        price_prediction: Predicted price (optional)
        sentiment: Market sentiment (optional)
        risk_level: Risk level (optional)
        additional_data: Additional data
    """
    await notification_manager.send_ml_signal_notification(
        symbol=symbol,
        signal_type=signal_type,
        confidence=confidence,
        price_prediction=price_prediction,
        sentiment=sentiment,
        risk_level=risk_level,
        additional_data=additional_data
    )


async def notify_ml_prediction(
    symbol: str,
    current_price: float,
    predicted_price: float,
    confidence: float,
    direction: str,
    time_horizon: str = "1 day",
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function to send ML prediction notification.
    
    Args:
        symbol: Stock symbol
        current_price: Current stock price
        predicted_price: ML predicted price
        confidence: ML confidence level (0-1)
        direction: Price direction (up/down)
        time_horizon: Prediction time horizon
        additional_data: Additional data
    """
    await notification_manager.send_ml_prediction_notification(
        symbol=symbol,
        current_price=current_price,
        predicted_price=predicted_price,
        confidence=confidence,
        direction=direction,
        time_horizon=time_horizon,
        additional_data=additional_data
    )


async def notify_ml_sentiment(
    symbol: str,
    sentiment: str,
    confidence: float,
    news_count: int,
    sentiment_score: float,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function to send ML sentiment notification.
    
    Args:
        symbol: Stock symbol
        sentiment: Market sentiment (positive/negative/neutral)
        confidence: ML confidence level (0-1)
        news_count: Number of news articles analyzed
        sentiment_score: Sentiment score (-1 to 1)
        additional_data: Additional data
    """
    await notification_manager.send_ml_sentiment_notification(
        symbol=symbol,
        sentiment=sentiment,
        confidence=confidence,
        news_count=news_count,
        sentiment_score=sentiment_score,
        additional_data=additional_data
    )


async def notify_ml_alert(
    alert_type: str,
    message: str,
    symbols: Optional[List[str]] = None,
    severity: str = "medium",
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function to send ML alert notification.
    
    Args:
        alert_type: Type of ML alert
        message: Alert message
        symbols: Affected symbols (optional)
        severity: Alert severity (low/medium/high/critical)
        additional_data: Additional data
    """
    await notification_manager.send_ml_alert_notification(
        alert_type=alert_type,
        message=message,
        symbols=symbols,
        severity=severity,
        additional_data=additional_data
    )


async def notify_ml_analysis(
    analysis_type: str,
    summary: str,
    key_findings: List[str],
    recommendations: Optional[List[str]] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function to send ML analysis notification.
    
    Args:
        analysis_type: Type of ML analysis
        summary: Analysis summary
        key_findings: Key findings list
        recommendations: Recommendations list (optional)
        additional_data: Additional data
    """
    await notification_manager.send_ml_analysis_notification(
        analysis_type=analysis_type,
        summary=summary,
        key_findings=key_findings,
        recommendations=recommendations,
        additional_data=additional_data
    )

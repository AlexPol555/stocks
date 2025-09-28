"""Message formatter for different types of notifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union
import json


class NotificationType(Enum):
    """Types of notifications supported by the system."""
    
    SIGNAL = "signal"
    ERROR = "error"
    CRITICAL = "critical"
    DAILY_REPORT = "daily_report"
    SYSTEM_ALERT = "system_alert"
    TRADE_EXECUTED = "trade_executed"
    HEALTH_CHECK = "health_check"
    # ML Notifications
    ML_SIGNAL = "ml_signal"
    ML_PREDICTION = "ml_prediction"
    ML_SENTIMENT = "ml_sentiment"
    ML_ALERT = "ml_alert"
    ML_ANALYSIS = "ml_analysis"


@dataclass
class NotificationData:
    """Data structure for notification content."""
    
    type: NotificationType
    title: str
    message: str
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None
    priority: int = 1  # 1=low, 2=medium, 3=high, 4=critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data or {},
            "priority": self.priority,
        }


class MessageFormatter:
    """Formats notifications into different message formats."""
    
    def __init__(self):
        self.emoji_map = {
            NotificationType.SIGNAL: "📊",
            NotificationType.ERROR: "❌",
            NotificationType.CRITICAL: "🚨",
            NotificationType.DAILY_REPORT: "📈",
            NotificationType.SYSTEM_ALERT: "⚠️",
            NotificationType.TRADE_EXECUTED: "💰",
            NotificationType.HEALTH_CHECK: "🔍",
        }
        
        self.priority_colors = {
            1: "🟢",  # low
            2: "🟡",  # medium
            3: "🟠",  # high
            4: "🔴",  # critical
        }
    
    def format_telegram(self, notification: NotificationData) -> str:
        """Format notification for Telegram."""
        emoji = self.emoji_map.get(notification.type, "📢")
        priority_icon = self.priority_colors.get(notification.priority, "🟢")
        
        # Format timestamp
        time_str = notification.timestamp.strftime("%H:%M:%S")
        date_str = notification.timestamp.strftime("%d.%m.%Y")
        
        # Escape special characters for Markdown
        def escape_markdown(text):
            if not isinstance(text, str):
                text = str(text)
            # Escape special Markdown characters
            special_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in special_chars:
                text = text.replace(char, f'\\{char}')
            return text
        
        # Build message
        lines = [
            f"{emoji} *{escape_markdown(notification.title)}*",
            f"{priority_icon} {time_str} | {date_str}",
            "",
            escape_markdown(notification.message),
        ]
        
        # Add additional data if present
        if notification.data:
            lines.append("")
            lines.append("📋 *Детали:*")
            for key, value in notification.data.items():
                if isinstance(value, (int, float)):
                    if isinstance(value, float):
                        value = f"{value:.2f}"
                    lines.append(f"• {escape_markdown(str(key))}: `{escape_markdown(str(value))}`")
                else:
                    lines.append(f"• {escape_markdown(str(key))}: {escape_markdown(str(value))}")
        
        return "\n".join(lines)
    
    def format_dashboard(self, notification: NotificationData) -> Dict[str, Any]:
        """Format notification for dashboard display."""
        emoji = self.emoji_map.get(notification.type, "📢")
        priority_icon = self.priority_colors.get(notification.priority, "🟢")
        
        return {
            "id": f"{notification.type.value}_{notification.timestamp.timestamp()}",
            "type": notification.type.value,
            "title": f"{emoji} {notification.title}",
            "message": notification.message,
            "timestamp": notification.timestamp,
            "priority": notification.priority,
            "priority_icon": priority_icon,
            "data": notification.data or {},
            "is_read": False,
        }
    
    def format_signal_notification(
        self,
        ticker: str,
        signal_type: str,
        price: float,
        signal_value: int,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format a trading signal notification."""
        
        signal_emoji = "🟢" if signal_value > 0 else "🔴"
        signal_text = "ПОКУПКА" if signal_value > 0 else "ПРОДАЖА"
        
        title = f"Сигнал {signal_type}"
        message = f"{signal_emoji} {ticker}: {signal_text} по цене {price:.2f}"
        
        data = {
            "ticker": ticker,
            "signal_type": signal_type,
            "price": price,
            "signal_value": signal_value,
            **(additional_data or {})
        }
        
        return NotificationData(
            type=NotificationType.SIGNAL,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=3,  # High priority for signals
        )
    
    def format_error_notification(
        self,
        error_type: str,
        error_message: str,
        component: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format an error notification."""
        
        title = f"Ошибка в {component}"
        message = f"{error_type}: {error_message}"
        
        data = {
            "error_type": error_type,
            "component": component,
            "error_message": error_message,
            **(additional_data or {})
        }
        
        return NotificationData(
            type=NotificationType.ERROR,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=2,  # Medium priority for errors
        )
    
    def format_critical_notification(
        self,
        critical_type: str,
        message: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format a critical system notification."""
        
        title = f"КРИТИЧЕСКОЕ СОБЫТИЕ: {critical_type}"
        
        data = {
            "critical_type": critical_type,
            **(additional_data or {})
        }
        
        return NotificationData(
            type=NotificationType.CRITICAL,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=4,  # Critical priority
        )
    
    def format_daily_report_notification(
        self,
        report_data: Dict[str, Any],
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format a daily report notification."""
        
        title = "Ежедневный отчет"
        
        # Build report message
        lines = []
        if "total_signals" in report_data:
            lines.append(f"📊 Всего сигналов: {report_data['total_signals']}")
        if "trades_executed" in report_data:
            lines.append(f"💰 Сделок выполнено: {report_data['trades_executed']}")
        if "profit_loss" in report_data:
            pnl = report_data['profit_loss']
            pnl_emoji = "📈" if pnl >= 0 else "📉"
            lines.append(f"{pnl_emoji} P/L: {pnl:.2f}")
        if "active_positions" in report_data:
            lines.append(f"📋 Активных позиций: {report_data['active_positions']}")
        
        message = "\n".join(lines) if lines else "Нет данных для отчета"
        
        data = {
            "report_data": report_data,
            **(additional_data or {})
        }
        
        return NotificationData(
            type=NotificationType.DAILY_REPORT,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=1,  # Low priority for daily reports
        )
    
    def format_trade_executed_notification(
        self,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
        total_value: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format a trade execution notification."""
        
        side_emoji = "🟢" if side.upper() == "BUY" else "🔴"
        side_text = "ПОКУПКА" if side.upper() == "BUY" else "ПРОДАЖА"
        
        title = "Сделка выполнена"
        message = f"{side_emoji} {ticker}: {side_text} {quantity} шт. по {price:.2f} (сумма: {total_value:.2f})"
        
        data = {
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "price": price,
            "total_value": total_value,
            **(additional_data or {})
        }
        
        return NotificationData(
            type=NotificationType.TRADE_EXECUTED,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=3,  # High priority for trades
        )
    
    def format_health_check_notification(
        self,
        component: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format a health check notification."""
        
        status_emoji = "✅" if status == "healthy" else "❌"
        
        title = f"Health Check: {component}"
        message = f"{status_emoji} Статус: {status}"
        
        if details:
            detail_lines = []
            for key, value in details.items():
                detail_lines.append(f"• {key}: {value}")
            message += "\n\n" + "\n".join(detail_lines)
        
        data = {
            "component": component,
            "status": status,
            "details": details or {},
            **(additional_data or {})
        }
        
        return NotificationData(
            type=NotificationType.HEALTH_CHECK,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=1 if status == "healthy" else 2,
        )
    
    # Dashboard compatibility methods that return dictionaries
    def format_signal(self, ticker: str, signal_type: str, price: float, signal_value: int, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format signal notification for dashboard (returns dict)."""
        notification = self.format_signal_notification(ticker, signal_type, price, signal_value, additional_data)
        return self.format_dashboard(notification)
    
    def format_error(self, error_type: str, error_message: str, component: str, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format error notification for dashboard (returns dict)."""
        notification = self.format_error_notification(error_type, error_message, component, additional_data)
        return self.format_dashboard(notification)
    
    def format_critical(self, critical_type: str, message: str, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format critical notification for dashboard (returns dict)."""
        notification = self.format_critical_notification(critical_type, message, additional_data)
        return self.format_dashboard(notification)
    
    def format_trade_executed(self, ticker: str, side: str, quantity: int, price: float, total_value: float, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format trade notification for dashboard (returns dict)."""
        notification = self.format_trade_executed_notification(ticker, side, quantity, price, total_value, additional_data)
        return self.format_dashboard(notification)
    
    def format_daily_report(self, report_data: Dict[str, Any], additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format daily report notification for dashboard (returns dict)."""
        notification = self.format_daily_report_notification(report_data, additional_data)
        return self.format_dashboard(notification)
    
    # ML Notification Methods
    def format_ml_signal_notification(
        self,
        symbol: str,
        signal_type: str,
        confidence: float,
        price_prediction: Optional[float] = None,
        sentiment: Optional[str] = None,
        risk_level: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format ML signal notification."""
        
        # Signal emoji mapping
        signal_emojis = {
            'STRONG_BUY': '🚀',
            'BUY': '📈',
            'HOLD': '⏸️',
            'SELL': '📉',
            'STRONG_SELL': '💥'
        }
        
        emoji = signal_emojis.get(signal_type, '🤖')
        title = f"{emoji} ML Signal: {symbol}"
        
        # Build message
        lines = [f"🤖 ML Signal: {signal_type}"]
        lines.append(f"📊 Confidence: {confidence:.1%}")
        
        if price_prediction:
            lines.append(f"💰 Predicted Price: {price_prediction:.2f}")
        
        if sentiment:
            sentiment_emoji = {'positive': '😊', 'negative': '😞', 'neutral': '😐'}.get(sentiment, '🤔')
            lines.append(f"{sentiment_emoji} Sentiment: {sentiment.title()}")
        
        if risk_level:
            risk_emoji = {'LOW': '🟢', 'MEDIUM': '🟡', 'HIGH': '🔴'}.get(risk_level, '⚪')
            lines.append(f"{risk_emoji} Risk: {risk_level}")
        
        message = "\n".join(lines)
        
        data = {
            "symbol": symbol,
            "signal_type": signal_type,
            "confidence": confidence,
            "price_prediction": price_prediction,
            "sentiment": sentiment,
            "risk_level": risk_level,
            **(additional_data or {})
        }
        
        # Priority based on signal strength
        priority = 3 if signal_type in ['STRONG_BUY', 'STRONG_SELL'] else 2
        
        return NotificationData(
            type=NotificationType.ML_SIGNAL,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=priority,
        )
    
    def format_ml_prediction_notification(
        self,
        symbol: str,
        current_price: float,
        predicted_price: float,
        confidence: float,
        direction: str,
        time_horizon: str = "1 day",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format ML price prediction notification."""
        
        price_change = predicted_price - current_price
        price_change_pct = (price_change / current_price) * 100
        
        direction_emoji = "📈" if price_change > 0 else "📉" if price_change < 0 else "➡️"
        title = f"{direction_emoji} ML Prediction: {symbol}"
        
        message = f"""🤖 ML Price Prediction
        
💰 Current: {current_price:.2f}
🎯 Predicted: {predicted_price:.2f}
📊 Change: {price_change:+.2f} ({price_change_pct:+.1f}%)
🎯 Direction: {direction.title()}
⏰ Horizon: {time_horizon}
🎯 Confidence: {confidence:.1%}"""
        
        data = {
            "symbol": symbol,
            "current_price": current_price,
            "predicted_price": predicted_price,
            "price_change": price_change,
            "price_change_pct": price_change_pct,
            "direction": direction,
            "confidence": confidence,
            "time_horizon": time_horizon,
            **(additional_data or {})
        }
        
        return NotificationData(
            type=NotificationType.ML_PREDICTION,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=2,
        )
    
    def format_ml_sentiment_notification(
        self,
        symbol: str,
        sentiment: str,
        confidence: float,
        news_count: int,
        sentiment_score: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format ML sentiment analysis notification."""
        
        sentiment_emojis = {
            'positive': '😊',
            'negative': '😞', 
            'neutral': '😐'
        }
        
        emoji = sentiment_emojis.get(sentiment, '🤔')
        title = f"{emoji} ML Sentiment: {symbol}"
        
        message = f"""🤖 ML Sentiment Analysis
        
📰 News Analyzed: {news_count}
😊 Sentiment: {sentiment.title()}
📊 Score: {sentiment_score:.2f}
🎯 Confidence: {confidence:.1%}"""
        
        data = {
            "symbol": symbol,
            "sentiment": sentiment,
            "confidence": confidence,
            "news_count": news_count,
            "sentiment_score": sentiment_score,
            **(additional_data or {})
        }
        
        return NotificationData(
            type=NotificationType.ML_SENTIMENT,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=1,
        )
    
    def format_ml_alert_notification(
        self,
        alert_type: str,
        message: str,
        symbols: Optional[List[str]] = None,
        severity: str = "medium",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format ML alert notification."""
        
        severity_emojis = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴',
            'critical': '🚨'
        }
        
        emoji = severity_emojis.get(severity, '⚠️')
        title = f"{emoji} ML Alert: {alert_type}"
        
        if symbols:
            symbols_str = ", ".join(symbols[:5])  # Show first 5 symbols
            if len(symbols) > 5:
                symbols_str += f" (+{len(symbols) - 5} more)"
            message = f"{message}\n\n📊 Affected Symbols: {symbols_str}"
        
        data = {
            "alert_type": alert_type,
            "severity": severity,
            "symbols": symbols or [],
            **(additional_data or {})
        }
        
        # Priority based on severity
        priority_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        priority = priority_map.get(severity, 2)
        
        return NotificationData(
            type=NotificationType.ML_ALERT,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=priority,
        )
    
    def format_ml_analysis_notification(
        self,
        analysis_type: str,
        summary: str,
        key_findings: List[str],
        recommendations: Optional[List[str]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationData:
        """Format ML analysis notification."""
        
        title = f"🤖 ML Analysis: {analysis_type}"
        
        message_lines = [f"📊 Analysis: {analysis_type}", f"📝 Summary: {summary}"]
        
        if key_findings:
            message_lines.append("\n🔍 Key Findings:")
            for finding in key_findings:
                message_lines.append(f"• {finding}")
        
        if recommendations:
            message_lines.append("\n💡 Recommendations:")
            for rec in recommendations:
                message_lines.append(f"• {rec}")
        
        message = "\n".join(message_lines)
        
        data = {
            "analysis_type": analysis_type,
            "summary": summary,
            "key_findings": key_findings,
            "recommendations": recommendations or [],
            **(additional_data or {})
        }
        
        return NotificationData(
            type=NotificationType.ML_ANALYSIS,
            title=title,
            message=message,
            timestamp=datetime.now(),
            data=data,
            priority=2,
        )
    
    # Dashboard compatibility methods for ML notifications
    def format_ml_signal(self, symbol: str, signal_type: str, confidence: float, **kwargs) -> Dict[str, Any]:
        """Format ML signal notification for dashboard (returns dict)."""
        notification = self.format_ml_signal_notification(symbol, signal_type, confidence, **kwargs)
        return self.format_dashboard(notification)
    
    def format_ml_prediction(self, symbol: str, current_price: float, predicted_price: float, confidence: float, **kwargs) -> Dict[str, Any]:
        """Format ML prediction notification for dashboard (returns dict)."""
        notification = self.format_ml_prediction_notification(symbol, current_price, predicted_price, confidence, **kwargs)
        return self.format_dashboard(notification)
    
    def format_ml_sentiment(self, symbol: str, sentiment: str, confidence: float, **kwargs) -> Dict[str, Any]:
        """Format ML sentiment notification for dashboard (returns dict)."""
        notification = self.format_ml_sentiment_notification(symbol, sentiment, confidence, **kwargs)
        return self.format_dashboard(notification)
    
    def format_ml_alert(self, alert_type: str, message: str, **kwargs) -> Dict[str, Any]:
        """Format ML alert notification for dashboard (returns dict)."""
        notification = self.format_ml_alert_notification(alert_type, message, **kwargs)
        return self.format_dashboard(notification)
    
    def format_ml_analysis(self, analysis_type: str, summary: str, key_findings: List[str], **kwargs) -> Dict[str, Any]:
        """Format ML analysis notification for dashboard (returns dict)."""
        notification = self.format_ml_analysis_notification(analysis_type, summary, key_findings, **kwargs)
        return self.format_dashboard(notification)
    
    def format_health_check(self, component: str, status: str, details: Optional[Dict[str, Any]] = None, additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format health check notification for dashboard (returns dict)."""
        notification = self.format_health_check_notification(component, status, details, additional_data)
        return self.format_dashboard(notification)

"""ML Notifications integration module.

This module provides integration between ML system and notifications,
automatically sending notifications for ML signals, predictions, and alerts.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..notifications import (
    notify_ml_signal,
    notify_ml_prediction,
    notify_ml_sentiment,
    notify_ml_alert,
    notify_ml_analysis
)

logger = logging.getLogger(__name__)


class MLNotificationManager:
    """Manages ML-specific notifications."""
    
    def __init__(self, enabled: bool = True):
        """Initialize ML notification manager.
        
        Args:
            enabled: Whether to enable ML notifications
        """
        self.enabled = enabled
        self.notification_thresholds = {
            'confidence_threshold': 0.7,  # Only notify for high confidence signals
            'sentiment_threshold': 0.6,   # Only notify for strong sentiment
            'prediction_threshold': 0.05, # Only notify for significant price changes
        }
        
    async def notify_ml_signal_if_worthy(
        self,
        symbol: str,
        signal_type: str,
        confidence: float,
        price_prediction: Optional[float] = None,
        sentiment: Optional[str] = None,
        risk_level: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send ML signal notification if it meets quality thresholds.
        
        Args:
            symbol: Stock symbol
            signal_type: Type of ML signal
            confidence: ML confidence level (0-1)
            price_prediction: Predicted price (optional)
            sentiment: Market sentiment (optional)
            risk_level: Risk level (optional)
            additional_data: Additional data
            
        Returns:
            True if notification was sent, False otherwise
        """
        if not self.enabled:
            return False
            
        # Check if signal meets quality thresholds
        if confidence < self.notification_thresholds['confidence_threshold']:
            logger.debug(f"ML signal for {symbol} below confidence threshold: {confidence:.2f}")
            return False
            
        # Always notify for strong signals regardless of confidence
        if signal_type in ['STRONG_BUY', 'STRONG_SELL']:
            logger.info(f"Sending ML signal notification for {symbol}: {signal_type}")
            await notify_ml_signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price_prediction=price_prediction,
                sentiment=sentiment,
                risk_level=risk_level,
                additional_data=additional_data
            )
            return True
            
        # For other signals, check confidence threshold
        if confidence >= self.notification_thresholds['confidence_threshold']:
            logger.info(f"Sending ML signal notification for {symbol}: {signal_type}")
            await notify_ml_signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price_prediction=price_prediction,
                sentiment=sentiment,
                risk_level=risk_level,
                additional_data=additional_data
            )
            return True
            
        return False
    
    async def notify_ml_prediction_if_worthy(
        self,
        symbol: str,
        current_price: float,
        predicted_price: float,
        confidence: float,
        direction: str,
        time_horizon: str = "1 day",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send ML prediction notification if it meets quality thresholds.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            predicted_price: ML predicted price
            confidence: ML confidence level (0-1)
            direction: Price direction (up/down)
            time_horizon: Prediction time horizon
            additional_data: Additional data
            
        Returns:
            True if notification was sent, False otherwise
        """
        if not self.enabled:
            return False
            
        # Calculate price change percentage
        price_change_pct = abs((predicted_price - current_price) / current_price)
        
        # Check if prediction meets quality thresholds
        if (confidence < self.notification_thresholds['confidence_threshold'] or 
            price_change_pct < self.notification_thresholds['prediction_threshold']):
            logger.debug(f"ML prediction for {symbol} below thresholds: confidence={confidence:.2f}, change={price_change_pct:.2%}")
            return False
            
        logger.info(f"Sending ML prediction notification for {symbol}: {direction} {price_change_pct:.1%}")
        await notify_ml_prediction(
            symbol=symbol,
            current_price=current_price,
            predicted_price=predicted_price,
            confidence=confidence,
            direction=direction,
            time_horizon=time_horizon,
            additional_data=additional_data
        )
        return True
    
    async def notify_ml_sentiment_if_worthy(
        self,
        symbol: str,
        sentiment: str,
        confidence: float,
        news_count: int,
        sentiment_score: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send ML sentiment notification if it meets quality thresholds.
        
        Args:
            symbol: Stock symbol
            sentiment: Market sentiment (positive/negative/neutral)
            confidence: ML confidence level (0-1)
            news_count: Number of news articles analyzed
            sentiment_score: Sentiment score (-1 to 1)
            additional_data: Additional data
            
        Returns:
            True if notification was sent, False otherwise
        """
        if not self.enabled:
            return False
            
        # Check if sentiment meets quality thresholds
        if (confidence < self.notification_thresholds['sentiment_threshold'] or 
            abs(sentiment_score) < 0.3):  # Only notify for strong sentiment
            logger.debug(f"ML sentiment for {symbol} below thresholds: confidence={confidence:.2f}, score={sentiment_score:.2f}")
            return False
            
        logger.info(f"Sending ML sentiment notification for {symbol}: {sentiment}")
        await notify_ml_sentiment(
            symbol=symbol,
            sentiment=sentiment,
            confidence=confidence,
            news_count=news_count,
            sentiment_score=sentiment_score,
            additional_data=additional_data
        )
        return True
    
    async def notify_ml_alert(
        self,
        alert_type: str,
        message: str,
        symbols: Optional[List[str]] = None,
        severity: str = "medium",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send ML alert notification.
        
        Args:
            alert_type: Type of ML alert
            message: Alert message
            symbols: Affected symbols (optional)
            severity: Alert severity (low/medium/high/critical)
            additional_data: Additional data
        """
        if not self.enabled:
            return
            
        logger.info(f"Sending ML alert notification: {alert_type}")
        await notify_ml_alert(
            alert_type=alert_type,
            message=message,
            symbols=symbols,
            severity=severity,
            additional_data=additional_data
        )
    
    async def notify_ml_analysis(
        self,
        analysis_type: str,
        summary: str,
        key_findings: List[str],
        recommendations: Optional[List[str]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send ML analysis notification.
        
        Args:
            analysis_type: Type of ML analysis
            summary: Analysis summary
            key_findings: Key findings list
            recommendations: Recommendations list (optional)
            additional_data: Additional data
        """
        if not self.enabled:
            return
            
        logger.info(f"Sending ML analysis notification: {analysis_type}")
        await notify_ml_analysis(
            analysis_type=analysis_type,
            summary=summary,
            key_findings=key_findings,
            recommendations=recommendations,
            additional_data=additional_data
        )
    
    def set_thresholds(
        self,
        confidence_threshold: Optional[float] = None,
        sentiment_threshold: Optional[float] = None,
        prediction_threshold: Optional[float] = None
    ) -> None:
        """Update notification thresholds.
        
        Args:
            confidence_threshold: Minimum confidence for notifications
            sentiment_threshold: Minimum sentiment strength for notifications
            prediction_threshold: Minimum price change for prediction notifications
        """
        if confidence_threshold is not None:
            self.notification_thresholds['confidence_threshold'] = confidence_threshold
        if sentiment_threshold is not None:
            self.notification_thresholds['sentiment_threshold'] = sentiment_threshold
        if prediction_threshold is not None:
            self.notification_thresholds['prediction_threshold'] = prediction_threshold
            
        logger.info(f"Updated ML notification thresholds: {self.notification_thresholds}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get ML notification manager status.
        
        Returns:
            Status dictionary
        """
        return {
            "enabled": self.enabled,
            "thresholds": self.notification_thresholds,
            "timestamp": datetime.now().isoformat()
        }


# Global ML notification manager instance
ml_notification_manager = MLNotificationManager()


# Convenience functions
async def notify_ml_signal_if_worthy(
    symbol: str,
    signal_type: str,
    confidence: float,
    **kwargs
) -> bool:
    """Convenience function to send ML signal notification if worthy."""
    return await ml_notification_manager.notify_ml_signal_if_worthy(
        symbol=symbol,
        signal_type=signal_type,
        confidence=confidence,
        **kwargs
    )


async def notify_ml_prediction_if_worthy(
    symbol: str,
    current_price: float,
    predicted_price: float,
    confidence: float,
    **kwargs
) -> bool:
    """Convenience function to send ML prediction notification if worthy."""
    return await ml_notification_manager.notify_ml_prediction_if_worthy(
        symbol=symbol,
        current_price=current_price,
        predicted_price=predicted_price,
        confidence=confidence,
        **kwargs
    )


async def notify_ml_sentiment_if_worthy(
    symbol: str,
    sentiment: str,
    confidence: float,
    news_count: int,
    sentiment_score: float,
    **kwargs
) -> bool:
    """Convenience function to send ML sentiment notification if worthy."""
    return await ml_notification_manager.notify_ml_sentiment_if_worthy(
        symbol=symbol,
        sentiment=sentiment,
        confidence=confidence,
        news_count=news_count,
        sentiment_score=sentiment_score,
        **kwargs
    )

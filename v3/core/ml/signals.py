#!/usr/bin/env python3
"""ML-based trading signals generation."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np

from .notifications import ml_notification_manager
from .cache import ml_cache_manager

logger = logging.getLogger(__name__)

class MLSignalGenerator:
    """Generate ML-based trading signals."""
    
    def __init__(self, ml_manager):
        self.ml_manager = ml_manager
        self.signal_cache = {}
        
    async def generate_ml_signals(self, symbol: str, days_back: int = 30) -> Dict[str, Any]:
        """Generate comprehensive ML signals for a symbol."""
        try:
            # Get stock data
            stock_data = self.ml_manager._get_stock_data_from_db(symbol, '1d')
            if stock_data.empty:
                return {'error': f'No data available for {symbol}'}
            
            signals = {}
            
            # 1. Price Prediction Signal
            prediction_result = self.ml_manager.predict_price_movement(symbol)
            if 'prediction' in prediction_result:
                pred = prediction_result['prediction']
                signals['ml_price_signal'] = self._interpret_price_prediction(pred)
                # Handle both dict and numpy object cases
                if isinstance(pred, dict):
                    signals['ml_price_confidence'] = pred.get('confidence', 0.0)
                    signals['ml_price_direction'] = pred.get('direction', 'neutral')
                else:
                    signals['ml_price_confidence'] = getattr(pred, 'confidence', 0.0)
                    signals['ml_price_direction'] = getattr(pred, 'direction', 'neutral')
            
            # 2. Sentiment Signal
            sentiment_result = self.ml_manager.analyze_market_sentiment(days_back)
            if 'overall_sentiment' in sentiment_result:
                signals['ml_sentiment_signal'] = self._interpret_sentiment(sentiment_result['overall_sentiment'])
                signals['ml_sentiment_confidence'] = sentiment_result.get('confidence', 0.0)
            
            # 3. Technical ML Signal (based on technical indicators)
            tech_signal = self._generate_technical_ml_signal(stock_data)
            signals.update(tech_signal)
            
            # 4. Ensemble Signal (combine all signals)
            ensemble_signal = self._generate_ensemble_signal(signals)
            signals['ml_ensemble_signal'] = ensemble_signal
            
            # 5. Risk Assessment
            risk_assessment = self._assess_ml_risk(stock_data, signals)
            signals.update(risk_assessment)
            
            signals['symbol'] = symbol
            signals['timestamp'] = datetime.now().isoformat()
            signals['data_points'] = len(stock_data)
            
            # Send notifications for worthy signals
            try:
                await self._send_ml_notifications(symbol, signals)
            except Exception as e:
                logger.error(f"Failed to send ML notifications for {symbol}: {e}")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating ML signals for {symbol}: {e}")
            return {'error': str(e)}
    
    def _interpret_price_prediction(self, prediction) -> str:
        """Convert price prediction to trading signal."""
        # Handle both dict and numpy object cases
        if isinstance(prediction, dict):
            direction = prediction.get('direction', 'neutral')
            confidence = prediction.get('confidence', 0.0)
        else:
            direction = getattr(prediction, 'direction', 'neutral')
            confidence = getattr(prediction, 'confidence', 0.0)
        
        if confidence < 0.3:
            return 'HOLD'
        elif direction == 'up' and confidence >= 0.6:
            return 'STRONG_BUY'
        elif direction == 'up' and confidence >= 0.4:
            return 'BUY'
        elif direction == 'down' and confidence >= 0.6:
            return 'STRONG_SELL'
        elif direction == 'down' and confidence >= 0.4:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _interpret_sentiment(self, sentiment: str) -> str:
        """Convert sentiment to trading signal."""
        sentiment_lower = sentiment.lower()
        if 'positive' in sentiment_lower:
            return 'BUY'
        elif 'negative' in sentiment_lower:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _generate_technical_ml_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate technical ML signal based on indicators."""
        if data.empty or len(data) < 20:
            return {'ml_technical_signal': 'HOLD', 'ml_technical_confidence': 0.0}
        
        try:
            # Calculate additional technical indicators
            data = data.copy()
            
            # RSI-based signal
            rsi = data.get('RSI', pd.Series([50] * len(data)))
            rsi_signal = 'BUY' if rsi.iloc[-1] < 30 else 'SELL' if rsi.iloc[-1] > 70 else 'HOLD'
            
            # MACD-based signal
            macd_signal = 'HOLD'
            if 'MACD' in data.columns and 'MACD_Signal' in data.columns:
                macd = data['MACD'].iloc[-1]
                macd_sig = data['MACD_Signal'].iloc[-1]
                if macd > macd_sig:
                    macd_signal = 'BUY'
                elif macd < macd_sig:
                    macd_signal = 'SELL'
            
            # Bollinger Bands signal
            bb_signal = 'HOLD'
            if 'BB_Upper' in data.columns and 'BB_Lower' in data.columns:
                close = data['close'].iloc[-1]
                bb_upper = data['BB_Upper'].iloc[-1]
                bb_lower = data['BB_Lower'].iloc[-1]
                if close <= bb_lower:
                    bb_signal = 'BUY'
                elif close >= bb_upper:
                    bb_signal = 'SELL'
            
            # Combine technical signals
            signals = [rsi_signal, macd_signal, bb_signal]
            buy_count = signals.count('BUY')
            sell_count = signals.count('SELL')
            
            if buy_count >= 2:
                technical_signal = 'BUY'
                confidence = min(0.8, 0.4 + (buy_count - 1) * 0.2)
            elif sell_count >= 2:
                technical_signal = 'SELL'
                confidence = min(0.8, 0.4 + (sell_count - 1) * 0.2)
            else:
                technical_signal = 'HOLD'
                confidence = 0.3
            
            return {
                'ml_technical_signal': technical_signal,
                'ml_technical_confidence': confidence,
                'ml_rsi_signal': rsi_signal,
                'ml_macd_signal': macd_signal,
                'ml_bb_signal': bb_signal
            }
            
        except Exception as e:
            logger.error(f"Error generating technical ML signal: {e}")
            return {'ml_technical_signal': 'HOLD', 'ml_technical_confidence': 0.0}
    
    def _generate_ensemble_signal(self, signals: Dict[str, Any]) -> str:
        """Generate ensemble signal from all ML signals."""
        try:
            # Collect all signals
            signal_list = []
            weights = []
            
            # Price prediction signal
            if 'ml_price_signal' in signals:
                signal_list.append(signals['ml_price_signal'])
                weights.append(signals.get('ml_price_confidence', 0.5))
            
            # Sentiment signal
            if 'ml_sentiment_signal' in signals:
                signal_list.append(signals['ml_sentiment_signal'])
                weights.append(signals.get('ml_sentiment_confidence', 0.3))
            
            # Technical signal
            if 'ml_technical_signal' in signals:
                signal_list.append(signals['ml_technical_signal'])
                weights.append(signals.get('ml_technical_confidence', 0.4))
            
            if not signal_list:
                return 'HOLD'
            
            # Weighted voting
            buy_score = 0
            sell_score = 0
            hold_score = 0
            
            for signal, weight in zip(signal_list, weights):
                if signal in ['BUY', 'STRONG_BUY']:
                    buy_score += weight
                elif signal in ['SELL', 'STRONG_SELL']:
                    sell_score += weight
                else:
                    hold_score += weight
            
            # Determine final signal
            if buy_score > sell_score and buy_score > hold_score:
                return 'STRONG_BUY' if buy_score > 0.7 else 'BUY'
            elif sell_score > buy_score and sell_score > hold_score:
                return 'STRONG_SELL' if sell_score > 0.7 else 'SELL'
            else:
                return 'HOLD'
                
        except Exception as e:
            logger.error(f"Error generating ensemble signal: {e}")
            return 'HOLD'
    
    def _assess_ml_risk(self, data: pd.DataFrame, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Assess ML-based risk metrics."""
        try:
            if data.empty or len(data) < 10:
                return {'ml_risk_level': 'UNKNOWN', 'ml_risk_score': 0.5}
            
            risk_factors = []
            
            # Volatility risk
            if 'close' in data.columns:
                returns = data['close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # Annualized
                if volatility > 0.3:
                    risk_factors.append('HIGH_VOLATILITY')
                elif volatility > 0.15:
                    risk_factors.append('MEDIUM_VOLATILITY')
                else:
                    risk_factors.append('LOW_VOLATILITY')
            
            # Confidence risk
            avg_confidence = np.mean([
                signals.get('ml_price_confidence', 0.5),
                signals.get('ml_sentiment_confidence', 0.5),
                signals.get('ml_technical_confidence', 0.5)
            ])
            
            if avg_confidence < 0.3:
                risk_factors.append('LOW_CONFIDENCE')
            elif avg_confidence > 0.7:
                risk_factors.append('HIGH_CONFIDENCE')
            
            # Data quality risk
            data_points = len(data)
            if data_points < 30:
                risk_factors.append('INSUFFICIENT_DATA')
            
            # Calculate overall risk
            risk_score = 0.5  # Base risk
            if 'HIGH_VOLATILITY' in risk_factors:
                risk_score += 0.3
            if 'LOW_CONFIDENCE' in risk_factors:
                risk_score += 0.2
            if 'INSUFFICIENT_DATA' in risk_factors:
                risk_score += 0.2
            
            risk_score = min(1.0, max(0.0, risk_score))
            
            if risk_score > 0.7:
                risk_level = 'HIGH'
            elif risk_score > 0.4:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            return {
                'ml_risk_level': risk_level,
                'ml_risk_score': round(risk_score, 2),
                'ml_risk_factors': risk_factors
            }
            
        except Exception as e:
            logger.error(f"Error assessing ML risk: {e}")
            return {'ml_risk_level': 'UNKNOWN', 'ml_risk_score': 0.5}
    
    async def get_ml_signal_summary(self, symbols: List[str], use_cache: bool = True) -> pd.DataFrame:
        """Get ML signal summary for multiple symbols.
        
        Args:
            symbols: List of symbols to get signals for
            use_cache: Whether to use cached data if available
            
        Returns:
            DataFrame with ML signals
        """
        try:
            # Try to get from cache first
            if use_cache:
                cached_signals = ml_cache_manager.get_ml_signals(symbols)
                if not cached_signals.empty:
                    logger.info(f"Using cached ML signals for {len(cached_signals)} symbols")
                    return cached_signals
            
            # Generate new signals if cache miss or cache disabled
            logger.info(f"Generating new ML signals for {len(symbols)} symbols")
            results = []
            
            for symbol in symbols:
                signals = await self.generate_ml_signals(symbol)
                if 'error' not in signals:
                    results.append({
                        'symbol': symbol,
                        'ensemble_signal': signals.get('ml_ensemble_signal', 'HOLD'),
                        'price_signal': signals.get('ml_price_signal', 'HOLD'),
                        'sentiment_signal': signals.get('ml_sentiment_signal', 'HOLD'),
                        'technical_signal': signals.get('ml_technical_signal', 'HOLD'),
                        'risk_level': signals.get('ml_risk_level', 'UNKNOWN'),
                        'confidence': round(np.mean([
                            signals.get('ml_price_confidence', 0.5),
                            signals.get('ml_sentiment_confidence', 0.5),
                            signals.get('ml_technical_confidence', 0.5)
                        ]), 2),
                        'data_points': signals.get('data_points', 0),
                        'timestamp': signals.get('timestamp', ''),
                        'price_prediction': signals.get('ml_price_prediction'),
                        'sentiment': signals.get('ml_sentiment'),
                        'sentiment_score': signals.get('ml_sentiment_score'),
                        'sentiment_confidence': signals.get('ml_sentiment_confidence'),
                        'price_confidence': signals.get('ml_price_confidence'),
                        'technical_confidence': signals.get('ml_technical_confidence')
                    })
            
            signals_df = pd.DataFrame(results)
            
            # Save to cache
            if not signals_df.empty:
                ml_cache_manager.save_ml_signals(signals_df)
                logger.info(f"Saved {len(signals_df)} ML signals to cache")
            
            return signals_df
            
        except Exception as e:
            logger.error(f"Error getting ML signal summary: {e}")
            return pd.DataFrame()
    
    async def _send_ml_notifications(self, symbol: str, signals: Dict[str, Any]) -> None:
        """Send ML notifications for worthy signals.
        
        Args:
            symbol: Stock symbol
            signals: Generated ML signals
        """
        try:
            # Send ML signal notification
            ensemble_signal = signals.get('ml_ensemble_signal', 'HOLD')
            confidence = signals.get('ml_ensemble_confidence', 0.5)
            
            await ml_notification_manager.notify_ml_signal_if_worthy(
                symbol=symbol,
                signal_type=ensemble_signal,
                confidence=confidence,
                price_prediction=signals.get('ml_price_prediction'),
                sentiment=signals.get('ml_sentiment'),
                risk_level=signals.get('ml_risk_level'),
                additional_data={
                    'price_signal': signals.get('ml_price_signal'),
                    'sentiment_signal': signals.get('ml_sentiment_signal'),
                    'technical_signal': signals.get('ml_technical_signal'),
                    'data_points': signals.get('data_points', 0)
                }
            )
            
            # Send ML prediction notification if available
            if 'ml_price_prediction' in signals and 'ml_price_confidence' in signals:
                current_price = signals.get('current_price', 0)
                predicted_price = signals.get('ml_price_prediction', 0)
                confidence = signals.get('ml_price_confidence', 0.5)
                direction = signals.get('ml_price_direction', 'neutral')
                
                if current_price > 0 and predicted_price > 0:
                    await ml_notification_manager.notify_ml_prediction_if_worthy(
                        symbol=symbol,
                        current_price=current_price,
                        predicted_price=predicted_price,
                        confidence=confidence,
                        direction=direction,
                        time_horizon="1 day"
                    )
            
            # Send ML sentiment notification if available
            if 'ml_sentiment' in signals and 'ml_sentiment_confidence' in signals:
                sentiment = signals.get('ml_sentiment', 'neutral')
                confidence = signals.get('ml_sentiment_confidence', 0.5)
                news_count = signals.get('ml_sentiment_news_count', 0)
                sentiment_score = signals.get('ml_sentiment_score', 0.0)
                
                await ml_notification_manager.notify_ml_sentiment_if_worthy(
                    symbol=symbol,
                    sentiment=sentiment,
                    confidence=confidence,
                    news_count=news_count,
                    sentiment_score=sentiment_score
                )
                
        except Exception as e:
            logger.error(f"Error sending ML notifications for {symbol}: {e}")

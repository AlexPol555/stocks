#!/usr/bin/env python3
"""ML integration with auto trading system."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class MLAutoTradingIntegration:
    """Integrate ML signals with auto trading system."""
    
    def __init__(self, ml_manager, auto_trader=None):
        self.ml_manager = ml_manager
        self.auto_trader = auto_trader
        self.signal_generator = None
        
    def initialize_signal_generator(self):
        """Initialize signal generator."""
        if self.signal_generator is None:
            from .signals import MLSignalGenerator
            self.signal_generator = MLSignalGenerator(self.ml_manager)
    
    def generate_ml_trading_signals(self, symbols: List[str]) -> Dict[str, Any]:
        """Generate ML trading signals for auto trading."""
        try:
            self.initialize_signal_generator()
            
            trading_signals = {
                'timestamp': datetime.now().isoformat(),
                'signals': {},
                'recommendations': {},
                'risk_assessment': {}
            }
            
            for symbol in symbols:
                try:
                    # Generate ML signals
                    signals = self.signal_generator.generate_ml_signals(symbol)
                    
                    if 'error' in signals:
                        continue
                    
                    # Extract trading signal
                    ensemble_signal = signals.get('ml_ensemble_signal', 'HOLD')
                    confidence = np.mean([
                        signals.get('ml_price_confidence', 0.5),
                        signals.get('ml_sentiment_confidence', 0.5),
                        signals.get('ml_technical_confidence', 0.5)
                    ])
                    
                    risk_level = signals.get('ml_risk_level', 'UNKNOWN')
                    
                    # Convert to trading action
                    action = self._convert_signal_to_action(ensemble_signal, confidence, risk_level)
                    
                    trading_signals['signals'][symbol] = {
                        'action': action,
                        'signal': ensemble_signal,
                        'confidence': confidence,
                        'risk_level': risk_level,
                        'price_signal': signals.get('ml_price_signal', 'HOLD'),
                        'sentiment_signal': signals.get('ml_sentiment_signal', 'HOLD'),
                        'technical_signal': signals.get('ml_technical_signal', 'HOLD'),
                        'timestamp': signals.get('timestamp', datetime.now().isoformat())
                    }
                    
                    # Generate position sizing recommendation
                    position_size = self._calculate_position_size(symbol, confidence, risk_level)
                    trading_signals['recommendations'][symbol] = {
                        'position_size': position_size,
                        'stop_loss': self._calculate_stop_loss(symbol, risk_level),
                        'take_profit': self._calculate_take_profit(symbol, confidence),
                        'max_hold_days': self._calculate_max_hold_days(risk_level)
                    }
                    
                except Exception as e:
                    logger.error(f"Error generating ML signal for {symbol}: {e}")
                    continue
            
            # Overall risk assessment
            trading_signals['risk_assessment'] = self._assess_overall_risk(trading_signals['signals'])
            
            return trading_signals
            
        except Exception as e:
            logger.error(f"Error generating ML trading signals: {e}")
            return {'error': str(e)}
    
    def _convert_signal_to_action(self, signal: str, confidence: float, risk_level: str) -> str:
        """Convert ML signal to trading action."""
        # High risk requires higher confidence
        confidence_threshold = 0.6 if risk_level == 'HIGH' else 0.4
        
        if confidence < confidence_threshold:
            return 'HOLD'
        
        if signal in ['STRONG_BUY', 'BUY']:
            return 'BUY'
        elif signal in ['STRONG_SELL', 'SELL']:
            return 'SELL'
        else:
            return 'HOLD'
    
    def _calculate_position_size(self, symbol: str, confidence: float, risk_level: str) -> float:
        """Calculate recommended position size based on ML analysis."""
        try:
            # Base position size
            base_size = 0.1  # 10% of portfolio
            
            # Adjust for confidence
            confidence_multiplier = min(2.0, confidence * 2)
            
            # Adjust for risk
            risk_multiplier = {
                'LOW': 1.2,
                'MEDIUM': 1.0,
                'HIGH': 0.5,
                'UNKNOWN': 0.3
            }.get(risk_level, 0.3)
            
            # Calculate final position size
            position_size = base_size * confidence_multiplier * risk_multiplier
            
            # Cap at maximum 20% of portfolio
            return min(0.2, max(0.01, position_size))
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            return 0.05  # Conservative default
    
    def _calculate_stop_loss(self, symbol: str, risk_level: str) -> float:
        """Calculate stop loss percentage."""
        stop_loss_percentages = {
            'LOW': 0.05,    # 5%
            'MEDIUM': 0.08, # 8%
            'HIGH': 0.12,   # 12%
            'UNKNOWN': 0.15 # 15%
        }
        return stop_loss_percentages.get(risk_level, 0.10)
    
    def _calculate_take_profit(self, symbol: str, confidence: float) -> float:
        """Calculate take profit percentage."""
        # Higher confidence = higher take profit target
        base_target = 0.10  # 10%
        confidence_multiplier = 1 + confidence
        return base_target * confidence_multiplier
    
    def _calculate_max_hold_days(self, risk_level: str) -> int:
        """Calculate maximum hold days based on risk level."""
        hold_days = {
            'LOW': 30,
            'MEDIUM': 14,
            'HIGH': 7,
            'UNKNOWN': 3
        }
        return hold_days.get(risk_level, 7)
    
    def _assess_overall_risk(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall portfolio risk."""
        try:
            if not signals:
                return {'level': 'UNKNOWN', 'score': 0.5, 'recommendations': []}
            
            # Count signals by risk level
            risk_counts = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'UNKNOWN': 0}
            total_signals = len(signals)
            
            for signal_data in signals.values():
                risk_level = signal_data.get('risk_level', 'UNKNOWN')
                risk_counts[risk_level] += 1
            
            # Calculate risk score
            risk_score = (
                risk_counts['LOW'] * 0.2 +
                risk_counts['MEDIUM'] * 0.5 +
                risk_counts['HIGH'] * 0.8 +
                risk_counts['UNKNOWN'] * 0.9
            ) / total_signals if total_signals > 0 else 0.5
            
            # Determine overall risk level
            if risk_score > 0.7:
                risk_level = 'HIGH'
            elif risk_score > 0.4:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            # Generate recommendations
            recommendations = []
            if risk_counts['HIGH'] > total_signals * 0.3:
                recommendations.append("Consider reducing high-risk positions")
            if risk_counts['UNKNOWN'] > total_signals * 0.2:
                recommendations.append("Review signals with unknown risk levels")
            if total_signals > 10:
                recommendations.append("Consider diversifying across more symbols")
            
            return {
                'level': risk_level,
                'score': round(risk_score, 2),
                'counts': risk_counts,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error assessing overall risk: {e}")
            return {'level': 'UNKNOWN', 'score': 0.5, 'recommendations': []}
    
    def execute_ml_trades(self, trading_signals: Dict[str, Any], account_id: int = 1) -> Dict[str, Any]:
        """Execute trades based on ML signals."""
        try:
            if not self.auto_trader:
                return {'error': 'Auto trader not available'}
            
            execution_results = {
                'timestamp': datetime.now().isoformat(),
                'executed_trades': [],
                'errors': [],
                'summary': {}
            }
            
            signals = trading_signals.get('signals', {})
            recommendations = trading_signals.get('recommendations', {})
            
            for symbol, signal_data in signals.items():
                try:
                    action = signal_data['action']
                    if action == 'HOLD':
                        continue
                    
                    # Get recommendation for this symbol
                    rec = recommendations.get(symbol, {})
                    position_size = rec.get('position_size', 0.05)
                    stop_loss = rec.get('stop_loss', 0.08)
                    take_profit = rec.get('take_profit', 0.12)
                    
                    # Execute trade
                    trade_result = self.auto_trader.execute_trade(
                        symbol=symbol,
                        action=action,
                        position_size=position_size,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        account_id=account_id,
                        ml_confidence=signal_data['confidence'],
                        ml_risk_level=signal_data['risk_level']
                    )
                    
                    if 'error' not in trade_result:
                        execution_results['executed_trades'].append({
                            'symbol': symbol,
                            'action': action,
                            'position_size': position_size,
                            'ml_confidence': signal_data['confidence'],
                            'trade_id': trade_result.get('trade_id'),
                            'timestamp': trade_result.get('timestamp')
                        })
                    else:
                        execution_results['errors'].append({
                            'symbol': symbol,
                            'error': trade_result['error']
                        })
                        
                except Exception as e:
                    logger.error(f"Error executing trade for {symbol}: {e}")
                    execution_results['errors'].append({
                        'symbol': symbol,
                        'error': str(e)
                    })
            
            # Summary
            execution_results['summary'] = {
                'total_signals': len(signals),
                'executed_trades': len(execution_results['executed_trades']),
                'errors': len(execution_results['errors']),
                'success_rate': len(execution_results['executed_trades']) / len(signals) if signals else 0
            }
            
            return execution_results
            
        except Exception as e:
            logger.error(f"Error executing ML trades: {e}")
            return {'error': str(e)}
    
    def get_ml_trading_performance(self, days_back: int = 30) -> Dict[str, Any]:
        """Get ML trading performance metrics."""
        try:
            # This would integrate with the existing trading history
            # For now, return placeholder metrics
            return {
                'total_ml_trades': 0,
                'ml_win_rate': 0.0,
                'ml_avg_return': 0.0,
                'ml_sharpe_ratio': 0.0,
                'ml_max_drawdown': 0.0,
                'ml_vs_traditional': {
                    'ml_performance': 0.0,
                    'traditional_performance': 0.0,
                    'outperformance': 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting ML trading performance: {e}")
            return {'error': str(e)}

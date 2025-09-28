"""Automated trading system that processes signals and executes orders."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from core.analytics.signal_filters import SignalFilter, FilterConfig
from core.analytics.scoring import compute_signal_scores, ScoringConfig
from core.analytics.risk import apply_risk_management
from core.database import (
    get_auto_trading_settings, update_auto_trading_settings,
    save_trading_signal, get_pending_signals, save_auto_order,
    update_order_status, mark_signal_processed, get_daily_order_count,
    save_trade_history, get_trade_history
)
from core.orders.service import create_order
from core.analyzer import StockAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class TradingSession:
    """Represents a trading session with current state."""
    session_id: str
    start_time: datetime
    settings: Dict
    daily_order_count: int
    active_positions: Dict[str, Dict]
    total_pnl: float = 0.0
    total_trades: int = 0


class AutoTrader:
    """Automated trading system."""
    
    def __init__(self, analyzer: StockAnalyzer, db_conn, signal_filter: Optional[SignalFilter] = None):
        self.analyzer = analyzer
        self.db_conn = db_conn
        self.signal_filter = signal_filter or SignalFilter()
        self.current_session: Optional[TradingSession] = None
    
    def start_trading_session(self) -> TradingSession:
        """Start a new trading session."""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        settings = get_auto_trading_settings(self.db_conn)
        daily_count = get_daily_order_count(self.db_conn)
        
        self.current_session = TradingSession(
            session_id=session_id,
            start_time=datetime.now(),
            settings=settings,
            daily_order_count=daily_count,
            active_positions={}
        )
        
        logger.info(f"Started trading session: {session_id}")
        return self.current_session
    
    def process_signals(self, data: pd.DataFrame, contract_code: str) -> List[Dict]:
        """
        Process trading signals for a given contract.
        
        Parameters
        ----------
        data : pd.DataFrame
            Market data with technical indicators
        contract_code : str
            Contract code to process
            
        Returns
        -------
        List[Dict]
            List of generated signals
        """
        if data.empty:
            return []
        
        try:
            # Ensure we have the required columns for technical analysis
            required_columns = ['open', 'high', 'low', 'close', 'volume', 'date']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                logger.warning(f"Missing required columns for {contract_code}: {missing_columns}")
                return []
            
            # Calculate technical indicators if not present
            if not self._has_technical_indicators(data):
                logger.info(f"Calculating technical indicators for {contract_code}")
                data = self._calculate_technical_indicators(data, contract_code)
            
            # Compute signal scores
            scoring_config = ScoringConfig()
            scored_data = compute_signal_scores(data, config=scoring_config)
            
            # Apply smart filters
            filtered_data = self.signal_filter.filter_signals(data, scored_data)
            
            # Generate signals
            signals = self._generate_signals(filtered_data, contract_code)
            
            # Save signals to database
            for signal in signals:
                try:
                    signal_id = save_trading_signal(self.db_conn, signal)
                    signal['signal_id'] = signal_id
                    logger.info(f"Saved signal for {contract_code}: {signal['signal_type']}")
                except Exception as e:
                    logger.error(f"Failed to save signal for {contract_code}: {e}")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error processing signals for {contract_code}: {e}")
            return []
    
    def _has_technical_indicators(self, data: pd.DataFrame) -> bool:
        """Check if data has required technical indicators."""
        required_indicators = ['SMA_FAST', 'SMA_SLOW', 'EMA_FAST', 'EMA_SLOW', 'RSI', 'MACD', 'MACD_SIGNAL', 'ATR']
        return all(indicator in data.columns for indicator in required_indicators)
    
    def _calculate_technical_indicators(self, data: pd.DataFrame, contract_code: str) -> pd.DataFrame:
        """Calculate technical indicators for the data."""
        try:
            from core.indicators import calculate_technical_indicators
            return calculate_technical_indicators(data, contract_code=contract_code)
        except Exception as e:
            logger.error(f"Failed to calculate technical indicators for {contract_code}: {e}")
            return data
    
    def _generate_signals(self, data: pd.DataFrame, contract_code: str) -> List[Dict]:
        """Generate trading signals from filtered data."""
        signals = []
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get the latest row (most recent data)
        if data.empty:
            return signals
        
        latest = data.iloc[-1]
        
        # Check for long signals
        if (latest.get('filtered_long_signal', 0) == 1 and 
            latest.get('final_filter', False)):
            
            signal = {
                'contract_code': contract_code,
                'date': current_date,
                'signal_type': 'long',
                'signal_strength': latest.get('long_probability', 0.0),
                'signal_score': latest.get('long_score', 0.0),
                'price': latest['close'],
                'volume': latest.get('volume', 0),
                'atr': latest.get('ATR', 0),
                'stop_loss': self._calculate_stop_loss(latest, 'long'),
                'take_profit': self._calculate_take_profit(latest, 'long'),
                'processed': False
            }
            signals.append(signal)
        
        # Check for short signals
        if (latest.get('filtered_short_signal', 0) == 1 and 
            latest.get('final_filter', False)):
            
            signal = {
                'contract_code': contract_code,
                'date': current_date,
                'signal_type': 'short',
                'signal_strength': latest.get('short_probability', 0.0),
                'signal_score': latest.get('short_score', 0.0),
                'price': latest['close'],
                'volume': latest.get('volume', 0),
                'atr': latest.get('ATR', 0),
                'stop_loss': self._calculate_stop_loss(latest, 'short'),
                'take_profit': self._calculate_take_profit(latest, 'short'),
                'processed': False
            }
            signals.append(signal)
        
        return signals
    
    def _calculate_stop_loss(self, row: pd.Series, direction: str) -> float:
        """Calculate stop loss price."""
        if direction == 'long':
            return row['close'] - (row.get('ATR', 0) * self.current_session.settings.get('stop_loss_atr_multiplier', 2.0))
        else:
            return row['close'] + (row.get('ATR', 0) * self.current_session.settings.get('stop_loss_atr_multiplier', 2.0))
    
    def _calculate_take_profit(self, row: pd.Series, direction: str) -> float:
        """Calculate take profit price."""
        if direction == 'long':
            return row['close'] + (row.get('ATR', 0) * self.current_session.settings.get('take_profit_atr_multiplier', 3.0))
        else:
            return row['close'] - (row.get('ATR', 0) * self.current_session.settings.get('take_profit_atr_multiplier', 3.0))
    
    def execute_pending_orders(self) -> List[Dict]:
        """
        Execute pending orders from the database.
        
        Returns
        -------
        List[Dict]
            List of execution results
        """
        if not self.current_session:
            logger.warning("No active trading session")
            return []
        
        # Get pending signals
        pending_signals = get_pending_signals(self.db_conn, limit=50)
        
        if pending_signals.empty:
            logger.info("No pending signals to process")
            return []
        
        execution_results = []
        
        for _, signal in pending_signals.iterrows():
            try:
                # Check daily order limit
                if self.current_session.daily_order_count >= self.current_session.settings.get('max_daily_orders', 10):
                    logger.warning("Daily order limit reached")
                    break
                
                # Check signal strength
                if signal['signal_strength'] < self.current_session.settings.get('min_signal_strength', 0.6):
                    logger.info(f"Signal {signal['id']} below minimum strength threshold")
                    mark_signal_processed(self.db_conn, signal['id'])
                    continue
                
                # Execute order
                result = self._execute_signal_order(signal)
                execution_results.append(result)
                
                # Mark signal as processed
                mark_signal_processed(self.db_conn, signal['id'])
                
                # Update session counters
                self.current_session.daily_order_count += 1
                self.current_session.total_trades += 1
                
            except Exception as e:
                logger.error(f"Failed to execute signal {signal['id']}: {e}")
                execution_results.append({
                    'signal_id': signal['id'],
                    'status': 'error',
                    'error': str(e)
                })
        
        return execution_results
    
    def _execute_signal_order(self, signal: pd.Series) -> Dict:
        """Execute a single signal order."""
        # Calculate position size based on risk management
        position_size = self._calculate_position_size(signal)
        
        if position_size <= 0:
            return {
                'signal_id': signal['id'],
                'status': 'skipped',
                'reason': 'Position size too small'
            }
        
        # Create order data
        order_data = {
            'signal_id': signal['id'],
            'company_id': signal['company_id'],
            'contract_code': signal['contract_code'],
            'order_type': 'market',  # Use market orders for automation
            'side': 'BUY' if signal['signal_type'] == 'long' else 'SELL',
            'quantity': int(position_size),
            'price': signal['price'],
            'status': 'pending'
        }
        
        # Save order to database
        order_id = save_auto_order(self.db_conn, order_data)
        
        try:
            # Execute order via Tinkoff API
            order_result = create_order(
                ticker=signal['contract_code'],
                volume=int(position_size),
                order_price=signal['price'],
                order_direction=order_data['side'],
                analyzer=self.analyzer
            )
            
            # Update order status
            if order_result.get('status') == 'success':
                update_order_status(
                    self.db_conn, order_id, 'submitted',
                    tinkoff_order_id=str(order_result.get('response', {}))
                )
                
                # Save trade history
                trade_data = {
                    'signal_id': signal['id'],
                    'order_id': order_id,
                    'company_id': signal['company_id'],
                    'contract_code': signal['contract_code'],
                    'side': order_data['side'],
                    'quantity': position_size,
                    'entry_price': signal['price'],
                    'stop_loss': signal.get('stop_loss'),
                    'take_profit': signal.get('take_profit'),
                    'entry_date': signal['date']
                }
                save_trade_history(self.db_conn, trade_data)
                
                logger.info(f"Successfully executed order {order_id} for {signal['contract_code']}")
                
            else:
                update_order_status(
                    self.db_conn, order_id, 'rejected',
                    error_message=order_result.get('message', 'Unknown error')
                )
                logger.warning(f"Order {order_id} rejected: {order_result.get('message')}")
            
            return {
                'signal_id': signal['id'],
                'order_id': order_id,
                'status': order_result.get('status', 'unknown'),
                'message': order_result.get('message', ''),
                'tinkoff_response': order_result
            }
            
        except Exception as e:
            update_order_status(
                self.db_conn, order_id, 'error',
                error_message=str(e)
            )
            logger.error(f"Failed to execute order {order_id}: {e}")
            
            return {
                'signal_id': signal['id'],
                'order_id': order_id,
                'status': 'error',
                'error': str(e)
            }
    
    def _calculate_position_size(self, signal: pd.Series) -> float:
        """Calculate position size based on risk management."""
        settings = self.current_session.settings
        
        # Get account balance (simplified - in real implementation, get from account)
        account_balance = 1000000.0  # Default demo balance
        
        # Calculate risk amount
        risk_per_trade = settings.get('risk_per_trade', 0.02)
        risk_amount = account_balance * risk_per_trade
        
        # Calculate stop loss distance
        stop_loss_distance = abs(signal['price'] - signal.get('stop_loss', signal['price']))
        
        if stop_loss_distance <= 0:
            return 0
        
        # Calculate position size
        position_value = risk_amount / (stop_loss_distance / signal['price'])
        
        # Apply maximum position size limit
        max_position_size = settings.get('max_position_size', 10000.0)
        position_value = min(position_value, max_position_size)
        
        # Convert to number of shares (assuming price per share)
        position_size = position_value / signal['price']
        
        return max(0, int(position_size))
    
    def get_trading_stats(self) -> Dict:
        """Get current trading session statistics."""
        if not self.current_session:
            return {}
        
        # Get trade history
        trade_history = get_trade_history(self.db_conn, limit=1000)
        
        stats = {
            'session_id': self.current_session.session_id,
            'start_time': self.current_session.start_time.isoformat(),
            'daily_orders': self.current_session.daily_order_count,
            'total_trades': self.current_session.total_trades,
            'total_pnl': self.current_session.total_pnl,
            'active_positions': len(self.current_session.active_positions)
        }
        
        if not trade_history.empty:
            # Calculate performance metrics
            stats['total_trades_executed'] = len(trade_history)
            stats['winning_trades'] = len(trade_history[trade_history['pnl'] > 0])
            stats['losing_trades'] = len(trade_history[trade_history['pnl'] < 0])
            stats['win_rate'] = stats['winning_trades'] / stats['total_trades_executed'] if stats['total_trades_executed'] > 0 else 0
            stats['total_pnl_realized'] = trade_history['pnl'].sum()
            stats['avg_trade_pnl'] = trade_history['pnl'].mean()
            stats['max_drawdown'] = trade_history['pnl'].cumsum().min()
        
        return stats
    
    def stop_trading_session(self) -> Dict:
        """Stop the current trading session and return final stats."""
        if not self.current_session:
            return {}
        
        final_stats = self.get_trading_stats()
        final_stats['end_time'] = datetime.now().isoformat()
        final_stats['session_duration'] = (
            datetime.now() - self.current_session.start_time
        ).total_seconds() / 3600  # hours
        
        logger.info(f"Stopped trading session: {self.current_session.session_id}")
        self.current_session = None
        
        return final_stats


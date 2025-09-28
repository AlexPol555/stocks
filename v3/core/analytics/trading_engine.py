"""Integrated trading engine that combines all automated trading components."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from core.analytics.auto_trader import AutoTrader
from core.analytics.signal_filters import SignalFilter, FilterConfig, create_adaptive_filter
from core.analytics.advanced_risk import AdvancedRiskManager, RiskProfile
from core.analytics.scoring import compute_signal_scores, ScoringConfig
from core.analytics.risk import apply_risk_management
from core.database import (
    get_auto_trading_settings, update_auto_trading_settings,
    save_trading_signal, get_pending_signals, save_auto_order,
    update_order_status, mark_signal_processed, get_daily_order_count,
    save_trade_history, get_trade_history, mergeMetrDaily
)
from core.analyzer import StockAnalyzer

logger = logging.getLogger(__name__)


class TradingEngine:
    """Integrated trading engine that orchestrates all automated trading components."""
    
    def __init__(self, analyzer: StockAnalyzer, db_conn):
        self.analyzer = analyzer
        self.db_conn = db_conn
        self.settings = get_auto_trading_settings(db_conn)
        
        # Initialize components
        self.signal_filter = self._create_signal_filter()
        self.auto_trader = AutoTrader(analyzer, db_conn, self.signal_filter)
        self.risk_manager = self._create_risk_manager()
        
        # Session state
        self.is_running = False
        self.last_update = None
        self.processed_tickers = set()
    
    def _create_signal_filter(self) -> SignalFilter:
        """Create signal filter with current settings."""
        config = FilterConfig(
            min_signal_strength=self.settings.get('min_signal_strength', 0.6),
            min_volume_ratio=1.2,
            max_volatility_percentile=0.8,
            min_atr_ratio=0.5,
            max_atr_ratio=0.15
        )
        return SignalFilter(config)
    
    def _create_risk_manager(self) -> AdvancedRiskManager:
        """Create risk manager with current settings."""
        profile = RiskProfile(
            max_position_size=self.settings.get('max_position_size', 10000.0),
            max_portfolio_risk=0.05,
            max_daily_loss=0.02,
            max_drawdown=0.10,
            max_positions=10,
            stop_loss_atr_multiplier=self.settings.get('stop_loss_atr_multiplier', 2.0),
            take_profit_atr_multiplier=self.settings.get('take_profit_atr_multiplier', 3.0),
            max_holding_days=self.settings.get('max_holding_days', 5)
        )
        return AdvancedRiskManager(profile)
    
    def start_engine(self) -> bool:
        """Start the trading engine."""
        if self.is_running:
            logger.warning("Trading engine is already running")
            return False
        
        if not self.settings.get('enabled', False):
            logger.warning("Auto trading is disabled in settings")
            return False
        
        self.is_running = True
        self.last_update = datetime.now()
        self.processed_tickers.clear()
        
        logger.info("Trading engine started")
        return True
    
    def stop_engine(self) -> bool:
        """Stop the trading engine."""
        if not self.is_running:
            logger.warning("Trading engine is not running")
            return False
        
        self.is_running = False
        logger.info("Trading engine stopped")
        return True
    
    def process_all_tickers(self) -> Dict[str, List[Dict]]:
        """
        Process signals for all available tickers.
        
        Returns
        -------
        Dict[str, List[Dict]]
            Dictionary mapping ticker to list of generated signals
        """
        if not self.is_running:
            logger.warning("Trading engine is not running")
            return {}
        
        # Get all available data
        source = mergeMetrDaily(self.db_conn)
        if source.empty:
            logger.warning("No data available for processing")
            return {}
        
        # Get unique tickers
        tickers = source["contract_code"].dropna().unique()
        results = {}
        
        for ticker in tickers:
            try:
                # Get data for this ticker
                ticker_data = source[source["contract_code"] == ticker].copy()
                ticker_data["date"] = pd.to_datetime(ticker_data["date"], errors="coerce")
                ticker_data = ticker_data.sort_values("date")
                
                # Calculate technical indicators
                from core.indicators import calculate_technical_indicators
                calculated_data = calculate_technical_indicators(ticker_data, contract_code=ticker)
                
                # Process signals
                signals = self.auto_trader.process_signals(calculated_data, ticker)
                results[ticker] = signals
                
                self.processed_tickers.add(ticker)
                
                logger.info(f"Processed {ticker}: {len(signals)} signals")
                
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                results[ticker] = []
        
        self.last_update = datetime.now()
        return results
    
    def execute_pending_orders(self) -> List[Dict]:
        """Execute all pending orders."""
        if not self.is_running:
            logger.warning("Trading engine is not running")
            return []
        
        return self.auto_trader.execute_pending_orders()
    
    def update_positions(self, market_data: Dict[str, float]) -> List[Dict]:
        """
        Update position prices and check for exit signals.
        
        Parameters
        ----------
        market_data : Dict[str, float]
            Dictionary mapping ticker to current price
            
        Returns
        -------
        List[Dict]
            List of closed positions
        """
        if not self.is_running:
            return []
        
        closed_positions = []
        
        # Update position prices
        for ticker, price in market_data.items():
            if self.risk_manager.update_position_price(ticker, price):
                logger.debug(f"Updated price for {ticker}: {price}")
        
        # Check for exit signals
        exit_signals = self.risk_manager.check_exit_signals()
        
        for ticker, exit_reason in exit_signals:
            try:
                # Get current price
                current_price = market_data.get(ticker, 0)
                if current_price <= 0:
                    logger.warning(f"No current price for {ticker}, skipping exit")
                    continue
                
                # Close position
                trade_summary = self.risk_manager.close_position(ticker, current_price, exit_reason)
                
                if trade_summary:
                    closed_positions.append(trade_summary)
                    
                    # Save to trade history
                    save_trade_history(self.db_conn, trade_summary)
                    
                    logger.info(f"Closed position {ticker}: {exit_reason}")
                
            except Exception as e:
                logger.error(f"Error closing position {ticker}: {e}")
        
        return closed_positions
    
    def get_engine_status(self) -> Dict:
        """Get current engine status."""
        return {
            'is_running': self.is_running,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'processed_tickers': len(self.processed_tickers),
            'settings': self.settings,
            'risk_summary': self.risk_manager.get_portfolio_summary(),
            'trading_stats': self.auto_trader.get_trading_stats() if self.auto_trader.current_session else {}
        }
    
    def get_performance_metrics(self) -> Dict:
        """Get comprehensive performance metrics."""
        # Get trade history
        trade_history = get_trade_history(self.db_conn, limit=1000)
        
        if trade_history.empty:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_trade_pnl': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        # Calculate metrics
        total_trades = len(trade_history)
        winning_trades = len(trade_history[trade_history['pnl'] > 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = trade_history['pnl'].sum()
        avg_trade_pnl = trade_history['pnl'].mean()
        
        # Calculate drawdown
        cumulative_pnl = trade_history['pnl'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = (cumulative_pnl - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calculate Sharpe ratio (simplified)
        if trade_history['pnl'].std() > 0:
            sharpe_ratio = trade_history['pnl'].mean() / trade_history['pnl'].std() * (252 ** 0.5)
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_trade_pnl': avg_trade_pnl,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'best_trade': trade_history['pnl'].max(),
            'worst_trade': trade_history['pnl'].min(),
            'avg_holding_days': trade_history['holding_days'].mean()
        }
    
    def run_cycle(self) -> Dict:
        """
        Run one complete trading cycle.
        
        Returns
        -------
        Dict
            Cycle results summary
        """
        if not self.is_running:
            return {'error': 'Engine not running'}
        
        cycle_start = datetime.now()
        results = {
            'cycle_start': cycle_start.isoformat(),
            'signals_generated': 0,
            'orders_executed': 0,
            'positions_closed': 0,
            'errors': []
        }
        
        try:
            # Process all tickers
            signal_results = self.process_all_tickers()
            total_signals = sum(len(signals) for signals in signal_results.values())
            results['signals_generated'] = total_signals
            
            # Execute pending orders
            order_results = self.execute_pending_orders()
            results['orders_executed'] = len(order_results)
            
            # Update positions (simplified - in real implementation, get live prices)
            # For now, we'll skip position updates as we don't have live price feeds
            
            logger.info(f"Trading cycle completed: {total_signals} signals, {len(order_results)} orders")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            results['errors'].append(str(e))
        
        results['cycle_duration'] = (datetime.now() - cycle_start).total_seconds()
        return results
    
    def update_settings(self, new_settings: Dict) -> bool:
        """Update trading settings."""
        try:
            update_auto_trading_settings(self.db_conn, new_settings)
            self.settings = get_auto_trading_settings(self.db_conn)
            
            # Recreate components with new settings
            self.signal_filter = self._create_signal_filter()
            self.risk_manager = self._create_risk_manager()
            
            logger.info("Settings updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False


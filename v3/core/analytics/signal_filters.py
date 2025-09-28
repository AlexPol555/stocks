"""Smart signal filtering system for automated trading."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.indicators.calculations import ATR_COL, RSI_COL, BB_STD_COL, BB_MID_COL

logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """Configuration for signal filters."""
    min_signal_strength: float = 0.6
    min_volume_ratio: float = 1.2  # Volume should be 20% above average
    max_volatility_percentile: float = 0.8  # Reject top 20% most volatile
    min_atr_ratio: float = 0.5  # Minimum ATR relative to price
    max_atr_ratio: float = 0.15  # Maximum ATR relative to price (15%)
    min_price: float = 1.0  # Minimum price to avoid penny stocks
    max_price: float = 10000.0  # Maximum price to avoid very expensive stocks
    rsi_oversold: float = 30.0  # RSI oversold threshold
    rsi_overbought: float = 70.0  # RSI overbought threshold
    bb_oversold: float = -2.0  # Bollinger Bands oversold (standard deviations)
    bb_overbought: float = 2.0  # Bollinger Bands overbought (standard deviations)


class SignalFilter:
    """Smart signal filtering system."""
    
    def __init__(self, config: Optional[FilterConfig] = None):
        self.config = config or FilterConfig()
    
    def filter_signals(self, data: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """
        Apply smart filters to trading signals.
        
        Parameters
        ----------
        data : pd.DataFrame
            Market data with technical indicators
        signals : pd.DataFrame
            DataFrame with signal columns (long_signal, short_signal, etc.)
            
        Returns
        -------
        pd.DataFrame
            Filtered signals with additional filter columns
        """
        if data.empty or signals.empty:
            return signals
        
        # Ensure we have the same index
        filtered_signals = signals.copy()
        
        # Apply volume filter
        filtered_signals = self._apply_volume_filter(data, filtered_signals)
        
        # Apply volatility filter
        filtered_signals = self._apply_volatility_filter(data, filtered_signals)
        
        # Apply price filter
        filtered_signals = self._apply_price_filter(data, filtered_signals)
        
        # Apply technical indicator filters
        filtered_signals = self._apply_technical_filters(data, filtered_signals)
        
        # Apply signal strength filter
        filtered_signals = self._apply_strength_filter(data, filtered_signals)
        
        # Apply ATR filter
        filtered_signals = self._apply_atr_filter(data, filtered_signals)
        
        # Combine all filters
        filtered_signals = self._combine_filters(filtered_signals)
        
        return filtered_signals
    
    def _apply_volume_filter(self, data: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """Filter based on volume relative to average."""
        if 'volume' not in data.columns:
            signals['volume_filter'] = True
            return signals
        
        # Calculate volume ratio (current volume / average volume)
        volume_ma = data['volume'].rolling(window=20, min_periods=5).mean()
        volume_ratio = data['volume'] / (volume_ma + 1e-9)
        
        # Apply filter
        signals['volume_filter'] = volume_ratio >= self.config.min_volume_ratio
        
        return signals
    
    def _apply_volatility_filter(self, data: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """Filter based on volatility (ATR) percentiles."""
        if ATR_COL not in data.columns:
            signals['volatility_filter'] = True
            return signals
        
        # Calculate ATR percentiles
        atr_percentiles = data[ATR_COL].rolling(window=50, min_periods=10).quantile(
            self.config.max_volatility_percentile
        )
        
        # Apply filter (reject high volatility)
        signals['volatility_filter'] = data[ATR_COL] <= atr_percentiles
        
        return signals
    
    def _apply_price_filter(self, data: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """Filter based on price range."""
        if 'close' not in data.columns:
            signals['price_filter'] = True
            return signals
        
        # Apply price range filter
        signals['price_filter'] = (
            (data['close'] >= self.config.min_price) & 
            (data['close'] <= self.config.max_price)
        )
        
        return signals
    
    def _apply_technical_filters(self, data: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """Apply technical indicator filters."""
        signals['technical_filter'] = True
        
        # RSI filter for long signals
        if RSI_COL in data.columns and 'long_signal' in signals.columns:
            rsi_long_filter = (
                (signals['long_signal'] == 0) |  # No long signal
                (data[RSI_COL] <= self.config.rsi_overbought)  # RSI not overbought
            )
            signals['technical_filter'] = signals['technical_filter'] & rsi_long_filter
        
        # RSI filter for short signals
        if RSI_COL in data.columns and 'short_signal' in signals.columns:
            rsi_short_filter = (
                (signals['short_signal'] == 0) |  # No short signal
                (data[RSI_COL] >= self.config.rsi_oversold)  # RSI not oversold
            )
            signals['technical_filter'] = signals['technical_filter'] & rsi_short_filter
        
        # Bollinger Bands filter
        if BB_MID_COL in data.columns and BB_STD_COL in data.columns:
            bb_position = (data['close'] - data[BB_MID_COL]) / (data[BB_STD_COL] + 1e-9)
            
            bb_long_filter = (
                (signals.get('long_signal', 0) == 0) |  # No long signal
                (bb_position >= self.config.bb_oversold)  # Not too oversold
            )
            
            bb_short_filter = (
                (signals.get('short_signal', 0) == 0) |  # No short signal
                (bb_position <= self.config.bb_overbought)  # Not too overbought
            )
            
            signals['technical_filter'] = (
                signals['technical_filter'] & bb_long_filter & bb_short_filter
            )
        
        return signals
    
    def _apply_strength_filter(self, data: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """Filter based on signal strength."""
        # Check for signal strength columns
        strength_columns = ['long_probability', 'short_probability', 'composite_signal']
        
        signals['strength_filter'] = True
        
        for col in strength_columns:
            if col in signals.columns:
                if 'probability' in col:
                    # For probability columns, check minimum threshold
                    strength_filter = (
                        (signals[col] >= self.config.min_signal_strength) |
                        (signals[col].isna())
                    )
                else:
                    # For composite signal, check absolute value
                    strength_filter = (
                        (np.abs(signals[col]) >= self.config.min_signal_strength) |
                        (signals[col].isna())
                    )
                
                signals['strength_filter'] = signals['strength_filter'] & strength_filter
        
        return signals
    
    def _apply_atr_filter(self, data: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """Filter based on ATR relative to price."""
        if ATR_COL not in data.columns or 'close' not in data.columns:
            signals['atr_filter'] = True
            return signals
        
        # Calculate ATR as percentage of price
        atr_ratio = data[ATR_COL] / (data['close'] + 1e-9)
        
        # Apply ATR range filter
        signals['atr_filter'] = (
            (atr_ratio >= self.config.min_atr_ratio) &
            (atr_ratio <= self.config.max_atr_ratio)
        )
        
        return signals
    
    def _combine_filters(self, signals: pd.DataFrame) -> pd.DataFrame:
        """Combine all filters into final signal."""
        # Get all filter columns
        filter_columns = [col for col in signals.columns if col.endswith('_filter')]
        
        if not filter_columns:
            signals['final_filter'] = True
        else:
            # All filters must pass
            signals['final_filter'] = signals[filter_columns].all(axis=1)
        
        # Apply final filter to signals
        signal_columns = ['long_signal', 'short_signal', 'long_probability', 'short_probability']
        for col in signal_columns:
            if col in signals.columns:
                signals[f'filtered_{col}'] = signals[col].where(
                    signals['final_filter'], 0
                )
        
        return signals
    
    def get_filter_stats(self, signals: pd.DataFrame) -> Dict[str, float]:
        """Get statistics about filter performance."""
        if signals.empty:
            return {}
        
        stats = {}
        total_signals = len(signals)
        
        if total_signals == 0:
            return stats
        
        # Count original signals
        if 'long_signal' in signals.columns:
            stats['original_long_signals'] = signals['long_signal'].sum()
        if 'short_signal' in signals.columns:
            stats['original_short_signals'] = signals['short_signal'].sum()
        
        # Count filtered signals
        if 'filtered_long_signal' in signals.columns:
            stats['filtered_long_signals'] = signals['filtered_long_signal'].sum()
        if 'filtered_short_signal' in signals.columns:
            stats['filtered_short_signals'] = signals['filtered_short_signal'].sum()
        
        # Calculate filter pass rates
        if 'final_filter' in signals.columns:
            stats['filter_pass_rate'] = signals['final_filter'].mean()
        
        # Individual filter pass rates
        filter_columns = [col for col in signals.columns if col.endswith('_filter')]
        for col in filter_columns:
            stats[f'{col}_pass_rate'] = signals[col].mean()
        
        return stats


def create_adaptive_filter(data: pd.DataFrame, lookback_days: int = 30) -> SignalFilter:
    """
    Create an adaptive filter based on recent market conditions.
    
    Parameters
    ----------
    data : pd.DataFrame
        Historical market data
    lookback_days : int
        Number of days to look back for adaptive parameters
        
    Returns
    -------
    SignalFilter
        Configured filter with adaptive parameters
    """
    if data.empty or len(data) < lookback_days:
        return SignalFilter()
    
    # Use recent data for adaptive parameters
    recent_data = data.tail(lookback_days)
    
    # Calculate adaptive volatility threshold (80th percentile of recent ATR)
    if ATR_COL in recent_data.columns:
        volatility_threshold = recent_data[ATR_COL].quantile(0.8)
    else:
        volatility_threshold = 0.1  # Default
    
    # Calculate adaptive volume threshold (median of recent volume ratios)
    if 'volume' in recent_data.columns:
        volume_ma = recent_data['volume'].rolling(window=10, min_periods=5).mean()
        volume_ratios = recent_data['volume'] / (volume_ma + 1e-9)
        volume_threshold = volume_ratios.median()
    else:
        volume_threshold = 1.2  # Default
    
    # Create adaptive config
    config = FilterConfig(
        min_volume_ratio=max(1.1, volume_threshold),
        max_volatility_percentile=0.8,
        min_signal_strength=0.6
    )
    
    return SignalFilter(config)


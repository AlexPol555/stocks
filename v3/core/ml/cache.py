"""ML Cache management module.

This module provides caching functionality for ML signals and metrics,
storing results in database for fast access and reducing computation time.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class MLCacheManager:
    """Manages ML signals and metrics caching in database."""
    
    def __init__(self, db_path: str = "stock_data.db"):
        """Initialize ML cache manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.cache_duration = timedelta(hours=6)  # Cache for 6 hours
        self.metrics_cache_duration = timedelta(hours=1)  # Metrics cache for 1 hour
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def save_ml_signals(self, signals_df: pd.DataFrame) -> bool:
        """Save ML signals to database.
        
        Args:
            signals_df: DataFrame with ML signals data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Clear old signals (older than cache duration)
            cutoff_time = (datetime.now() - self.cache_duration).isoformat()
            cursor.execute("DELETE FROM ml_signals WHERE created_at < ?", (cutoff_time,))
            
            # Insert new signals
            for _, row in signals_df.iterrows():
                cursor.execute("""
                    INSERT OR REPLACE INTO ml_signals (
                        symbol, signal_type, confidence, price_signal, sentiment_signal,
                        technical_signal, ensemble_signal, risk_level, price_prediction,
                        sentiment, sentiment_score, sentiment_confidence, price_confidence,
                        technical_confidence, data_points, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get('symbol', ''),
                    row.get('ensemble_signal', 'HOLD'),
                    row.get('confidence', 0.5),
                    row.get('price_signal', 'HOLD'),
                    row.get('sentiment_signal', 'HOLD'),
                    row.get('technical_signal', 'HOLD'),
                    row.get('ensemble_signal', 'HOLD'),
                    row.get('risk_level', 'UNKNOWN'),
                    row.get('price_prediction'),
                    row.get('sentiment'),
                    row.get('sentiment_score'),
                    row.get('sentiment_confidence'),
                    row.get('price_confidence'),
                    row.get('technical_confidence'),
                    row.get('data_points', 0),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Saved {len(signals_df)} ML signals to database")
            return True
            
        except Exception as e:
            logger.error(f"Error saving ML signals: {e}")
            return False
    
    def get_ml_signals(self, symbols: Optional[List[str]] = None, 
                      max_age_hours: int = 6) -> pd.DataFrame:
        """Get ML signals from database.
        
        Args:
            symbols: List of symbols to filter by (None for all)
            max_age_hours: Maximum age of signals in hours
            
        Returns:
            DataFrame with ML signals
        """
        try:
            conn = self._get_connection()
            
            # Calculate cutoff time
            cutoff_time = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
            
            # Build query
            query = """
                SELECT * FROM ml_signals 
                WHERE created_at >= ?
            """
            params = [cutoff_time]
            
            if symbols:
                placeholders = ','.join(['?' for _ in symbols])
                query += f" AND symbol IN ({placeholders})"
                params.extend(symbols)
            
            query += " ORDER BY created_at DESC"
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            logger.info(f"Retrieved {len(df)} ML signals from database")
            return df
            
        except Exception as e:
            logger.error(f"Error getting ML signals: {e}")
            return pd.DataFrame()
    
    def save_ml_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Save ML metrics to database.
        
        Args:
            metrics: Dictionary with metrics data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Clear old metrics
            cutoff_time = (datetime.now() - self.metrics_cache_duration).isoformat()
            cursor.execute("DELETE FROM ml_metrics WHERE created_at < ?", (cutoff_time,))
            
            # Insert new metrics
            cursor.execute("""
                INSERT INTO ml_metrics (
                    total_signals, buy_signals, sell_signals, hold_signals,
                    avg_confidence, high_risk_signals, buy_ratio, sell_ratio,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.get('total_signals', 0),
                metrics.get('buy_signals', 0),
                metrics.get('sell_signals', 0),
                metrics.get('hold_signals', 0),
                metrics.get('avg_confidence', 0.0),
                metrics.get('high_risk_signals', 0),
                metrics.get('buy_ratio', 0.0),
                metrics.get('sell_ratio', 0.0),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info("Saved ML metrics to database")
            return True
            
        except Exception as e:
            logger.error(f"Error saving ML metrics: {e}")
            return False
    
    def get_ml_metrics(self, max_age_hours: int = 1) -> Optional[Dict[str, Any]]:
        """Get latest ML metrics from database.
        
        Args:
            max_age_hours: Maximum age of metrics in hours
            
        Returns:
            Dictionary with metrics or None if not found
        """
        try:
            conn = self._get_connection()
            
            # Calculate cutoff time
            cutoff_time = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
            
            query = """
                SELECT * FROM ml_metrics 
                WHERE created_at >= ?
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            df = pd.read_sql_query(query, conn, params=[cutoff_time])
            conn.close()
            
            if df.empty:
                return None
            
            row = df.iloc[0]
            return {
                'total_signals': row['total_signals'],
                'buy_signals': row['buy_signals'],
                'sell_signals': row['sell_signals'],
                'hold_signals': row['hold_signals'],
                'avg_confidence': row['avg_confidence'],
                'high_risk_signals': row['high_risk_signals'],
                'buy_ratio': row['buy_ratio'],
                'sell_ratio': row['sell_ratio'],
                'created_at': row['created_at']
            }
            
        except Exception as e:
            logger.error(f"Error getting ML metrics: {e}")
            return None
    
    def save_cache_data(self, cache_key: str, data: Any, 
                       expires_in_hours: int = 6) -> bool:
        """Save arbitrary data to cache.
        
        Args:
            cache_key: Unique key for the data
            data: Data to cache (will be JSON serialized)
            expires_in_hours: Hours until data expires
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Calculate expiration time
            expires_at = (datetime.now() + timedelta(hours=expires_in_hours)).isoformat()
            
            # Serialize data
            cache_data = json.dumps(data, default=str)
            
            # Insert or replace
            cursor.execute("""
                INSERT OR REPLACE INTO ml_cache (cache_key, cache_data, expires_at, created_at)
                VALUES (?, ?, ?, ?)
            """, (cache_key, cache_data, expires_at, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Saved cache data for key: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving cache data: {e}")
            return False
    
    def get_cache_data(self, cache_key: str) -> Optional[Any]:
        """Get data from cache.
        
        Args:
            cache_key: Key to retrieve data for
            
        Returns:
            Cached data or None if not found/expired
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get cache entry
            cursor.execute("""
                SELECT cache_data, expires_at FROM ml_cache 
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                cache_data, expires_at = row
                data = json.loads(cache_data)
                logger.info(f"Retrieved cache data for key: {cache_key}")
                return data
            else:
                logger.debug(f"Cache miss for key: {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting cache data: {e}")
            return None
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Delete expired entries
            cursor.execute("DELETE FROM ml_cache WHERE expires_at < ?", 
                          (datetime.now().isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleared {deleted_count} expired cache entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")
            return 0
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status information.
        
        Returns:
            Dictionary with cache status
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Count entries by type
            cursor.execute("SELECT COUNT(*) FROM ml_signals")
            signals_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ml_metrics")
            metrics_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM ml_cache")
            cache_count = cursor.fetchone()[0]
            
            # Get latest signal time
            cursor.execute("SELECT MAX(created_at) FROM ml_signals")
            latest_signal = cursor.fetchone()[0]
            
            # Get latest metrics time
            cursor.execute("SELECT MAX(created_at) FROM ml_metrics")
            latest_metrics = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'signals_count': signals_count,
                'metrics_count': metrics_count,
                'cache_count': cache_count,
                'latest_signal': latest_signal,
                'latest_metrics': latest_metrics,
                'cache_duration_hours': self.cache_duration.total_seconds() / 3600,
                'metrics_cache_duration_hours': self.metrics_cache_duration.total_seconds() / 3600
            }
            
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {}


# Global cache manager instance
ml_cache_manager = MLCacheManager()

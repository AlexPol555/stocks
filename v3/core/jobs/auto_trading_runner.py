"""Automated trading runner that executes trading cycles periodically."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from core.analytics.trading_engine import TradingEngine
from core.analyzer import StockAnalyzer
from core.database import get_connection, get_auto_trading_settings
from core.utils import read_api_key

logger = logging.getLogger(__name__)


class AutoTradingRunner:
    """Runs automated trading engine in a loop."""
    
    def __init__(self, db_path: Optional[str] = None, cycle_interval: int = 300):
        """
        Initialize the auto trading runner.
        
        Parameters
        ----------
        db_path : str, optional
            Path to database file
        cycle_interval : int
            Interval between trading cycles in seconds (default: 5 minutes)
        """
        self.db_path = db_path
        self.cycle_interval = cycle_interval
        self.db_conn = None
        self.analyzer = None
        self.trading_engine = None
        self.is_running = False
        self.start_time = None
    
    def initialize(self) -> bool:
        """Initialize the trading runner."""
        try:
            # Connect to database
            self.db_conn = get_connection(self.db_path)
            
            # Get API key
            api_key = read_api_key()
            
            # Create analyzer
            self.analyzer = StockAnalyzer(api_key, db_conn=self.db_conn)
            
            # Create trading engine
            self.trading_engine = TradingEngine(self.analyzer, self.db_conn)
            
            logger.info("Auto trading runner initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize auto trading runner: {e}")
            return False
    
    def start(self) -> bool:
        """Start the auto trading runner."""
        if self.is_running:
            logger.warning("Auto trading runner is already running")
            return False
        
        if not self.trading_engine:
            logger.error("Trading engine not initialized")
            return False
        
        # Check if auto trading is enabled
        settings = get_auto_trading_settings(self.db_conn)
        if not settings.get('enabled', False):
            logger.warning("Auto trading is disabled in settings")
            return False
        
        # Start trading engine
        if not self.trading_engine.start_engine():
            logger.error("Failed to start trading engine")
            return False
        
        self.is_running = True
        self.start_time = datetime.now()
        
        logger.info(f"Auto trading runner started (cycle interval: {self.cycle_interval}s)")
        return True
    
    def stop(self) -> bool:
        """Stop the auto trading runner."""
        if not self.is_running:
            logger.warning("Auto trading runner is not running")
            return False
        
        self.is_running = False
        
        if self.trading_engine:
            self.trading_engine.stop_engine()
        
        logger.info("Auto trading runner stopped")
        return True
    
    def run_cycle(self) -> dict:
        """Run one trading cycle."""
        if not self.is_running or not self.trading_engine:
            return {'error': 'Runner not running or engine not initialized'}
        
        try:
            cycle_results = self.trading_engine.run_cycle()
            logger.info(f"Trading cycle completed: {cycle_results}")
            return cycle_results
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            return {'error': str(e)}
    
    def run_forever(self) -> None:
        """Run the trading engine forever (until stopped)."""
        if not self.start():
            logger.error("Failed to start auto trading runner")
            return
        
        logger.info("Starting continuous trading loop...")
        
        try:
            while self.is_running:
                cycle_start = datetime.now()
                
                # Run trading cycle
                cycle_results = self.run_cycle()
                
                # Log cycle results
                if 'error' in cycle_results:
                    logger.error(f"Cycle failed: {cycle_results['error']}")
                else:
                    logger.info(
                        f"Cycle completed: {cycle_results.get('signals_generated', 0)} signals, "
                        f"{cycle_results.get('orders_executed', 0)} orders, "
                        f"duration: {cycle_results.get('cycle_duration', 0):.2f}s"
                    )
                
                # Calculate sleep time
                cycle_duration = (datetime.now() - cycle_start).total_seconds()
                sleep_time = max(0, self.cycle_interval - cycle_duration)
                
                if sleep_time > 0:
                    logger.debug(f"Sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
        except Exception as e:
            logger.error(f"Unexpected error in trading loop: {e}")
        finally:
            self.stop()
    
    def get_status(self) -> dict:
        """Get current runner status."""
        if not self.trading_engine:
            return {'status': 'not_initialized'}
        
        engine_status = self.trading_engine.get_engine_status()
        
        return {
            'status': 'running' if self.is_running else 'stopped',
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'cycle_interval': self.cycle_interval,
            'engine_status': engine_status
        }
    
    def get_performance(self) -> dict:
        """Get performance metrics."""
        if not self.trading_engine:
            return {}
        
        return self.trading_engine.get_performance_metrics()


def main():
    """Main function for running the auto trading runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Auto Trading Runner')
    parser.add_argument('--db-path', type=str, help='Path to database file')
    parser.add_argument('--interval', type=int, default=300, help='Cycle interval in seconds')
    parser.add_argument('--log-level', type=str, default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run runner
    runner = AutoTradingRunner(db_path=args.db_path, cycle_interval=args.interval)
    
    if not runner.initialize():
        logger.error("Failed to initialize runner")
        return 1
    
    try:
        runner.run_forever()
    except Exception as e:
        logger.error(f"Runner failed: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())


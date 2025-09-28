"""Real integration example with existing modules.

This module demonstrates how to integrate the task scheduler
with the actual existing modules of the trading system.
"""

import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

from .scheduler import TaskScheduler
from .trading_calendar import TradingCalendar, Market
from .integration import SchedulerIntegration

# Import existing modules
from ..data_loader import load_csv_data
from ..news import run_fetch_job, build_summary
from ..analyzer import StockAnalyzer
from ..database import get_connection

logger = logging.getLogger(__name__)


class RealSchedulerIntegration:
    """Real integration with existing trading system modules."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize real integration.
        
        Args:
            api_key: Tinkoff API key for market data
        """
        self.api_key = api_key
        self.trading_calendar = TradingCalendar()
        self.scheduler = TaskScheduler(self.trading_calendar)
        self.integration = SchedulerIntegration(self.scheduler, self.trading_calendar)
        self._loop_thread = None
        self._loop = None
        
        # Setup all tasks
        self._setup_all_tasks()
        
    def _run_loop(self):
        """Run the event loop in a separate thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
        
    def _setup_all_tasks(self):
        """Setup all tasks with real functions."""
        self.integration.setup_all_tasks(
            data_loader_func=self._update_market_data,
            news_fetch_func=self._fetch_news,
            news_process_func=self._process_news,
            indicators_func=self._calculate_indicators,
            signals_func=self._generate_signals,
            notification_func=self._send_notifications
        )
        
    async def _update_market_data(self):
        """Update market data from CSV files."""
        try:
            logger.info("Starting market data update...")
            
            # Load data from CSV files
            data = load_csv_data("data/")
            
            if data.empty:
                logger.warning("No market data found in CSV files")
                return
                
            # Process and store data
            # This is a simplified example - in reality you would:
            # 1. Process the data
            # 2. Store it in the database
            # 3. Update existing records
            
            logger.info(f"Market data updated: {len(data)} records processed")
            
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
            raise
            
    async def _fetch_news(self):
        """Fetch news from RSS feeds."""
        try:
            logger.info("Starting news fetch...")
            
            # Run news fetch job
            result = run_fetch_job()
            
            if result["status"] == "success":
                stats = result.get("stats", {})
                new_articles = stats.get("new_articles", 0)
                duplicates = stats.get("duplicates", 0)
                logger.info(f"News fetched: {new_articles} new articles, {duplicates} duplicates")
            elif result["status"] == "locked":
                logger.warning("News parser is locked, skipping this run")
            else:
                logger.error(f"News fetch failed: {result.get('error', 'Unknown error')}")
                raise Exception(f"News fetch failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            raise
            
    async def _process_news(self):
        """Process news pipeline."""
        try:
            logger.info("Starting news processing...")
            
            # Build news summary
            summary = build_summary()
            
            if summary:
                clusters = summary.get("clusters", [])
                top_mentions = summary.get("top_mentions", [])
                logger.info(f"News processed: {len(clusters)} clusters, {len(top_mentions)} top mentions")
            else:
                logger.warning("No news summary generated")
                
        except Exception as e:
            logger.error(f"Error processing news: {e}")
            raise
            
    async def _calculate_indicators(self):
        """Calculate technical indicators."""
        try:
            logger.info("Starting indicators calculation...")
            
            # Get database connection
            conn = get_connection()
            if not conn:
                logger.error("No database connection available")
                return
                
            # Get list of companies
            cursor = conn.cursor()
            cursor.execute("SELECT id, contract_code, figi FROM companies WHERE figi IS NOT NULL")
            companies = cursor.fetchall()
            
            if not companies:
                logger.warning("No companies found for indicators calculation")
                return
                
            # Calculate indicators for each company
            processed = 0
            for company_id, contract_code, figi in companies:
                try:
                    # Get stock data
                    analyzer = StockAnalyzer(self.api_key, conn)
                    data = analyzer.get_stock_data(figi)
                    
                    if data.empty:
                        logger.warning(f"No data for {contract_code} ({figi})")
                        continue
                        
                    # Calculate indicators
                    # This is a simplified example - in reality you would:
                    # 1. Calculate various technical indicators
                    # 2. Store them in the database
                    # 3. Update existing records
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Error calculating indicators for {contract_code}: {e}")
                    continue
                    
            logger.info(f"Indicators calculated for {processed} companies")
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            raise
            
    async def _generate_signals(self):
        """Generate trading signals."""
        try:
            logger.info("Starting signal generation...")
            
            # Get database connection
            conn = get_connection()
            if not conn:
                logger.error("No database connection available")
                return
                
            # Get companies with calculated indicators
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT c.id, c.contract_code, c.figi 
                FROM companies c
                WHERE c.figi IS NOT NULL
            """)
            companies = cursor.fetchall()
            
            if not companies:
                logger.warning("No companies found for signal generation")
                return
                
            # Generate signals for each company
            signals_generated = 0
            for company_id, contract_code, figi in companies:
                try:
                    # Get latest data and indicators
                    # This is a simplified example - in reality you would:
                    # 1. Get latest price data
                    # 2. Get calculated indicators
                    # 3. Apply signal generation logic
                    # 4. Store signals in database
                    
                    signals_generated += 1
                    
                except Exception as e:
                    logger.error(f"Error generating signals for {contract_code}: {e}")
                    continue
                    
            logger.info(f"Signals generated for {signals_generated} companies")
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            raise
            
    async def _send_notifications(self):
        """Send notifications for critical events."""
        try:
            logger.info("Checking for notifications...")
            
            # Check for critical events
            # This is a simplified example - in reality you would:
            # 1. Check for price alerts
            # 2. Check for news alerts
            # 3. Check for system alerts
            # 4. Send appropriate notifications
            
            # For now, just log that we checked
            logger.info("Notification check completed")
            
        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
            raise
            
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running and self._loop_thread is None:
            # Start event loop in separate thread
            self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
            self._loop_thread.start()
            
            # Wait for loop to be ready
            while self._loop is None:
                threading.Event().wait(0.01)
            
            # Start scheduler in the loop
            asyncio.run_coroutine_threadsafe(self.scheduler.start(), self._loop)
            logger.info("Real scheduler started")
        else:
            logger.warning("Scheduler is already running")
            
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running and self._loop is not None:
            # Stop scheduler in the loop
            asyncio.run_coroutine_threadsafe(self.scheduler.stop(), self._loop)
            
            # Stop the event loop
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._loop_thread.join(timeout=5)
            
            self._loop = None
            self._loop_thread = None
            logger.info("Real scheduler stopped")
        else:
            logger.warning("Scheduler is not running")
            
    @property
    def running(self):
        """Check if scheduler is running."""
        return self.scheduler.running and self._loop_thread is not None and self._loop_thread.is_alive()
        
    def get_status(self):
        """Get scheduler status."""
        return self.integration.get_task_status()
        
    def enable_task(self, task_name: str):
        """Enable a task."""
        self.integration.enable_task(task_name)
        
    def disable_task(self, task_name: str):
        """Disable a task."""
        self.integration.disable_task(task_name)
        
    def get_next_run_times(self):
        """Get next run times for all tasks."""
        return self.integration.get_next_run_times()
        
    def start_scheduler(self):
        """Start the scheduler (alias for start method)."""
        self.start()
        
    def stop_scheduler(self):
        """Stop the scheduler (alias for stop method)."""
        self.stop()


# Example usage
async def main():
    """Example usage of real integration."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create integration
    integration = RealSchedulerIntegration(api_key="your_tinkoff_api_key")
    
    # Start scheduler
    integration.start()
    
    # Run for 60 seconds
    await asyncio.sleep(60)
    
    # Stop scheduler
    integration.stop()
    
    # Print final status
    status = integration.get_status()
    print(f"Scheduler status: {status}")


if __name__ == "__main__":
    asyncio.run(main())

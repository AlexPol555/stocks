"""Example usage of the task scheduler.

This module demonstrates how to use the task scheduler with existing
components of the trading system.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from .scheduler import TaskScheduler
from .trading_calendar import TradingCalendar, Market
from .integration import SchedulerIntegration

logger = logging.getLogger(__name__)


async def example_market_data_update():
    """Example function for market data updates."""
    logger.info("Updating market data...")
    # Simulate market data update
    await asyncio.sleep(1)
    logger.info("Market data updated")


async def example_news_fetch():
    """Example function for news fetching."""
    logger.info("Fetching news...")
    # Simulate news fetching
    await asyncio.sleep(2)
    logger.info("News fetched")


async def example_news_process():
    """Example function for news processing."""
    logger.info("Processing news pipeline...")
    # Simulate news processing
    await asyncio.sleep(1)
    logger.info("News processed")


async def example_calculate_indicators():
    """Example function for calculating indicators."""
    logger.info("Calculating technical indicators...")
    # Simulate indicator calculation
    await asyncio.sleep(3)
    logger.info("Indicators calculated")


async def example_generate_signals():
    """Example function for generating signals."""
    logger.info("Generating trading signals...")
    # Simulate signal generation
    await asyncio.sleep(2)
    logger.info("Signals generated")


async def example_send_notifications():
    """Example function for sending notifications."""
    logger.info("Sending notifications...")
    # Simulate notification sending
    await asyncio.sleep(1)
    logger.info("Notifications sent")


async def main():
    """Main example function."""
    # Create scheduler and trading calendar
    trading_calendar = TradingCalendar()
    scheduler = TaskScheduler(trading_calendar)
    
    # Create integration
    integration = SchedulerIntegration(scheduler, trading_calendar)
    
    # Setup all tasks
    integration.setup_all_tasks(
        data_loader_func=example_market_data_update,
        news_fetch_func=example_news_fetch,
        news_process_func=example_news_process,
        indicators_func=example_calculate_indicators,
        signals_func=example_generate_signals,
        notification_func=example_send_notifications
    )
    
    # Start scheduler
    integration.start_scheduler()
    
    # Run for 30 seconds
    await asyncio.sleep(30)
    
    # Stop scheduler
    integration.stop_scheduler()
    
    # Print final status
    status = integration.get_task_status()
    print(f"Scheduler status: {status}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    asyncio.run(main())

"""Examples of using the task scheduler.

This module provides various examples of how to use the task scheduler
in different scenarios and configurations.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from .scheduler import TaskScheduler
from .trading_calendar import TradingCalendar, Market
from .integration import SchedulerIntegration
from .config import get_config, get_task_config
from .utils import retry_on_failure, format_duration, get_task_summary

logger = logging.getLogger(__name__)


# Example 1: Basic scheduler setup
async def example_basic_scheduler():
    """Example of basic scheduler setup and usage."""
    print("=== Example 1: Basic Scheduler ===")
    
    # Create scheduler
    scheduler = TaskScheduler()
    
    # Add a simple task
    async def simple_task():
        print(f"Simple task executed at {datetime.now()}")
        await asyncio.sleep(1)
        
    scheduler.add_task(
        name="simple_task",
        func=simple_task,
        interval=timedelta(seconds=5),
        priority=1
    )
    
    # Start scheduler
    await scheduler.start()
    
    # Run for 20 seconds
    await asyncio.sleep(20)
    
    # Stop scheduler
    await scheduler.stop()
    
    print("Basic scheduler example completed")


# Example 2: Scheduler with trading calendar
async def example_trading_scheduler():
    """Example of scheduler with trading calendar integration."""
    print("=== Example 2: Trading Scheduler ===")
    
    # Create trading calendar and scheduler
    trading_calendar = TradingCalendar()
    scheduler = TaskScheduler(trading_calendar)
    
    # Add market-aware tasks
    async def market_data_task():
        if trading_calendar.is_market_open(Market.MOEX):
            print(f"Market data updated at {datetime.now()}")
        else:
            print("Market is closed, skipping data update")
            
    async def news_task():
        print(f"News fetched at {datetime.now()}")
        
    scheduler.add_task(
        name="market_data",
        func=market_data_task,
        interval=timedelta(minutes=2),
        priority=10
    )
    
    scheduler.add_task(
        name="news_fetch",
        func=news_task,
        interval=timedelta(minutes=1),
        priority=5
    )
    
    # Start scheduler
    await scheduler.start()
    
    # Run for 30 seconds
    await asyncio.sleep(30)
    
    # Stop scheduler
    await scheduler.stop()
    
    print("Trading scheduler example completed")


# Example 3: Scheduler with dependencies
async def example_dependency_scheduler():
    """Example of scheduler with task dependencies."""
    print("=== Example 3: Dependency Scheduler ===")
    
    scheduler = TaskScheduler()
    
    # Task 1: Data collection
    async def collect_data():
        print("Collecting data...")
        await asyncio.sleep(2)
        print("Data collected")
        
    # Task 2: Data processing (depends on data collection)
    async def process_data():
        print("Processing data...")
        await asyncio.sleep(1)
        print("Data processed")
        
    # Task 3: Generate report (depends on data processing)
    async def generate_report():
        print("Generating report...")
        await asyncio.sleep(1)
        print("Report generated")
        
    # Add tasks with dependencies
    scheduler.add_task(
        name="collect_data",
        func=collect_data,
        interval=timedelta(seconds=10),
        priority=10
    )
    
    scheduler.add_task(
        name="process_data",
        func=process_data,
        interval=timedelta(seconds=10),
        priority=8,
        dependencies=["collect_data"]
    )
    
    scheduler.add_task(
        name="generate_report",
        func=generate_report,
        interval=timedelta(seconds=10),
        priority=6,
        dependencies=["process_data"]
    )
    
    # Start scheduler
    await scheduler.start()
    
    # Run for 40 seconds
    await asyncio.sleep(40)
    
    # Stop scheduler
    await scheduler.stop()
    
    print("Dependency scheduler example completed")


# Example 4: Scheduler with error handling
async def example_error_handling_scheduler():
    """Example of scheduler with error handling and retries."""
    print("=== Example 4: Error Handling Scheduler ===")
    
    scheduler = TaskScheduler()
    
    # Task that sometimes fails
    async def unreliable_task():
        import random
        if random.random() < 0.7:  # 70% chance of failure
            raise Exception("Random failure")
        print("Task completed successfully")
        
    # Task with retry decorator
    @retry_on_failure(max_retries=3, delay=1.0, exponential=True)
    async def retry_task():
        import random
        if random.random() < 0.5:  # 50% chance of failure
            raise Exception("Random failure")
        print("Retry task completed successfully")
        
    scheduler.add_task(
        name="unreliable_task",
        func=unreliable_task,
        interval=timedelta(seconds=3),
        priority=5,
        max_errors=2
    )
    
    scheduler.add_task(
        name="retry_task",
        func=retry_task,
        interval=timedelta(seconds=3),
        priority=5,
        max_errors=5
    )
    
    # Start scheduler
    await scheduler.start()
    
    # Run for 30 seconds
    await asyncio.sleep(30)
    
    # Stop scheduler
    await scheduler.stop()
    
    print("Error handling scheduler example completed")


# Example 5: Scheduler with configuration
async def example_config_scheduler():
    """Example of scheduler using configuration."""
    print("=== Example 5: Config Scheduler ===")
    
    # Get configuration
    config = get_config()
    
    # Create scheduler
    scheduler = TaskScheduler()
    
    # Add tasks from configuration
    for task_name, interval in config["intervals"].items():
        async def task_func():
            print(f"Task {task_name} executed at {datetime.now()}")
            await asyncio.sleep(0.5)
            
        task_config = get_task_config(task_name)
        scheduler.add_task(
            name=task_name,
            func=task_func,
            interval=interval,
            priority=task_config["priority"],
            dependencies=task_config["dependencies"],
            max_errors=task_config["max_errors"]
        )
        
    # Start scheduler
    await scheduler.start()
    
    # Run for 60 seconds
    await asyncio.sleep(60)
    
    # Stop scheduler
    await scheduler.stop()
    
    print("Config scheduler example completed")


# Example 6: Scheduler monitoring
async def example_monitoring_scheduler():
    """Example of scheduler with monitoring."""
    print("=== Example 6: Monitoring Scheduler ===")
    
    scheduler = TaskScheduler()
    
    # Add some tasks
    async def task1():
        print("Task 1 executed")
        await asyncio.sleep(1)
        
    async def task2():
        print("Task 2 executed")
        await asyncio.sleep(2)
        
    scheduler.add_task("task1", task1, timedelta(seconds=5), priority=5)
    scheduler.add_task("task2", task2, timedelta(seconds=8), priority=3)
    
    # Start scheduler
    await scheduler.start()
    
    # Monitor for 30 seconds
    for i in range(6):
        await asyncio.sleep(5)
        
        # Get status
        status = scheduler.get_status()
        summary = get_task_summary(status["tasks"])
        
        print(f"\n--- Status Update {i+1} ---")
        print(f"Total tasks: {summary['total']}")
        print(f"Enabled tasks: {summary['enabled']}")
        print(f"Running tasks: {summary['running']}")
        print(f"Completed tasks: {summary['completed']}")
        print(f"Failed tasks: {summary['failed']}")
        
        # Get next scheduled tasks
        next_tasks = []
        for name, task_info in status["tasks"].items():
            if task_info.get("next_run"):
                next_tasks.append({
                    "name": name,
                    "next_run": task_info["next_run"]
                })
                
        next_tasks.sort(key=lambda x: x["next_run"])
        print("Next scheduled tasks:")
        for task in next_tasks[:3]:
            print(f"  {task['name']}: {task['next_run']}")
            
    # Stop scheduler
    await scheduler.stop()
    
    print("Monitoring scheduler example completed")


# Example 7: Real-world integration
async def example_real_integration():
    """Example of real-world integration."""
    print("=== Example 7: Real Integration ===")
    
    # Create integration
    trading_calendar = TradingCalendar()
    scheduler = TaskScheduler(trading_calendar)
    integration = SchedulerIntegration(scheduler, trading_calendar)
    
    # Setup tasks
    integration.setup_all_tasks(
        data_loader_func=lambda: print("Market data updated"),
        news_fetch_func=lambda: print("News fetched"),
        news_process_func=lambda: print("News processed"),
        indicators_func=lambda: print("Indicators calculated"),
        signals_func=lambda: print("Signals generated"),
        notification_func=lambda: print("Notifications sent")
    )
    
    # Start scheduler
    integration.start_scheduler()
    
    # Run for 60 seconds
    await asyncio.sleep(60)
    
    # Stop scheduler
    integration.stop_scheduler()
    
    # Print final status
    status = integration.get_task_status()
    print(f"\nFinal status: {status}")
    
    print("Real integration example completed")


# Main function to run all examples
async def main():
    """Run all examples."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    examples = [
        example_basic_scheduler,
        example_trading_scheduler,
        example_dependency_scheduler,
        example_error_handling_scheduler,
        example_config_scheduler,
        example_monitoring_scheduler,
        example_real_integration,
    ]
    
    for example in examples:
        try:
            await example()
            print(f"\n{example.__name__} completed successfully\n")
        except Exception as e:
            print(f"\n{example.__name__} failed: {e}\n")
            
        # Wait between examples
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())

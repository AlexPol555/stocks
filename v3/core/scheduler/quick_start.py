"""Quick start guide for the task scheduler.

This module provides a simple example of how to get started
with the task scheduler in your application.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from .scheduler import TaskScheduler
from .trading_calendar import TradingCalendar, Market
from .integration import SchedulerIntegration

logger = logging.getLogger(__name__)


async def example_task_1():
    """Example task 1: Simple data processing."""
    print(f"Task 1 executed at {datetime.now()}")
    await asyncio.sleep(1)  # Simulate work


async def example_task_2():
    """Example task 2: News processing."""
    print(f"Task 2 executed at {datetime.now()}")
    await asyncio.sleep(2)  # Simulate work


async def example_task_3():
    """Example task 3: Signal generation."""
    print(f"Task 3 executed at {datetime.now()}")
    await asyncio.sleep(1)  # Simulate work


def example_sync_task():
    """Example synchronous task."""
    print(f"Sync task executed at {datetime.now()}")


async def quick_start_example():
    """Quick start example showing basic scheduler usage."""
    print("=== Quick Start Example ===")
    
    # 1. Create scheduler
    print("1. Creating scheduler...")
    trading_calendar = TradingCalendar()
    scheduler = TaskScheduler(trading_calendar)
    
    # 2. Add tasks
    print("2. Adding tasks...")
    
    # Add async task
    scheduler.add_task(
        name="data_processing",
        func=example_task_1,
        interval=timedelta(seconds=5),
        priority=10
    )
    
    # Add another async task
    scheduler.add_task(
        name="news_processing",
        func=example_task_2,
        interval=timedelta(seconds=8),
        priority=5
    )
    
    # Add sync task
    scheduler.add_task(
        name="signal_generation",
        func=example_sync_task,
        interval=timedelta(seconds=10),
        priority=3
    )
    
    # Add task with dependencies
    scheduler.add_task(
        name="final_processing",
        func=example_task_3,
        interval=timedelta(seconds=12),
        priority=1,
        dependencies=["data_processing", "news_processing"]
    )
    
    print("3. Starting scheduler...")
    
    # 3. Start scheduler
    await scheduler.start()
    
    # 4. Run for 30 seconds
    print("4. Running for 30 seconds...")
    await asyncio.sleep(30)
    
    # 5. Stop scheduler
    print("5. Stopping scheduler...")
    await scheduler.stop()
    
    # 6. Show final status
    print("6. Final status:")
    status = scheduler.get_status()
    print(f"Total tasks: {status['total_tasks']}")
    print(f"Enabled tasks: {status['enabled_tasks']}")
    print(f"Running tasks: {status['running_tasks']}")
    print(f"Failed tasks: {status['failed_tasks']}")
    
    print("Quick start example completed!")


async def trading_calendar_example():
    """Example showing trading calendar integration."""
    print("=== Trading Calendar Example ===")
    
    # Create trading calendar
    calendar = TradingCalendar()
    
    # Check if it's a trading day
    is_trading = calendar.is_trading_day()
    print(f"Is trading day: {is_trading}")
    
    # Check if MOEX is open
    is_moex_open = calendar.is_market_open(Market.MOEX)
    print(f"MOEX is open: {is_moex_open}")
    
    # Get next trading day
    next_trading = calendar.get_next_trading_day()
    print(f"Next trading day: {next_trading}")
    
    # Check if task should run
    should_run = calendar.should_run_task("update_market_data", Market.MOEX)
    print(f"Should run market data task: {should_run}")
    
    # Get optimal run time
    optimal_time = calendar.get_optimal_run_time("update_market_data", Market.MOEX)
    print(f"Optimal run time: {optimal_time}")


async def integration_example():
    """Example showing integration with existing modules."""
    print("=== Integration Example ===")
    
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
    
    # Run for 20 seconds
    await asyncio.sleep(20)
    
    # Stop scheduler
    integration.stop_scheduler()
    
    # Show status
    status = integration.get_task_status()
    print(f"Integration status: {status}")


async def error_handling_example():
    """Example showing error handling."""
    print("=== Error Handling Example ===")
    
    # Create scheduler
    scheduler = TaskScheduler()
    
    # Add task that sometimes fails
    async def unreliable_task():
        import random
        if random.random() < 0.7:  # 70% chance of failure
            raise Exception("Random failure")
        print("Task completed successfully")
    
    scheduler.add_task(
        name="unreliable_task",
        func=unreliable_task,
        interval=timedelta(seconds=3),
        priority=5,
        max_errors=3
    )
    
    # Start scheduler
    await scheduler.start()
    
    # Run for 20 seconds
    await asyncio.sleep(20)
    
    # Stop scheduler
    await scheduler.stop()
    
    # Show status
    status = scheduler.get_status()
    print(f"Error handling status: {status}")


async def monitoring_example():
    """Example showing monitoring capabilities."""
    print("=== Monitoring Example ===")
    
    # Create scheduler
    scheduler = TaskScheduler()
    
    # Add some tasks
    scheduler.add_task("task1", example_task_1, timedelta(seconds=5), priority=10)
    scheduler.add_task("task2", example_task_2, timedelta(seconds=8), priority=5)
    scheduler.add_task("task3", example_sync_task, timedelta(seconds=10), priority=3)
    
    # Start scheduler
    await scheduler.start()
    
    # Monitor for 30 seconds
    for i in range(6):
        await asyncio.sleep(5)
        
        # Get status
        status = scheduler.get_status()
        print(f"\n--- Status Update {i+1} ---")
        print(f"Total tasks: {status['total_tasks']}")
        print(f"Enabled tasks: {status['enabled_tasks']}")
        print(f"Running tasks: {status['running_tasks']}")
        print(f"Failed tasks: {status['failed_tasks']}")
        
        # Get next scheduled tasks
        next_tasks = []
        for name, task_info in status['tasks'].items():
            if task_info.get('next_run'):
                next_tasks.append({
                    'name': name,
                    'next_run': task_info['next_run']
                })
                
        next_tasks.sort(key=lambda x: x['next_run'])
        print("Next scheduled tasks:")
        for task in next_tasks[:3]:
            print(f"  {task['name']}: {task['next_run']}")
            
    # Stop scheduler
    await scheduler.stop()
    
    print("Monitoring example completed!")


async def main():
    """Main function running all examples."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    examples = [
        ("Quick Start", quick_start_example),
        ("Trading Calendar", trading_calendar_example),
        ("Integration", integration_example),
        ("Error Handling", error_handling_example),
        ("Monitoring", monitoring_example),
    ]
    
    for name, example_func in examples:
        try:
            print(f"\n{'='*50}")
            print(f"Running {name} Example")
            print('='*50)
            await example_func()
            print(f"{name} example completed successfully")
        except Exception as e:
            print(f"{name} example failed: {e}")
            logger.exception(f"Error in {name} example")
            
        # Wait between examples
        await asyncio.sleep(2)
        
    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(main())

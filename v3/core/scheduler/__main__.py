"""Main entry point for the task scheduler module.

This module provides the main entry point for running the task scheduler
as a standalone application or as part of the main trading system.
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime
from typing import Optional

from .scheduler import TaskScheduler
from .trading_calendar import TradingCalendar
from .integration import SchedulerIntegration
from .real_integration import RealSchedulerIntegration
from .migrations import run_migrations, get_migration_status
from .cli import main as cli_main

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration.
    
    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('scheduler.log')
        ]
    )


async def run_scheduler(api_key: Optional[str] = None) -> None:
    """Run the task scheduler.
    
    Args:
        api_key: Tinkoff API key for market data
    """
    try:
        # Create scheduler integration
        integration = RealSchedulerIntegration(api_key)
        
        # Start scheduler
        integration.start_scheduler()
        
        logger.info("Task scheduler started successfully")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping scheduler...")
            
    except Exception as e:
        logger.error(f"Error running scheduler: {e}")
        raise
    finally:
        # Stop scheduler
        if 'integration' in locals():
            integration.stop_scheduler()
            logger.info("Task scheduler stopped")


async def run_example() -> None:
    """Run example scheduler."""
    try:
        # Create basic scheduler
        trading_calendar = TradingCalendar()
        scheduler = TaskScheduler(trading_calendar)
        
        # Add example tasks
        async def example_task_1():
            logger.info("Example task 1 executed")
            await asyncio.sleep(1)
            
        async def example_task_2():
            logger.info("Example task 2 executed")
            await asyncio.sleep(2)
            
        scheduler.add_task(
            name="example_task_1",
            func=example_task_1,
            interval=timedelta(seconds=5),
            priority=10
        )
        
        scheduler.add_task(
            name="example_task_2",
            func=example_task_2,
            interval=timedelta(seconds=8),
            priority=5
        )
        
        # Start scheduler
        await scheduler.start()
        
        logger.info("Example scheduler started, running for 30 seconds...")
        
        # Run for 30 seconds
        await asyncio.sleep(30)
        
        # Stop scheduler
        await scheduler.stop()
        
        logger.info("Example scheduler stopped")
        
    except Exception as e:
        logger.error(f"Error running example: {e}")
        raise


def run_migrations_cli(db_path: str) -> None:
    """Run database migrations.
    
    Args:
        db_path: Path to database file
    """
    try:
        run_migrations(db_path)
        print("Migrations completed successfully")
    except Exception as e:
        print(f"Error running migrations: {e}")
        sys.exit(1)


def show_migration_status(db_path: str) -> None:
    """Show migration status.
    
    Args:
        db_path: Path to database file
    """
    try:
        status = get_migration_status(db_path)
        
        print("Migration Status:")
        print("-" * 50)
        
        for migration in status:
            status_text = "✓ Applied" if migration["applied"] else "✗ Pending"
            applied_at = migration["applied_at"] or "N/A"
            print(f"{migration['name']}: {status_text} ({applied_at})")
            
    except Exception as e:
        print(f"Error getting migration status: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Task Scheduler")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--api-key", help="Tinkoff API key")
    parser.add_argument("--db-path", default="stock_data.db", help="Database path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run scheduler command
    run_parser = subparsers.add_parser("run", help="Run the task scheduler")
    run_parser.add_argument("--api-key", help="Tinkoff API key")
    
    # Run example command
    subparsers.add_parser("example", help="Run example scheduler")
    
    # Migrations command
    migrate_parser = subparsers.add_parser("migrate", help="Run database migrations")
    migrate_parser.add_argument("--db-path", default="stock_data.db", help="Database path")
    
    # Migration status command
    status_parser = subparsers.add_parser("migration-status", help="Show migration status")
    status_parser.add_argument("--db-path", default="stock_data.db", help="Database path")
    
    # CLI command
    subparsers.add_parser("cli", help="Run CLI interface")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Execute command
    try:
        if args.command == "run":
            asyncio.run(run_scheduler(args.api_key))
        elif args.command == "example":
            asyncio.run(run_example())
        elif args.command == "migrate":
            run_migrations_cli(args.db_path)
        elif args.command == "migration-status":
            show_migration_status(args.db_path)
        elif args.command == "cli":
            cli_main()
        else:
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

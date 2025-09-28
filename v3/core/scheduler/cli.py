"""Command-line interface for the task scheduler.

This module provides a CLI for managing the task scheduler,
including starting, stopping, and monitoring tasks.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .scheduler import TaskScheduler
from .trading_calendar import TradingCalendar
from .integration import SchedulerIntegration
from .migrations import run_migrations, get_migration_status
from .config import get_config, get_task_config

logger = logging.getLogger(__name__)


class SchedulerCLI:
    """Command-line interface for the task scheduler."""
    
    def __init__(self, db_path: str):
        """Initialize CLI.
        
        Args:
            db_path: Path to the database file
        """
        self.db_path = db_path
        self.trading_calendar = TradingCalendar()
        self.scheduler = TaskScheduler(self.trading_calendar)
        self.integration = SchedulerIntegration(self.scheduler, self.trading_calendar)
        
    def setup_logging(self, level: str = "INFO") -> None:
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
        
    def run_migrations(self) -> None:
        """Run database migrations."""
        print("Running database migrations...")
        try:
            run_migrations(self.db_path)
            print("Migrations completed successfully")
        except Exception as e:
            print(f"Error running migrations: {e}")
            sys.exit(1)
            
    def show_migration_status(self) -> None:
        """Show migration status."""
        print("Migration Status:")
        print("-" * 50)
        
        try:
            status = get_migration_status(self.db_path)
            for migration in status:
                status_text = "✓ Applied" if migration["applied"] else "✗ Pending"
                applied_at = migration["applied_at"] or "N/A"
                print(f"{migration['name']}: {status_text} ({applied_at})")
                
        except Exception as e:
            print(f"Error getting migration status: {e}")
            sys.exit(1)
            
    def show_status(self) -> None:
        """Show scheduler status."""
        print("Scheduler Status:")
        print("-" * 50)
        
        try:
            status = self.scheduler.get_status()
            
            print(f"Running: {status['running']}")
            print(f"Total tasks: {status['total_tasks']}")
            print(f"Enabled tasks: {status['enabled_tasks']}")
            print(f"Running tasks: {status['running_tasks']}")
            print(f"Failed tasks: {status['failed_tasks']}")
            
            print("\nTask Details:")
            print("-" * 50)
            for name, task_info in status['tasks'].items():
                print(f"\n{name}:")
                print(f"  Status: {task_info['status']}")
                print(f"  Enabled: {task_info['enabled']}")
                print(f"  Last run: {task_info['last_run'] or 'Never'}")
                print(f"  Next run: {task_info['next_run'] or 'Not scheduled'}")
                print(f"  Error count: {task_info['error_count']}")
                
        except Exception as e:
            print(f"Error getting status: {e}")
            sys.exit(1)
            
    def show_tasks(self) -> None:
        """Show all tasks."""
        print("Tasks:")
        print("-" * 50)
        
        try:
            status = self.scheduler.get_status()
            
            for name, task_info in status['tasks'].items():
                print(f"\n{name}:")
                print(f"  Status: {task_info['status']}")
                print(f"  Enabled: {task_info['enabled']}")
                print(f"  Last run: {task_info['last_run'] or 'Never'}")
                print(f"  Next run: {task_info['next_run'] or 'Not scheduled'}")
                print(f"  Error count: {task_info['error_count']}")
                
        except Exception as e:
            print(f"Error getting tasks: {e}")
            sys.exit(1)
            
    def enable_task(self, task_name: str) -> None:
        """Enable a task.
        
        Args:
            task_name: Name of task to enable
        """
        try:
            self.scheduler.enable_task(task_name)
            print(f"Task '{task_name}' enabled")
        except Exception as e:
            print(f"Error enabling task '{task_name}': {e}")
            sys.exit(1)
            
    def disable_task(self, task_name: str) -> None:
        """Disable a task.
        
        Args:
            task_name: Name of task to disable
        """
        try:
            self.scheduler.disable_task(task_name)
            print(f"Task '{task_name}' disabled")
        except Exception as e:
            print(f"Error disabling task '{task_name}': {e}")
            sys.exit(1)
            
    def show_config(self) -> None:
        """Show scheduler configuration."""
        print("Scheduler Configuration:")
        print("-" * 50)
        
        try:
            config = get_config()
            
            print("Task Intervals:")
            for task_name, interval in config["intervals"].items():
                print(f"  {task_name}: {interval}")
                
            print("\nTask Priorities:")
            for task_name, priority in config["priorities"].items():
                print(f"  {task_name}: {priority}")
                
            print("\nTask Dependencies:")
            for task_name, dependencies in config["dependencies"].items():
                print(f"  {task_name}: {dependencies}")
                
            print("\nMarket Hours:")
            for market, hours in config["market_hours"].items():
                print(f"  {market}: {hours['start']} - {hours['end']} ({hours['timezone']})")
                
        except Exception as e:
            print(f"Error getting configuration: {e}")
            sys.exit(1)
            
    def show_health(self) -> None:
        """Show scheduler health status."""
        print("Scheduler Health:")
        print("-" * 50)
        
        try:
            status = self.scheduler.get_status()
            
            # Calculate health metrics
            total_tasks = status['total_tasks']
            enabled_tasks = status['enabled_tasks']
            running_tasks = status['running_tasks']
            failed_tasks = status['failed_tasks']
            
            print(f"Total tasks: {total_tasks}")
            print(f"Enabled tasks: {enabled_tasks}")
            print(f"Running tasks: {running_tasks}")
            print(f"Failed tasks: {failed_tasks}")
            
            # Health status
            if failed_tasks > 0:
                health = "UNHEALTHY"
            elif running_tasks > 0:
                health = "RUNNING"
            elif enabled_tasks > 0:
                health = "HEALTHY"
            else:
                health = "IDLE"
                
            print(f"\nHealth Status: {health}")
            
            # Error rate
            if total_tasks > 0:
                error_rate = (failed_tasks / total_tasks) * 100
                print(f"Error Rate: {error_rate:.1f}%")
                
        except Exception as e:
            print(f"Error getting health status: {e}")
            sys.exit(1)
            
    def show_metrics(self) -> None:
        """Show scheduler metrics."""
        print("Scheduler Metrics:")
        print("-" * 50)
        
        try:
            status = self.scheduler.get_status()
            
            # Calculate metrics
            total_tasks = status['total_tasks']
            enabled_tasks = status['enabled_tasks']
            running_tasks = status['running_tasks']
            failed_tasks = status['failed_tasks']
            
            print(f"Total tasks: {total_tasks}")
            print(f"Enabled tasks: {enabled_tasks}")
            print(f"Running tasks: {running_tasks}")
            print(f"Failed tasks: {failed_tasks}")
            
            # Task load
            if total_tasks > 0:
                task_load = (running_tasks / total_tasks) * 100
                print(f"Task load: {task_load:.1f}%")
                
            # Error rate
            if total_tasks > 0:
                error_rate = (failed_tasks / total_tasks) * 100
                print(f"Error rate: {error_rate:.1f}%")
                
            # Next scheduled tasks
            print("\nNext Scheduled Tasks:")
            next_tasks = []
            for name, task_info in status['tasks'].items():
                if task_info.get('next_run'):
                    next_tasks.append({
                        'name': name,
                        'next_run': task_info['next_run']
                    })
                    
            next_tasks.sort(key=lambda x: x['next_run'])
            for task in next_tasks[:5]:
                print(f"  {task['name']}: {task['next_run']}")
                
        except Exception as e:
            print(f"Error getting metrics: {e}")
            sys.exit(1)
            
    def export_config(self, output_file: str) -> None:
        """Export configuration to file.
        
        Args:
            output_file: Output file path
        """
        try:
            config = get_config()
            
            with open(output_file, 'w') as f:
                json.dump(config, f, indent=2, default=str)
                
            print(f"Configuration exported to {output_file}")
            
        except Exception as e:
            print(f"Error exporting configuration: {e}")
            sys.exit(1)
            
    def import_config(self, input_file: str) -> None:
        """Import configuration from file.
        
        Args:
            input_file: Input file path
        """
        try:
            with open(input_file, 'r') as f:
                config = json.load(f)
                
            # Validate configuration
            # This is a simplified validation
            required_keys = ["intervals", "priorities", "dependencies"]
            for key in required_keys:
                if key not in config:
                    print(f"Error: Missing required key '{key}' in configuration")
                    sys.exit(1)
                    
            print(f"Configuration imported from {input_file}")
            print("Note: Configuration import is not yet fully implemented")
            
        except Exception as e:
            print(f"Error importing configuration: {e}")
            sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Task Scheduler CLI")
    parser.add_argument("--db-path", required=True, help="Database file path")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Migration commands
    subparsers.add_parser("migrate", help="Run database migrations")
    subparsers.add_parser("migration-status", help="Show migration status")
    
    # Status commands
    subparsers.add_parser("status", help="Show scheduler status")
    subparsers.add_parser("tasks", help="Show all tasks")
    subparsers.add_parser("health", help="Show health status")
    subparsers.add_parser("metrics", help="Show metrics")
    
    # Task management commands
    task_parser = subparsers.add_parser("enable-task", help="Enable a task")
    task_parser.add_argument("task_name", help="Name of task to enable")
    
    task_parser = subparsers.add_parser("disable-task", help="Disable a task")
    task_parser.add_argument("task_name", help="Name of task to disable")
    
    # Configuration commands
    subparsers.add_parser("config", help="Show configuration")
    
    config_parser = subparsers.add_parser("export-config", help="Export configuration")
    config_parser.add_argument("output_file", help="Output file path")
    
    config_parser = subparsers.add_parser("import-config", help="Import configuration")
    config_parser.add_argument("input_file", help="Input file path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    # Create CLI instance
    cli = SchedulerCLI(args.db_path)
    cli.setup_logging(args.log_level)
    
    # Execute command
    try:
        if args.command == "migrate":
            cli.run_migrations()
        elif args.command == "migration-status":
            cli.show_migration_status()
        elif args.command == "status":
            cli.show_status()
        elif args.command == "tasks":
            cli.show_tasks()
        elif args.command == "health":
            cli.show_health()
        elif args.command == "metrics":
            cli.show_metrics()
        elif args.command == "enable-task":
            cli.enable_task(args.task_name)
        elif args.command == "disable-task":
            cli.disable_task(args.task_name)
        elif args.command == "config":
            cli.show_config()
        elif args.command == "export-config":
            cli.export_config(args.output_file)
        elif args.command == "import-config":
            cli.import_config(args.input_file)
        else:
            print(f"Unknown command: {args.command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

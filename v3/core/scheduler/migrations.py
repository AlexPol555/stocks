"""Database migrations for the task scheduler.

This module provides database migration functionality for the task scheduler,
including schema creation and updates.
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SchedulerMigrations:
    """Handles database migrations for the task scheduler."""
    
    def __init__(self, db_path: str):
        """Initialize migrations.
        
        Args:
            db_path: Path to the database file
        """
        self.db_path = db_path
        self.migrations = [
            self._create_scheduler_tables,
            self._create_task_logs_table,
            self._create_scheduler_config_table,
            self._create_task_metrics_table,
        ]
        
    def migrate(self) -> None:
        """Run all pending migrations."""
        logger.info("Starting scheduler migrations...")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Create migrations table if it doesn't exist
                self._create_migrations_table(conn)
                
                # Get applied migrations
                applied_migrations = self._get_applied_migrations(conn)
                
                # Run pending migrations
                for migration in self.migrations:
                    migration_name = migration.__name__
                    if migration_name not in applied_migrations:
                        logger.info(f"Running migration: {migration_name}")
                        migration(conn)
                        self._record_migration(conn, migration_name)
                        logger.info(f"Migration {migration_name} completed")
                    else:
                        logger.debug(f"Migration {migration_name} already applied")
                        
            logger.info("Scheduler migrations completed successfully")
            
        except Exception as e:
            logger.error(f"Error running migrations: {e}")
            raise
            
    def _create_migrations_table(self, conn: sqlite3.Connection) -> None:
        """Create migrations tracking table."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
    def _get_applied_migrations(self, conn: sqlite3.Connection) -> List[str]:
        """Get list of applied migrations."""
        cursor = conn.cursor()
        cursor.execute("SELECT migration_name FROM scheduler_migrations")
        return [row[0] for row in cursor.fetchall()]
        
    def _record_migration(self, conn: sqlite3.Connection, migration_name: str) -> None:
        """Record a migration as applied."""
        conn.execute(
            "INSERT INTO scheduler_migrations (migration_name) VALUES (?)",
            (migration_name,)
        )
        conn.commit()
        
    def _create_scheduler_tables(self, conn: sqlite3.Connection) -> None:
        """Create main scheduler tables."""
        # Tasks table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                func_name TEXT NOT NULL,
                interval_seconds INTEGER NOT NULL,
                priority INTEGER DEFAULT 0,
                max_errors INTEGER DEFAULT 3,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Task dependencies table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_task_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                dependency_task_id INTEGER NOT NULL,
                FOREIGN KEY (task_id) REFERENCES scheduler_tasks (id),
                FOREIGN KEY (dependency_task_id) REFERENCES scheduler_tasks (id),
                UNIQUE (task_id, dependency_task_id)
            )
        """)
        
        # Task executions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_task_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                started_at TIMESTAMP NOT NULL,
                finished_at TIMESTAMP,
                status TEXT NOT NULL,
                error_message TEXT,
                execution_time_ms INTEGER,
                FOREIGN KEY (task_id) REFERENCES scheduler_tasks (id)
            )
        """)
        
        conn.commit()
        
    def _create_task_logs_table(self, conn: sqlite3.Connection) -> None:
        """Create task logs table."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                log_level TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES scheduler_tasks (id)
            )
        """)
        
        # Create index for better performance
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduler_task_logs_task_id 
            ON scheduler_task_logs (task_id)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduler_task_logs_timestamp 
            ON scheduler_task_logs (timestamp)
        """)
        
        conn.commit()
        
    def _create_scheduler_config_table(self, conn: sqlite3.Connection) -> None:
        """Create scheduler configuration table."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                config_type TEXT DEFAULT 'string',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default configuration
        default_config = [
            ("max_concurrent_tasks", "5", "integer", "Maximum number of concurrent tasks"),
            ("task_timeout_seconds", "300", "integer", "Default task timeout in seconds"),
            ("retry_delay_seconds", "60", "integer", "Default retry delay in seconds"),
            ("max_retries", "3", "integer", "Maximum number of retries"),
            ("enable_notifications", "true", "boolean", "Enable notification system"),
            ("log_level", "INFO", "string", "Logging level"),
        ]
        
        for key, value, config_type, description in default_config:
            conn.execute("""
                INSERT OR IGNORE INTO scheduler_config 
                (config_key, config_value, config_type, description)
                VALUES (?, ?, ?, ?)
            """, (key, value, config_type, description))
            
        conn.commit()
        
    def _create_task_metrics_table(self, conn: sqlite3.Connection) -> None:
        """Create task metrics table."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_task_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES scheduler_tasks (id)
            )
        """)
        
        # Create index for better performance
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduler_task_metrics_task_id 
            ON scheduler_task_metrics (task_id)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduler_task_metrics_timestamp 
            ON scheduler_task_metrics (metric_timestamp)
        """)
        
        conn.commit()
        
    def rollback(self, migration_name: str) -> None:
        """Rollback a specific migration.
        
        Args:
            migration_name: Name of migration to rollback
        """
        logger.info(f"Rolling back migration: {migration_name}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Remove migration record
                conn.execute(
                    "DELETE FROM scheduler_migrations WHERE migration_name = ?",
                    (migration_name,)
                )
                
                # Rollback specific migration
                if migration_name == "create_scheduler_tables":
                    self._rollback_scheduler_tables(conn)
                elif migration_name == "create_task_logs_table":
                    self._rollback_task_logs_table(conn)
                elif migration_name == "create_scheduler_config_table":
                    self._rollback_scheduler_config_table(conn)
                elif migration_name == "create_task_metrics_table":
                    self._rollback_task_metrics_table(conn)
                    
                conn.commit()
                logger.info(f"Migration {migration_name} rolled back successfully")
                
        except Exception as e:
            logger.error(f"Error rolling back migration {migration_name}: {e}")
            raise
            
    def _rollback_scheduler_tables(self, conn: sqlite3.Connection) -> None:
        """Rollback scheduler tables."""
        conn.execute("DROP TABLE IF EXISTS scheduler_task_executions")
        conn.execute("DROP TABLE IF EXISTS scheduler_task_dependencies")
        conn.execute("DROP TABLE IF EXISTS scheduler_tasks")
        
    def _rollback_task_logs_table(self, conn: sqlite3.Connection) -> None:
        """Rollback task logs table."""
        conn.execute("DROP TABLE IF EXISTS scheduler_task_logs")
        
    def _rollback_scheduler_config_table(self, conn: sqlite3.Connection) -> None:
        """Rollback scheduler config table."""
        conn.execute("DROP TABLE IF EXISTS scheduler_config")
        
    def _rollback_task_metrics_table(self, conn: sqlite3.Connection) -> None:
        """Rollback task metrics table."""
        conn.execute("DROP TABLE IF EXISTS scheduler_task_metrics")
        
    def get_migration_status(self) -> List[Dict[str, Any]]:
        """Get status of all migrations.
        
        Returns:
            List of migration status information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT migration_name, applied_at 
                    FROM scheduler_migrations 
                    ORDER BY applied_at
                """)
                
                applied_migrations = {row[0]: row[1] for row in cursor.fetchall()}
                
                status = []
                for migration in self.migrations:
                    migration_name = migration.__name__
                    status.append({
                        "name": migration_name,
                        "applied": migration_name in applied_migrations,
                        "applied_at": applied_migrations.get(migration_name),
                        "description": migration.__doc__ or "No description available"
                    })
                    
                return status
                
        except Exception as e:
            logger.error(f"Error getting migration status: {e}")
            return []
            
    def reset_all_migrations(self) -> None:
        """Reset all migrations (WARNING: This will delete all data)."""
        logger.warning("Resetting all migrations - this will delete all data!")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Drop all scheduler tables
                conn.execute("DROP TABLE IF EXISTS scheduler_task_metrics")
                conn.execute("DROP TABLE IF EXISTS scheduler_config")
                conn.execute("DROP TABLE IF EXISTS scheduler_task_logs")
                conn.execute("DROP TABLE IF EXISTS scheduler_task_executions")
                conn.execute("DROP TABLE IF EXISTS scheduler_task_dependencies")
                conn.execute("DROP TABLE IF EXISTS scheduler_tasks")
                conn.execute("DROP TABLE IF EXISTS scheduler_migrations")
                
                conn.commit()
                logger.info("All migrations reset successfully")
                
        except Exception as e:
            logger.error(f"Error resetting migrations: {e}")
            raise


def run_migrations(db_path: str) -> None:
    """Run scheduler migrations.
    
    Args:
        db_path: Path to the database file
    """
    migrations = SchedulerMigrations(db_path)
    migrations.migrate()


def get_migration_status(db_path: str) -> List[Dict[str, Any]]:
    """Get migration status.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        List of migration status information
    """
    migrations = SchedulerMigrations(db_path)
    return migrations.get_migration_status()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python migrations.py <db_path> [status|migrate|reset]")
        sys.exit(1)
        
    db_path = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "migrate"
    
    if action == "migrate":
        run_migrations(db_path)
    elif action == "status":
        status = get_migration_status(db_path)
        for migration in status:
            print(f"{migration['name']}: {'Applied' if migration['applied'] else 'Pending'}")
    elif action == "reset":
        migrations = SchedulerMigrations(db_path)
        migrations.reset_all_migrations()
    else:
        print("Invalid action. Use: status, migrate, or reset")
        sys.exit(1)

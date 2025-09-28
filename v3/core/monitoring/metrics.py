"""System metrics collection and monitoring."""

from __future__ import annotations

import asyncio
import logging
import psutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
import threading

from core.settings import get_settings


logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System metrics container."""
    
    # CPU metrics
    cpu_percent: float = 0.0
    cpu_count: int = 0
    
    # Memory metrics
    memory_total: int = 0
    memory_available: int = 0
    memory_used: int = 0
    memory_percent: float = 0.0
    
    # Disk metrics
    disk_total: int = 0
    disk_used: int = 0
    disk_free: int = 0
    disk_percent: float = 0.0
    
    # Process metrics
    process_cpu_percent: float = 0.0
    process_memory_rss: int = 0
    process_memory_vms: int = 0
    process_num_threads: int = 0
    
    # Application metrics
    database_size: int = 0
    database_connections: int = 0
    active_signals: int = 0
    trades_today: int = 0
    
    # Timestamps
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cpu_percent": self.cpu_percent,
            "cpu_count": self.cpu_count,
            "memory_total": self.memory_total,
            "memory_available": self.memory_available,
            "memory_used": self.memory_used,
            "memory_percent": self.memory_percent,
            "disk_total": self.disk_total,
            "disk_used": self.disk_used,
            "disk_free": self.disk_free,
            "disk_percent": self.disk_percent,
            "process_cpu_percent": self.process_cpu_percent,
            "process_memory_rss": self.process_memory_rss,
            "process_memory_vms": self.process_memory_vms,
            "process_num_threads": self.process_num_threads,
            "database_size": self.database_size,
            "database_connections": self.database_connections,
            "active_signals": self.active_signals,
            "trades_today": self.trades_today,
            "timestamp": self.timestamp.isoformat()
        }


class MetricsCollector:
    """Collects and stores system metrics."""
    
    def __init__(self, max_history: int = 1000):
        """Initialize metrics collector.
        
        Args:
            max_history: Maximum number of historical data points to keep
        """
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.current_metrics: Optional[SystemMetrics] = None
        self._lock = threading.Lock()
        self._running = False
        self._collection_task: Optional[asyncio.Task] = None
    
    async def start_collection(self, interval: float = 60.0) -> None:
        """Start automatic metrics collection.
        
        Args:
            interval: Collection interval in seconds
        """
        if self._running:
            logger.warning("Metrics collection already running")
            return
        
        self._running = True
        self._collection_task = asyncio.create_task(
            self._collection_loop(interval)
        )
        logger.info(f"Started metrics collection with {interval}s interval")
    
    async def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        if not self._running:
            return
        
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped metrics collection")
    
    async def _collection_loop(self, interval: float) -> None:
        """Main collection loop."""
        while self._running:
            try:
                await self.collect_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(interval)
    
    async def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics.
        
        Returns:
            Current system metrics
        """
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            memory = psutil.virtual_memory()
            
            # Get disk usage for database directory
            settings = get_settings()
            disk_usage = psutil.disk_usage(str(settings.database_path.parent))
            
            # Get process metrics
            process = psutil.Process()
            process_cpu = process.cpu_percent()
            process_memory = process.memory_info()
            
            # Get application-specific metrics
            app_metrics = await self._collect_application_metrics()
            
            # Create metrics object
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                cpu_count=cpu_count,
                memory_total=memory.total,
                memory_available=memory.available,
                memory_used=memory.used,
                memory_percent=memory.percent,
                disk_total=disk_usage.total,
                disk_used=disk_usage.used,
                disk_free=disk_usage.free,
                disk_percent=(disk_usage.used / disk_usage.total) * 100,
                process_cpu_percent=process_cpu,
                process_memory_rss=process_memory.rss,
                process_memory_vms=process_memory.vms,
                process_num_threads=process.num_threads(),
                **app_metrics
            )
            
            # Store metrics
            with self._lock:
                self.current_metrics = metrics
                self.metrics_history.append(metrics)
            
            logger.debug("Collected system metrics")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            # Return empty metrics on error
            return SystemMetrics()
    
    async def _collect_application_metrics(self) -> Dict[str, Any]:
        """Collect application-specific metrics.
        
        Returns:
            Dictionary of application metrics
        """
        try:
            # Get database size
            settings = get_settings()
            db_path = settings.database_path
            
            database_size = 0
            database_connections = 0
            active_signals = 0
            trades_today = 0
            
            if db_path.exists():
                database_size = db_path.stat().st_size
                
                # Try to get database-specific metrics
                try:
                    from core.utils import open_database_connection
                    conn = open_database_connection()
                    cursor = conn.cursor()
                    
                    # Count active signals (simplified)
                    try:
                        cursor.execute("""
                            SELECT COUNT(*) FROM daily_data 
                            WHERE date = (SELECT MAX(date) FROM daily_data)
                            AND (Adaptive_Buy_Signal = 1 OR Adaptive_Sell_Signal = 1 
                                 OR New_Adaptive_Buy_Signal = 1 OR New_Adaptive_Sell_Signal = 1)
                        """)
                        active_signals = cursor.fetchone()[0] or 0
                    except Exception:
                        active_signals = 0
                    
                    # Count trades today
                    try:
                        today = datetime.now().strftime("%Y-%m-%d")
                        cursor.execute("""
                            SELECT COUNT(*) FROM trades 
                            WHERE DATE(executed_at) = ?
                        """, (today,))
                        trades_today = cursor.fetchone()[0] or 0
                    except Exception:
                        trades_today = 0
                    
                    conn.close()
                    
                except Exception as e:
                    logger.debug(f"Could not get database metrics: {e}")
            
            return {
                "database_size": database_size,
                "database_connections": database_connections,
                "active_signals": active_signals,
                "trades_today": trades_today
            }
            
        except Exception as e:
            logger.error(f"Failed to collect application metrics: {e}")
            return {
                "database_size": 0,
                "database_connections": 0,
                "active_signals": 0,
                "trades_today": 0
            }
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get current metrics.
        
        Returns:
            Current metrics or None if not available
        """
        with self._lock:
            return self.current_metrics
    
    def get_metrics_history(
        self,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[SystemMetrics]:
        """Get historical metrics.
        
        Args:
            since: Get metrics since this time
            limit: Maximum number of metrics to return
            
        Returns:
            List of historical metrics
        """
        with self._lock:
            history = list(self.metrics_history)
        
        if since:
            history = [m for m in history if m.timestamp >= since]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_metrics_summary(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get metrics summary for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Summary dictionary
        """
        since = datetime.now() - timedelta(hours=hours)
        history = self.get_metrics_history(since=since)
        
        if not history:
            return {
                "period_hours": hours,
                "data_points": 0,
                "summary": {}
            }
        
        # Calculate summary statistics
        cpu_values = [m.cpu_percent for m in history]
        memory_values = [m.memory_percent for m in history]
        disk_values = [m.disk_percent for m in history]
        
        summary = {
            "period_hours": hours,
            "data_points": len(history),
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values)
            },
            "memory": {
                "avg": sum(memory_values) / len(memory_values),
                "min": min(memory_values),
                "max": max(memory_values)
            },
            "disk": {
                "avg": sum(disk_values) / len(disk_values),
                "min": min(disk_values),
                "max": max(disk_values)
            },
            "application": {
                "avg_active_signals": sum(m.active_signals for m in history) / len(history),
                "total_trades_today": history[-1].trades_today if history else 0,
                "database_size_mb": (history[-1].database_size / 1024 / 1024) if history else 0
            }
        }
        
        return summary
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current system alerts based on metrics.
        
        Returns:
            List of alert dictionaries
        """
        alerts = []
        current = self.get_current_metrics()
        
        if not current:
            return alerts
        
        # CPU alert
        if current.cpu_percent > 90:
            alerts.append({
                "type": "critical",
                "component": "cpu",
                "message": f"High CPU usage: {current.cpu_percent:.1f}%",
                "value": current.cpu_percent,
                "threshold": 90
            })
        elif current.cpu_percent > 80:
            alerts.append({
                "type": "warning",
                "component": "cpu",
                "message": f"Elevated CPU usage: {current.cpu_percent:.1f}%",
                "value": current.cpu_percent,
                "threshold": 80
            })
        
        # Memory alert
        if current.memory_percent > 95:
            alerts.append({
                "type": "critical",
                "component": "memory",
                "message": f"Critical memory usage: {current.memory_percent:.1f}%",
                "value": current.memory_percent,
                "threshold": 95
            })
        elif current.memory_percent > 85:
            alerts.append({
                "type": "warning",
                "component": "memory",
                "message": f"High memory usage: {current.memory_percent:.1f}%",
                "value": current.memory_percent,
                "threshold": 85
            })
        
        # Disk alert
        if current.disk_percent > 95:
            alerts.append({
                "type": "critical",
                "component": "disk",
                "message": f"Critical disk usage: {current.disk_percent:.1f}%",
                "value": current.disk_percent,
                "threshold": 95
            })
        elif current.disk_percent > 85:
            alerts.append({
                "type": "warning",
                "component": "disk",
                "message": f"High disk usage: {current.disk_percent:.1f}%",
                "value": current.disk_percent,
                "threshold": 85
            })
        
        # Process memory alert
        if current.process_memory_rss > 1024 * 1024 * 1024:  # 1GB
            alerts.append({
                "type": "warning",
                "component": "process",
                "message": f"High process memory: {current.process_memory_rss / 1024 / 1024:.1f}MB",
                "value": current.process_memory_rss,
                "threshold": 1024 * 1024 * 1024
            })
        
        return alerts
    
    def is_running(self) -> bool:
        """Check if metrics collection is running.
        
        Returns:
            True if running, False otherwise
        """
        return self._running

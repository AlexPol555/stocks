"""Health checks for system components."""

from __future__ import annotations

import asyncio
import logging
import os
import psutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import time

from core.settings import get_settings
from core.utils import open_database_connection


logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    
    component: str
    status: str  # "healthy", "warning", "critical", "unknown"
    message: str
    timestamp: datetime
    details: Dict[str, Any]
    response_time_ms: Optional[float] = None
    
    @property
    def is_healthy(self) -> bool:
        """Check if the component is healthy."""
        return self.status == "healthy"
    
    @property
    def is_critical(self) -> bool:
        """Check if the component is in critical state."""
        return self.status == "critical"


class HealthCheck:
    """Base class for health checks."""
    
    def __init__(self, name: str, timeout: float = 30.0):
        """Initialize health check.
        
        Args:
            name: Name of the health check
            timeout: Timeout in seconds
        """
        self.name = name
        self.timeout = timeout
    
    async def check(self) -> HealthCheckResult:
        """Perform the health check.
        
        Returns:
            Health check result
        """
        start_time = time.time()
        
        try:
            # Run the check with timeout
            result = await asyncio.wait_for(
                self._perform_check(),
                timeout=self.timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            result.response_time_ms = response_time
            
            return result
            
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component=self.name,
                status="critical",
                message=f"Health check timed out after {self.timeout}s",
                timestamp=datetime.now(),
                details={"timeout": self.timeout},
                response_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status="critical",
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)},
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _perform_check(self) -> HealthCheckResult:
        """Override this method to implement the actual health check."""
        raise NotImplementedError


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity."""
    
    def __init__(self):
        super().__init__("database", timeout=10.0)
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check database connectivity and basic operations."""
        try:
            # Get database path
            settings = get_settings()
            db_path = settings.database_path
            
            if not db_path.exists():
                return HealthCheckResult(
                    component=self.name,
                    status="critical",
                    message="Database file does not exist",
                    timestamp=datetime.now(),
                    details={"path": str(db_path)}
                )
            
            # Check file size
            file_size = db_path.stat().st_size
            if file_size == 0:
                return HealthCheckResult(
                    component=self.name,
                    status="critical",
                    message="Database file is empty",
                    timestamp=datetime.now(),
                    details={"path": str(db_path), "size": file_size}
                )
            
            # Test connection
            conn = open_database_connection()
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result[0] != 1:
                return HealthCheckResult(
                    component=self.name,
                    status="critical",
                    message="Database query test failed",
                    timestamp=datetime.now(),
                    details={"query_result": result}
                )
            
            # Check table existence
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('daily_data', 'trades', 'positions')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            missing_tables = {"daily_data", "trades", "positions"} - set(tables)
            if missing_tables:
                return HealthCheckResult(
                    component=self.name,
                    status="warning",
                    message=f"Missing tables: {', '.join(missing_tables)}",
                    timestamp=datetime.now(),
                    details={"existing_tables": tables, "missing_tables": list(missing_tables)}
                )
            
            return HealthCheckResult(
                component=self.name,
                status="healthy",
                message="Database is accessible and functional",
                timestamp=datetime.now(),
                details={
                    "path": str(db_path),
                    "size_bytes": file_size,
                    "tables": tables
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status="critical",
                message=f"Database check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )


class DiskSpaceHealthCheck(HealthCheck):
    """Health check for disk space."""
    
    def __init__(self, warning_threshold: float = 0.85, critical_threshold: float = 0.95):
        """Initialize disk space check.
        
        Args:
            warning_threshold: Warning threshold (0.0-1.0)
            critical_threshold: Critical threshold (0.0-1.0)
        """
        super().__init__("disk_space", timeout=5.0)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check available disk space."""
        try:
            # Get database path to check the same disk
            settings = get_settings()
            db_path = settings.database_path
            
            # Get disk usage
            disk_usage = psutil.disk_usage(str(db_path.parent))
            
            total = disk_usage.total
            used = disk_usage.used
            free = disk_usage.free
            percent_used = used / total
            
            details = {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "percent_used": percent_used,
                "path": str(db_path.parent)
            }
            
            if percent_used >= self.critical_threshold:
                return HealthCheckResult(
                    component=self.name,
                    status="critical",
                    message=f"Disk space critically low: {percent_used:.1%} used",
                    timestamp=datetime.now(),
                    details=details
                )
            elif percent_used >= self.warning_threshold:
                return HealthCheckResult(
                    component=self.name,
                    status="warning",
                    message=f"Disk space warning: {percent_used:.1%} used",
                    timestamp=datetime.now(),
                    details=details
                )
            else:
                return HealthCheckResult(
                    component=self.name,
                    status="healthy",
                    message=f"Disk space OK: {percent_used:.1%} used",
                    timestamp=datetime.now(),
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status="critical",
                message=f"Disk space check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )


class MemoryHealthCheck(HealthCheck):
    """Health check for memory usage."""
    
    def __init__(self, warning_threshold: float = 0.85, critical_threshold: float = 0.95):
        """Initialize memory check.
        
        Args:
            warning_threshold: Warning threshold (0.0-1.0)
            critical_threshold: Critical threshold (0.0-1.0)
        """
        super().__init__("memory", timeout=5.0)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check memory usage."""
        try:
            # Get memory usage
            memory = psutil.virtual_memory()
            
            total = memory.total
            available = memory.available
            used = memory.used
            percent_used = memory.percent / 100
            
            details = {
                "total_bytes": total,
                "used_bytes": used,
                "available_bytes": available,
                "percent_used": percent_used
            }
            
            if percent_used >= self.critical_threshold:
                return HealthCheckResult(
                    component=self.name,
                    status="critical",
                    message=f"Memory usage critically high: {memory.percent:.1f}%",
                    timestamp=datetime.now(),
                    details=details
                )
            elif percent_used >= self.warning_threshold:
                return HealthCheckResult(
                    component=self.name,
                    status="warning",
                    message=f"Memory usage warning: {memory.percent:.1f}%",
                    timestamp=datetime.now(),
                    details=details
                )
            else:
                return HealthCheckResult(
                    component=self.name,
                    status="healthy",
                    message=f"Memory usage OK: {memory.percent:.1f}%",
                    timestamp=datetime.now(),
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status="critical",
                message=f"Memory check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )


class ProcessHealthCheck(HealthCheck):
    """Health check for process status."""
    
    def __init__(self):
        super().__init__("process", timeout=5.0)
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check process status."""
        try:
            # Get current process
            process = psutil.Process()
            
            # Get process info
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            num_threads = process.num_threads()
            status = process.status()
            
            details = {
                "pid": process.pid,
                "cpu_percent": cpu_percent,
                "memory_rss": memory_info.rss,
                "memory_vms": memory_info.vms,
                "num_threads": num_threads,
                "status": status,
                "create_time": process.create_time()
            }
            
            # Check for potential issues
            issues = []
            if cpu_percent > 90:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            if memory_info.rss > 1024 * 1024 * 1024:  # 1GB
                issues.append(f"High memory usage: {memory_info.rss / 1024 / 1024:.1f}MB")
            if status not in ["running", "sleeping"]:
                issues.append(f"Unusual process status: {status}")
            
            if issues:
                return HealthCheckResult(
                    component=self.name,
                    status="warning",
                    message=f"Process issues detected: {'; '.join(issues)}",
                    timestamp=datetime.now(),
                    details=details
                )
            else:
                return HealthCheckResult(
                    component=self.name,
                    status="healthy",
                    message="Process is running normally",
                    timestamp=datetime.now(),
                    details=details
                )
                
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status="critical",
                message=f"Process check failed: {str(e)}",
                timestamp=datetime.now(),
                details={"error": str(e)}
            )


class SystemHealthChecker:
    """Main system health checker."""
    
    def __init__(self):
        """Initialize system health checker."""
        self.checks: List[HealthCheck] = [
            DatabaseHealthCheck(),
            DiskSpaceHealthCheck(),
            MemoryHealthCheck(),
            ProcessHealthCheck(),
        ]
        self.results: Dict[str, HealthCheckResult] = {}
        self.last_check_time: Optional[datetime] = None
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks.
        
        Returns:
            Dictionary of check results
        """
        logger.info("Running system health checks...")
        
        # Run checks concurrently
        tasks = [check.check() for check in self.checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        self.results = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error result
                check_name = self.checks[i].name
                self.results[check_name] = HealthCheckResult(
                    component=check_name,
                    status="critical",
                    message=f"Check execution failed: {str(result)}",
                    timestamp=datetime.now(),
                    details={"error": str(result)}
                )
            else:
                self.results[result.component] = result
        
        self.last_check_time = datetime.now()
        
        # Log results
        healthy_count = sum(1 for r in self.results.values() if r.is_healthy)
        total_count = len(self.results)
        
        logger.info(f"Health checks completed: {healthy_count}/{total_count} healthy")
        
        return self.results
    
    async def run_check(self, component: str) -> Optional[HealthCheckResult]:
        """Run a specific health check.
        
        Args:
            component: Component name to check
            
        Returns:
            Health check result or None if not found
        """
        for check in self.checks:
            if check.name == component:
                result = await check.check()
                self.results[component] = result
                return result
        
        return None
    
    def get_overall_status(self) -> str:
        """Get overall system status.
        
        Returns:
            Overall status: "healthy", "warning", "critical"
        """
        if not self.results:
            return "unknown"
        
        statuses = [result.status for result in self.results.values()]
        
        if "critical" in statuses:
            return "critical"
        elif "warning" in statuses:
            return "warning"
        else:
            return "healthy"
    
    def get_unhealthy_components(self) -> List[str]:
        """Get list of unhealthy components.
        
        Returns:
            List of component names that are not healthy
        """
        return [
            name for name, result in self.results.items()
            if not result.is_healthy
        ]
    
    def get_critical_components(self) -> List[str]:
        """Get list of critical components.
        
        Returns:
            List of component names that are in critical state
        """
        return [
            name for name, result in self.results.items()
            if result.is_critical
        ]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get health check summary.
        
        Returns:
            Summary dictionary
        """
        if not self.results:
            return {
                "overall_status": "unknown",
                "total_checks": 0,
                "healthy_checks": 0,
                "warning_checks": 0,
                "critical_checks": 0,
                "last_check_time": None,
                "components": {}
            }
        
        healthy_count = sum(1 for r in self.results.values() if r.is_healthy)
        warning_count = sum(1 for r in self.results.values() if r.status == "warning")
        critical_count = sum(1 for r in self.results.values() if r.is_critical)
        
        return {
            "overall_status": self.get_overall_status(),
            "total_checks": len(self.results),
            "healthy_checks": healthy_count,
            "warning_checks": warning_count,
            "critical_checks": critical_count,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "components": {
                name: {
                    "status": result.status,
                    "message": result.message,
                    "response_time_ms": result.response_time_ms,
                    "timestamp": result.timestamp.isoformat()
                }
                for name, result in self.results.items()
            }
        }

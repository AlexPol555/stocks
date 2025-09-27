from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .models import ProcessingMetrics
from .repository import NewsPipelineRepository

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring."""
    timestamp: str
    batch_id: str
    total_news: int
    processed_news: int
    candidates_generated: int
    auto_applied: int
    skipped_duplicates: int
    errors: int
    duration_seconds: float
    chunk_count: int
    avg_time_per_news: float
    candidates_per_news: float
    auto_apply_rate: float
    error_rate: float
    throughput_news_per_second: float

    @classmethod
    def from_processing_metrics(cls, metrics: ProcessingMetrics, batch_id: str) -> "PerformanceMetrics":
        """Create performance metrics from processing metrics."""
        timestamp = datetime.utcnow().isoformat()
        
        # Calculate derived metrics
        avg_time_per_news = metrics.duration_seconds / max(metrics.processed_news, 1)
        candidates_per_news = metrics.candidates_generated / max(metrics.processed_news, 1)
        auto_apply_rate = metrics.auto_applied / max(metrics.candidates_generated, 1)
        error_rate = metrics.errors / max(metrics.total_news, 1)
        throughput_news_per_second = metrics.processed_news / max(metrics.duration_seconds, 0.001)
        
        return cls(
            timestamp=timestamp,
            batch_id=batch_id,
            total_news=metrics.total_news,
            processed_news=metrics.processed_news,
            candidates_generated=metrics.candidates_generated,
            auto_applied=metrics.auto_applied,
            skipped_duplicates=metrics.skipped_duplicates,
            errors=metrics.errors,
            duration_seconds=metrics.duration_seconds,
            chunk_count=metrics.chunk_count,
            avg_time_per_news=avg_time_per_news,
            candidates_per_news=candidates_per_news,
            auto_apply_rate=auto_apply_rate,
            error_rate=error_rate,
            throughput_news_per_second=throughput_news_per_second,
        )


@dataclass
class SystemHealth:
    """System health metrics."""
    timestamp: str
    database_connected: bool
    total_news: int
    processed_news: int
    pending_candidates: int
    confirmed_candidates: int
    rejected_candidates: int
    recent_errors: int
    avg_processing_time: float
    last_successful_run: Optional[str]
    system_load: float
    memory_usage: float
    disk_usage: float

    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return (
            self.database_connected and
            self.recent_errors < 10 and
            self.system_load < 0.8 and
            self.memory_usage < 0.9 and
            self.disk_usage < 0.9
        )


class MetricsCollector:
    """Collects and stores performance metrics."""
    
    def __init__(self, repository: NewsPipelineRepository, metrics_dir: Optional[Path] = None):
        self.repository = repository
        self.metrics_dir = metrics_dir or Path("metrics")
        self.metrics_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.MetricsCollector")
        
    def collect_processing_metrics(self, metrics: ProcessingMetrics, batch_id: str) -> PerformanceMetrics:
        """Collect and store processing metrics."""
        perf_metrics = PerformanceMetrics.from_processing_metrics(metrics, batch_id)
        
        # Store in file
        self._store_metrics(perf_metrics)
        
        # Log metrics
        self.logger.info(
            "Processing metrics collected: batch_id=%s, news=%d, candidates=%d, "
            "auto_applied=%d, errors=%d, duration=%.2fs, throughput=%.2f news/s",
            batch_id,
            perf_metrics.processed_news,
            perf_metrics.candidates_generated,
            perf_metrics.auto_applied,
            perf_metrics.errors,
            perf_metrics.duration_seconds,
            perf_metrics.throughput_news_per_second,
        )
        
        return perf_metrics
    
    def collect_system_health(self) -> SystemHealth:
        """Collect system health metrics."""
        try:
            with self.repository.connect() as conn:
                # Database metrics
                total_news = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
                processed_news = conn.execute("SELECT COUNT(*) FROM articles WHERE processed = 1").fetchone()[0]
                pending_candidates = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = 0").fetchone()[0]
                confirmed_candidates = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = 1").fetchone()[0]
                rejected_candidates = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = -1").fetchone()[0]
                
                # Recent errors (last 24 hours)
                recent_errors = conn.execute("""
                    SELECT COUNT(*) FROM processing_runs 
                    WHERE status = 'failed' AND started_at > datetime('now', '-1 day')
                """).fetchone()[0]
                
                # Average processing time (last 7 days)
                avg_processing_time = conn.execute("""
                    SELECT AVG(CAST(json_extract(metrics, '$.duration_seconds') AS REAL))
                    FROM processing_runs 
                    WHERE status = 'completed' AND started_at > datetime('now', '-7 days')
                """).fetchone()[0] or 0.0
                
                # Last successful run
                last_successful_run = conn.execute("""
                    SELECT started_at FROM processing_runs 
                    WHERE status = 'completed' 
                    ORDER BY started_at DESC LIMIT 1
                """).fetchone()
                last_successful_run = last_successful_run[0] if last_successful_run else None
                
        except Exception as exc:
            self.logger.error("Failed to collect database metrics: %s", exc)
            return SystemHealth(
                timestamp=datetime.utcnow().isoformat(),
                database_connected=False,
                total_news=0,
                processed_news=0,
                pending_candidates=0,
                confirmed_candidates=0,
                rejected_candidates=0,
                recent_errors=1,
                avg_processing_time=0.0,
                last_successful_run=None,
                system_load=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
            )
        
        # System metrics
        system_load = self._get_system_load()
        memory_usage = self._get_memory_usage()
        disk_usage = self._get_disk_usage()
        
        health = SystemHealth(
            timestamp=datetime.utcnow().isoformat(),
            database_connected=True,
            total_news=total_news,
            processed_news=processed_news,
            pending_candidates=pending_candidates,
            confirmed_candidates=confirmed_candidates,
            rejected_candidates=rejected_candidates,
            recent_errors=recent_errors,
            avg_processing_time=avg_processing_time,
            last_successful_run=last_successful_run,
            system_load=system_load,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
        )
        
        # Store health metrics
        self._store_health_metrics(health)
        
        return health
    
    def get_performance_history(self, days: int = 7) -> List[PerformanceMetrics]:
        """Get performance metrics history."""
        metrics_file = self.metrics_dir / "performance_metrics.jsonl"
        if not metrics_file.exists():
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        metrics = []
        
        try:
            with metrics_file.open("r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        metric_time = datetime.fromisoformat(data["timestamp"])
                        if metric_time >= cutoff_time:
                            metrics.append(PerformanceMetrics(**data))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception as exc:
            self.logger.error("Failed to read performance metrics: %s", exc)
        
        return sorted(metrics, key=lambda x: x.timestamp)
    
    def get_health_history(self, days: int = 1) -> List[SystemHealth]:
        """Get system health history."""
        health_file = self.metrics_dir / "system_health.jsonl"
        if not health_file.exists():
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        health_metrics = []
        
        try:
            with health_file.open("r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        metric_time = datetime.fromisoformat(data["timestamp"])
                        if metric_time >= cutoff_time:
                            health_metrics.append(SystemHealth(**data))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception as exc:
            self.logger.error("Failed to read health metrics: %s", exc)
        
        return sorted(health_metrics, key=lambda x: x.timestamp)
    
    def _store_metrics(self, metrics: PerformanceMetrics) -> None:
        """Store performance metrics to file."""
        metrics_file = self.metrics_dir / "performance_metrics.jsonl"
        try:
            with metrics_file.open("a") as f:
                f.write(json.dumps(asdict(metrics)) + "\n")
        except Exception as exc:
            self.logger.error("Failed to store performance metrics: %s", exc)
    
    def _store_health_metrics(self, health: SystemHealth) -> None:
        """Store system health metrics to file."""
        health_file = self.metrics_dir / "system_health.jsonl"
        try:
            with health_file.open("a") as f:
                f.write(json.dumps(asdict(health)) + "\n")
        except Exception as exc:
            self.logger.error("Failed to store health metrics: %s", exc)
    
    def _get_system_load(self) -> float:
        """Get system load average."""
        try:
            import psutil
            return psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get memory usage percentage."""
        try:
            import psutil
            return psutil.virtual_memory().percent / 100.0
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
    def _get_disk_usage(self) -> float:
        """Get disk usage percentage."""
        try:
            import psutil
            return psutil.disk_usage('/').percent / 100.0
        except ImportError:
            return 0.0
        except Exception:
            return 0.0


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(f"{__name__}.AlertManager")
        self._alert_thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "system_load": 0.8,  # 80% system load
            "memory_usage": 0.9,  # 90% memory usage
            "disk_usage": 0.9,  # 90% disk usage
            "processing_time": 300.0,  # 5 minutes per batch
            "no_successful_runs": 24 * 3600,  # 24 hours without successful runs
        }
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        
        try:
            # Get recent health metrics
            health_history = self.metrics_collector.get_health_history(days=1)
            if not health_history:
                return alerts
            
            latest_health = health_history[-1]
            
            # Check error rate
            if latest_health.recent_errors > 5:
                alerts.append({
                    "type": "high_error_rate",
                    "severity": "warning",
                    "message": f"High error rate: {latest_health.recent_errors} errors in last 24 hours",
                    "timestamp": latest_health.timestamp,
                })
            
            # Check system resources
            if latest_health.system_load > self._alert_thresholds["system_load"]:
                alerts.append({
                    "type": "high_system_load",
                    "severity": "warning",
                    "message": f"High system load: {latest_health.system_load:.2f}",
                    "timestamp": latest_health.timestamp,
                })
            
            if latest_health.memory_usage > self._alert_thresholds["memory_usage"]:
                alerts.append({
                    "type": "high_memory_usage",
                    "severity": "critical",
                    "message": f"High memory usage: {latest_health.memory_usage:.2f}",
                    "timestamp": latest_health.timestamp,
                })
            
            if latest_health.disk_usage > self._alert_thresholds["disk_usage"]:
                alerts.append({
                    "type": "high_disk_usage",
                    "severity": "critical",
                    "message": f"High disk usage: {latest_health.disk_usage:.2f}",
                    "timestamp": latest_health.timestamp,
                })
            
            # Check for no successful runs
            if latest_health.last_successful_run:
                last_run_time = datetime.fromisoformat(latest_health.last_successful_run)
                time_since_last = (datetime.utcnow() - last_run_time).total_seconds()
                if time_since_last > self._alert_thresholds["no_successful_runs"]:
                    alerts.append({
                        "type": "no_recent_successful_runs",
                        "severity": "warning",
                        "message": f"No successful runs in {time_since_last/3600:.1f} hours",
                        "timestamp": latest_health.timestamp,
                    })
            
            # Check performance metrics
            perf_history = self.metrics_collector.get_performance_history(days=1)
            if perf_history:
                latest_perf = perf_history[-1]
                if latest_perf.duration_seconds > self._alert_thresholds["processing_time"]:
                    alerts.append({
                        "type": "slow_processing",
                        "severity": "warning",
                        "message": f"Slow processing: {latest_perf.duration_seconds:.2f}s for {latest_perf.processed_news} news items",
                        "timestamp": latest_perf.timestamp,
                    })
                
                if latest_perf.error_rate > self._alert_thresholds["error_rate"]:
                    alerts.append({
                        "type": "high_processing_error_rate",
                        "severity": "warning",
                        "message": f"High processing error rate: {latest_perf.error_rate:.2f}",
                        "timestamp": latest_perf.timestamp,
                    })
        
        except Exception as exc:
            self.logger.error("Failed to check alerts: %s", exc)
            alerts.append({
                "type": "alert_check_failed",
                "severity": "critical",
                "message": f"Failed to check alerts: {exc}",
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        return alerts
    
    def send_alert(self, alert: Dict[str, Any]) -> None:
        """Send an alert notification."""
        self.logger.warning(
            "ALERT [%s]: %s - %s",
            alert["severity"].upper(),
            alert["type"],
            alert["message"],
        )
        
        # Here you could integrate with external alerting systems
        # like email, Slack, PagerDuty, etc.
        
        # For now, just log the alert
        if alert["severity"] == "critical":
            self.logger.critical("CRITICAL ALERT: %s", alert["message"])
        elif alert["severity"] == "warning":
            self.logger.warning("WARNING: %s", alert["message"])


__all__ = [
    "PerformanceMetrics",
    "SystemHealth", 
    "MetricsCollector",
    "AlertManager",
]

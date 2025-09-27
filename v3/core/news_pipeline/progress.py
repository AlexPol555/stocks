from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProgressEvent:
    stage: str
    current: int
    total: int
    message: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    @property
    def progress_percent(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100.0

    @property
    def is_complete(self) -> bool:
        return self.current >= self.total


class ProgressReporter:
    """Thread-safe progress reporter for batch processing."""
    
    def __init__(self, refresh_interval: float = 0.5):
        self.refresh_interval = refresh_interval
        self._lock = threading.Lock()
        self._last_report_time = 0.0
        self._last_event: Optional[ProgressEvent] = None
        self._callbacks: list = []

    def add_callback(self, callback) -> None:
        """Add a callback function to be called on progress updates."""
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback) -> None:
        """Remove a callback function."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def report(self, event: ProgressEvent) -> None:
        """Report a progress event."""
        with self._lock:
            current_time = time.time()
            
            # Throttle reports based on refresh interval
            if current_time - self._last_report_time < self.refresh_interval:
                return
            
            self._last_report_time = current_time
            self._last_event = event
            
            # Call all callbacks
            for callback in self._callbacks:
                try:
                    callback(event)
                except Exception as exc:
                    logger.warning("Progress callback failed: %s", exc)

    def get_last_event(self) -> Optional[ProgressEvent]:
        """Get the last reported progress event."""
        with self._lock:
            return self._last_event

    def clear(self) -> None:
        """Clear the last event and reset state."""
        with self._lock:
            self._last_event = None
            self._last_report_time = 0.0


class StreamlitProgressReporter(ProgressReporter):
    """Progress reporter that integrates with Streamlit."""
    
    def __init__(self, progress_bar, status_text, refresh_interval: float = 0.5):
        super().__init__(refresh_interval)
        self.progress_bar = progress_bar
        self.status_text = status_text
        self.add_callback(self._update_streamlit)

    def _update_streamlit(self, event: ProgressEvent) -> None:
        """Update Streamlit UI elements."""
        try:
            if self.progress_bar:
                self.progress_bar.progress(event.progress_percent / 100.0)
            
            if self.status_text:
                self.status_text.text(event.message)
                
        except Exception as exc:
            logger.warning("Failed to update Streamlit UI: %s", exc)


class LoggingProgressReporter(ProgressReporter):
    """Progress reporter that logs progress to the logger."""
    
    def __init__(self, logger_name: str = __name__, refresh_interval: float = 5.0):
        super().__init__(refresh_interval)
        self.logger = logging.getLogger(logger_name)
        self.add_callback(self._log_progress)

    def _log_progress(self, event: ProgressEvent) -> None:
        """Log progress to the logger."""
        try:
            self.logger.info(
                "Progress: %s - %d/%d (%.1f%%) - %s",
                event.stage,
                event.current,
                event.total,
                event.progress_percent,
                event.message,
            )
        except Exception as exc:
            logger.warning("Failed to log progress: %s", exc)


__all__ = ["ProgressEvent", "ProgressReporter", "StreamlitProgressReporter", "LoggingProgressReporter"]
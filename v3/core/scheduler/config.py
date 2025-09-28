"""Configuration for the task scheduler.

This module provides configuration settings and constants
for the task scheduler system.
"""

from datetime import timedelta
from typing import Dict, Any

# Task intervals
TASK_INTERVALS = {
    "update_market_data": timedelta(hours=1),
    "fetch_news": timedelta(minutes=30),
    "process_news_pipeline": timedelta(hours=2),
    "calculate_indicators": timedelta(hours=1),
    "generate_signals": timedelta(hours=1),
    "send_notifications": timedelta(minutes=15),
}

# Task priorities (higher number = higher priority)
TASK_PRIORITIES = {
    "update_market_data": 10,
    "send_notifications": 9,
    "calculate_indicators": 8,
    "generate_signals": 7,
    "fetch_news": 5,
    "process_news_pipeline": 3,
}

# Task dependencies
TASK_DEPENDENCIES = {
    "calculate_indicators": ["update_market_data"],
    "generate_signals": ["calculate_indicators"],
    "process_news_pipeline": ["fetch_news"],
}

# Maximum errors before disabling task
TASK_MAX_ERRORS = {
    "update_market_data": 3,
    "fetch_news": 5,
    "process_news_pipeline": 3,
    "calculate_indicators": 3,
    "generate_signals": 3,
    "send_notifications": 5,
}

# Market hours (in MSK timezone)
MARKET_HOURS = {
    "moex": {
        "start": "10:00",
        "end": "18:45",
        "timezone": "Europe/Moscow",
        "weekdays": [0, 1, 2, 3, 4]  # Monday to Friday
    },
    "nyse": {
        "start": "09:30",
        "end": "16:00",
        "timezone": "America/New_York",
        "weekdays": [0, 1, 2, 3, 4]  # Monday to Friday
    },
    "nasdaq": {
        "start": "09:30",
        "end": "16:00",
        "timezone": "America/New_York",
        "weekdays": [0, 1, 2, 3, 4]  # Monday to Friday
    }
}

# Retry configuration
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 60,  # seconds
    "max_delay": 3600,  # seconds
    "exponential_base": 2,
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/scheduler.log",
    "max_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
}

# Database configuration
DATABASE_CONFIG = {
    "connection_timeout": 30,
    "query_timeout": 60,
    "max_connections": 10,
}

# Notification configuration
NOTIFICATION_CONFIG = {
    "enabled": True,
    "channels": ["email", "telegram", "webhook"],
    "retry_attempts": 3,
    "retry_delay": 300,  # seconds
}

# Performance configuration
PERFORMANCE_CONFIG = {
    "max_concurrent_tasks": 5,
    "task_timeout": 300,  # seconds
    "memory_limit": 512 * 1024 * 1024,  # 512MB
    "cpu_limit": 80,  # percentage
}

# Security configuration
SECURITY_CONFIG = {
    "api_key_required": True,
    "rate_limit": 100,  # requests per minute
    "ip_whitelist": [],
    "encryption_enabled": True,
}

# Monitoring configuration
MONITORING_CONFIG = {
    "enabled": True,
    "metrics_interval": 60,  # seconds
    "health_check_interval": 30,  # seconds
    "alert_thresholds": {
        "error_rate": 0.1,  # 10%
        "response_time": 30,  # seconds
        "memory_usage": 0.8,  # 80%
        "cpu_usage": 0.8,  # 80%
    }
}

# Default configuration
DEFAULT_CONFIG = {
    "intervals": TASK_INTERVALS,
    "priorities": TASK_PRIORITIES,
    "dependencies": TASK_DEPENDENCIES,
    "max_errors": TASK_MAX_ERRORS,
    "market_hours": MARKET_HOURS,
    "retry": RETRY_CONFIG,
    "logging": LOGGING_CONFIG,
    "database": DATABASE_CONFIG,
    "notifications": NOTIFICATION_CONFIG,
    "performance": PERFORMANCE_CONFIG,
    "security": SECURITY_CONFIG,
    "monitoring": MONITORING_CONFIG,
}


def get_config() -> Dict[str, Any]:
    """Get the complete configuration.
    
    Returns:
        Dictionary with all configuration settings
    """
    return DEFAULT_CONFIG.copy()


def get_task_config(task_name: str) -> Dict[str, Any]:
    """Get configuration for a specific task.
    
    Args:
        task_name: Name of the task
        
    Returns:
        Dictionary with task-specific configuration
    """
    return {
        "interval": TASK_INTERVALS.get(task_name),
        "priority": TASK_PRIORITIES.get(task_name, 0),
        "dependencies": TASK_DEPENDENCIES.get(task_name, []),
        "max_errors": TASK_MAX_ERRORS.get(task_name, 3),
    }


def get_market_config(market: str) -> Dict[str, Any]:
    """Get configuration for a specific market.
    
    Args:
        market: Market name (moex, nyse, nasdaq)
        
    Returns:
        Dictionary with market-specific configuration
    """
    return MARKET_HOURS.get(market.lower(), {})


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration settings.
    
    Args:
        config: Configuration to validate
        
    Returns:
        True if configuration is valid
    """
    required_keys = [
        "intervals", "priorities", "dependencies", 
        "max_errors", "market_hours"
    ]
    
    for key in required_keys:
        if key not in config:
            return False
            
    # Validate task intervals
    for task_name, interval in config["intervals"].items():
        if not isinstance(interval, timedelta):
            return False
            
    # Validate task priorities
    for task_name, priority in config["priorities"].items():
        if not isinstance(priority, int) or priority < 0:
            return False
            
    # Validate task dependencies
    for task_name, dependencies in config["dependencies"].items():
        if not isinstance(dependencies, list):
            return False
            
    # Validate market hours
    for market, hours in config["market_hours"].items():
        required_hour_keys = ["start", "end", "timezone", "weekdays"]
        for key in required_hour_keys:
            if key not in hours:
                return False
                
    return True

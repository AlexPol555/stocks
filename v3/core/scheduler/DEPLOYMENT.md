# Task Scheduler Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying and configuring the Task Scheduler module in your trading system.

## Prerequisites

- Python 3.8 or higher
- SQLite database
- Required Python packages (see requirements.txt)
- Access to trading data sources
- News feed access (optional)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Database Setup

Run the database migrations to create the necessary tables:

```bash
python -m core.scheduler.migrations your_database.db migrate
```

### 3. Verify Installation

Check that the scheduler module can be imported:

```python
from core.scheduler import TaskScheduler, TradingCalendar
from core.scheduler.integration import SchedulerIntegration
```

## Configuration

### 1. Basic Configuration

Create a configuration file or use environment variables:

```python
# config/scheduler_config.py
SCHEDULER_CONFIG = {
    "database_path": "your_database.db",
    "log_level": "INFO",
    "max_concurrent_tasks": 5,
    "task_timeout_seconds": 300,
    "retry_delay_seconds": 60,
    "max_retries": 3,
    "enable_notifications": True,
}
```

### 2. Task Configuration

Configure individual tasks:

```python
# config/tasks.py
TASK_CONFIGS = {
    "update_market_data": {
        "interval": timedelta(hours=1),
        "priority": 10,
        "dependencies": [],
        "max_errors": 3,
        "enabled": True,
    },
    "fetch_news": {
        "interval": timedelta(minutes=30),
        "priority": 5,
        "dependencies": [],
        "max_errors": 5,
        "enabled": True,
    },
    # ... more tasks
}
```

### 3. Market Configuration

Configure trading sessions:

```python
# config/markets.py
MARKET_CONFIG = {
    "moex": {
        "start": "10:00",
        "end": "18:45",
        "timezone": "Europe/Moscow",
        "weekdays": [0, 1, 2, 3, 4],  # Monday to Friday
    },
    "nyse": {
        "start": "09:30",
        "end": "16:00",
        "timezone": "America/New_York",
        "weekdays": [0, 1, 2, 3, 4],  # Monday to Friday
    },
}
```

## Deployment Options

### Option 1: Standalone Service

Deploy as a standalone service using systemd (Linux) or Windows Service:

#### Linux (systemd)

1. Create service file:

```ini
# /etc/systemd/system/scheduler.service
[Unit]
Description=Task Scheduler Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/your/project
ExecStart=/usr/bin/python -m core.scheduler.service
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable and start service:

```bash
sudo systemctl enable scheduler.service
sudo systemctl start scheduler.service
```

#### Windows Service

1. Install as Windows service using `pywin32`:

```python
# scheduler_service.py
import win32serviceutil
import win32service
import win32event
from core.scheduler.service import SchedulerService

class SchedulerWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "TaskScheduler"
    _svc_display_name_ = "Task Scheduler Service"
    _svc_description_ = "Automated task scheduler for trading system"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.scheduler_service = SchedulerService()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        self.scheduler_service.start()
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(SchedulerWindowsService)
```

2. Install service:

```bash
python scheduler_service.py install
python scheduler_service.py start
```

### Option 2: Docker Container

Deploy using Docker:

#### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "core.scheduler.service"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  scheduler:
    build: .
    container_name: task-scheduler
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - DATABASE_PATH=/app/data/scheduler.db
      - LOG_LEVEL=INFO
    restart: unless-stopped
    depends_on:
      - database

  database:
    image: sqlite:latest
    container_name: scheduler-db
    volumes:
      - ./data:/data
    restart: unless-stopped
```

#### Deploy with Docker

```bash
docker-compose up -d
```

### Option 3: Integration with Existing Application

Integrate with your existing Streamlit application:

```python
# app.py
import streamlit as st
from core.scheduler import TaskScheduler, TradingCalendar
from core.scheduler.integration import SchedulerIntegration

# Initialize scheduler
@st.cache_resource
def get_scheduler():
    trading_calendar = TradingCalendar()
    scheduler = TaskScheduler(trading_calendar)
    integration = SchedulerIntegration(scheduler, trading_calendar)
    
    # Setup tasks
    integration.setup_all_tasks(
        data_loader_func=your_data_loader,
        news_fetch_func=your_news_fetcher,
        news_process_func=your_news_processor,
        indicators_func=your_indicators_calculator,
        signals_func=your_signals_generator,
        notification_func=your_notification_sender
    )
    
    return integration

# Use scheduler in your app
scheduler = get_scheduler()

# Start scheduler when app starts
if not scheduler.scheduler.running:
    scheduler.start_scheduler()

# Add scheduler status to your UI
st.sidebar.title("Scheduler Status")
status = scheduler.get_task_status()
st.sidebar.write(f"Running: {status['running']}")
st.sidebar.write(f"Total tasks: {status['total_tasks']}")
st.sidebar.write(f"Enabled tasks: {status['enabled_tasks']}")
```

## Monitoring and Maintenance

### 1. Health Checks

Set up health check endpoints:

```python
# health_check.py
from flask import Flask, jsonify
from core.scheduler import TaskScheduler

app = Flask(__name__)
scheduler = TaskScheduler()

@app.route('/health')
def health():
    status = scheduler.get_status()
    return jsonify({
        'status': 'healthy' if status['failed_tasks'] == 0 else 'unhealthy',
        'running': status['running'],
        'total_tasks': status['total_tasks'],
        'failed_tasks': status['failed_tasks']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### 2. Logging

Configure logging for production:

```python
# logging_config.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Create logger
    logger = logging.getLogger('scheduler')
    logger.setLevel(logging.INFO)
    
    # Create file handler
    file_handler = RotatingFileHandler(
        'logs/scheduler.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger
```

### 3. Metrics Collection

Collect and export metrics:

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from core.scheduler import TaskScheduler

# Define metrics
task_executions = Counter('scheduler_task_executions_total', 'Total task executions', ['task_name', 'status'])
task_duration = Histogram('scheduler_task_duration_seconds', 'Task execution duration', ['task_name'])
active_tasks = Gauge('scheduler_active_tasks', 'Number of active tasks')

def collect_metrics(scheduler: TaskScheduler):
    """Collect metrics from scheduler."""
    status = scheduler.get_status()
    
    # Update active tasks gauge
    active_tasks.set(status['running_tasks'])
    
    # Update task execution counters
    for task_name, task_info in status['tasks'].items():
        task_executions.labels(
            task_name=task_name,
            status=task_info['status']
        ).inc()

# Start metrics server
start_http_server(8000)
```

### 4. Backup and Recovery

Set up database backups:

```bash
#!/bin/bash
# backup_scheduler.sh

BACKUP_DIR="/backups/scheduler"
DB_PATH="/path/to/scheduler.db"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp $DB_PATH $BACKUP_DIR/scheduler_$DATE.db

# Keep only last 30 days of backups
find $BACKUP_DIR -name "scheduler_*.db" -mtime +30 -delete

echo "Backup completed: scheduler_$DATE.db"
```

### 5. Alerting

Set up alerting for critical events:

```python
# alerts.py
import smtplib
from email.mime.text import MIMEText
from core.scheduler import TaskScheduler

class SchedulerAlerts:
    def __init__(self, smtp_server, smtp_port, username, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        
    def send_alert(self, subject, message, recipients):
        """Send alert email."""
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = self.username
        msg['To'] = ', '.join(recipients)
        
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            
    def check_scheduler_health(self, scheduler: TaskScheduler):
        """Check scheduler health and send alerts if needed."""
        status = scheduler.get_status()
        
        if status['failed_tasks'] > 0:
            self.send_alert(
                "Scheduler Alert: Failed Tasks",
                f"Scheduler has {status['failed_tasks']} failed tasks",
                ["admin@yourcompany.com"]
            )
            
        if not status['running']:
            self.send_alert(
                "Scheduler Alert: Not Running",
                "Scheduler is not running",
                ["admin@yourcompany.com"]
            )
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check database file permissions
   - Verify database path is correct
   - Ensure database is not locked by another process

2. **Task Execution Failures**
   - Check task function implementations
   - Verify dependencies are available
   - Review error logs for specific error messages

3. **Scheduler Not Starting**
   - Check Python version compatibility
   - Verify all dependencies are installed
   - Review configuration for errors

4. **Performance Issues**
   - Monitor task execution times
   - Check system resources (CPU, memory)
   - Consider adjusting task intervals

### Debug Mode

Enable debug mode for troubleshooting:

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run scheduler in debug mode
scheduler = TaskScheduler()
scheduler.debug = True
await scheduler.start()
```

### Log Analysis

Analyze logs for issues:

```bash
# View recent logs
tail -f logs/scheduler.log

# Search for errors
grep "ERROR" logs/scheduler.log

# Search for specific task
grep "task_name" logs/scheduler.log
```

## Security Considerations

1. **Database Security**
   - Use proper file permissions
   - Consider database encryption
   - Regular security updates

2. **API Security**
   - Use authentication for API endpoints
   - Implement rate limiting
   - Validate input parameters

3. **Network Security**
   - Use HTTPS for external communications
   - Implement firewall rules
   - Monitor network traffic

## Performance Optimization

1. **Task Optimization**
   - Optimize task functions
   - Use async/await where possible
   - Implement proper error handling

2. **Database Optimization**
   - Create appropriate indexes
   - Regular database maintenance
   - Consider connection pooling

3. **System Optimization**
   - Monitor system resources
   - Adjust task intervals based on load
   - Use appropriate hardware

## Maintenance

### Regular Tasks

1. **Daily**
   - Check scheduler status
   - Review error logs
   - Monitor task execution

2. **Weekly**
   - Review task performance
   - Update task configurations
   - Clean up old logs

3. **Monthly**
   - Database maintenance
   - Security updates
   - Performance review

### Updates

1. **Scheduler Updates**
   - Test updates in staging environment
   - Backup database before updates
   - Monitor after deployment

2. **Configuration Updates**
   - Validate configuration changes
   - Test with small changes first
   - Document changes

## Support

For support and questions:

1. Check the documentation
2. Review error logs
3. Search existing issues
4. Create new issue with details

## Conclusion

This deployment guide provides comprehensive instructions for deploying and maintaining the Task Scheduler module. Follow the steps carefully and adapt them to your specific environment and requirements.

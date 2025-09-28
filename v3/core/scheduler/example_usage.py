"""Example usage of the task scheduler in the main application.

This module demonstrates how to integrate the task scheduler
into the main Streamlit application.
"""

import streamlit as st
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from .scheduler import TaskScheduler
from .trading_calendar import TradingCalendar, Market
from .integration import SchedulerIntegration
from .real_integration import RealSchedulerIntegration

logger = logging.getLogger(__name__)


def setup_scheduler_in_app():
    """Setup scheduler in the main application."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = RealSchedulerIntegration()
        
    return st.session_state.scheduler


def render_scheduler_sidebar():
    """Render scheduler status in sidebar."""
    scheduler = setup_scheduler_in_app()
    
    with st.sidebar:
        st.title("📅 Scheduler")
        
        # Get status
        status = scheduler.get_status()
        
        if status:
            # Overall status
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total", status.get('total_tasks', 0))
            with col2:
                st.metric("Enabled", status.get('enabled_tasks', 0))
                
            # Running status
            if status.get('running', False):
                st.success("🟢 Running")
            else:
                st.error("🔴 Stopped")
                
            # Quick controls
            if st.button("Start"):
                scheduler.start_scheduler()
                st.rerun()
                
            if st.button("Stop"):
                scheduler.stop_scheduler()
                st.rerun()
        else:
            st.warning("Scheduler not available")


def render_scheduler_page():
    """Render dedicated scheduler page."""
    st.title("📅 Task Scheduler")
    
    scheduler = setup_scheduler_in_app()
    
    # Status overview
    st.header("Status Overview")
    
    status = scheduler.get_status()
    if status:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tasks", status.get('total_tasks', 0))
        with col2:
            st.metric("Enabled Tasks", status.get('enabled_tasks', 0))
        with col3:
            st.metric("Running Tasks", status.get('running_tasks', 0))
        with col4:
            st.metric("Failed Tasks", status.get('failed_tasks', 0))
            
        # Health status
        failed_tasks = status.get('failed_tasks', 0)
        if failed_tasks > 0:
            st.error(f"⚠️ {failed_tasks} tasks have failed")
        else:
            st.success("✅ All tasks are healthy")
            
    else:
        st.error("Unable to get scheduler status")
        return
        
    # Task management
    st.header("Task Management")
    
    # Task list
    tasks = status.get('tasks', {})
    if tasks:
        for task_name, task_info in tasks.items():
            with st.expander(f"Task: {task_name}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Status:** {task_info.get('status', 'Unknown')}")
                    st.write(f"**Enabled:** {task_info.get('enabled', False)}")
                    st.write(f"**Error Count:** {task_info.get('error_count', 0)}")
                    
                    last_run = task_info.get('last_run')
                    if last_run:
                        st.write(f"**Last Run:** {last_run}")
                    else:
                        st.write("**Last Run:** Never")
                        
                    next_run = task_info.get('next_run')
                    if next_run:
                        st.write(f"**Next Run:** {next_run}")
                    else:
                        st.write("**Next Run:** Not scheduled")
                        
                with col2:
                    if task_info.get('enabled', False):
                        if st.button("Disable", key=f"disable_{task_name}"):
                            scheduler.disable_task(task_name)
                            st.rerun()
                    else:
                        if st.button("Enable", key=f"enable_{task_name}"):
                            scheduler.enable_task(task_name)
                            st.rerun()
                            
    else:
        st.warning("No tasks configured")
        
    # Scheduler controls
    st.header("Scheduler Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Start Scheduler", type="primary"):
            scheduler.start_scheduler()
            st.rerun()
            
    with col2:
        if st.button("Stop Scheduler"):
            scheduler.stop_scheduler()
            st.rerun()
            
    with col3:
        if st.button("Refresh Status"):
            st.rerun()
            
    # Next scheduled tasks
    st.header("Next Scheduled Tasks")
    
    next_runs = scheduler.get_next_run_times()
    if next_runs:
        # Sort by next run time
        sorted_tasks = sorted(
            [(name, time) for name, time in next_runs.items() if time],
            key=lambda x: x[1]
        )
        
        if sorted_tasks:
            for task_name, next_run in sorted_tasks[:5]:  # Show next 5 tasks
                st.write(f"**{task_name}:** {next_run}")
        else:
            st.write("No tasks scheduled")
    else:
        st.write("Unable to get next run times")


def render_scheduler_metrics():
    """Render scheduler metrics page."""
    st.title("📊 Scheduler Metrics")
    
    scheduler = setup_scheduler_in_app()
    
    # Get status
    status = scheduler.get_status()
    if not status:
        st.error("Unable to get scheduler status")
        return
        
    # Metrics
    st.header("Performance Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Tasks", status.get('total_tasks', 0))
        st.metric("Enabled Tasks", status.get('enabled_tasks', 0))
        
    with col2:
        st.metric("Running Tasks", status.get('running_tasks', 0))
        st.metric("Failed Tasks", status.get('failed_tasks', 0))
        
    # Task execution chart
    st.header("Task Execution Status")
    
    tasks = status.get('tasks', {})
    if tasks:
        # Count tasks by status
        status_counts = {}
        for task_info in tasks.values():
            task_status = task_info.get('status', 'unknown')
            status_counts[task_status] = status_counts.get(task_status, 0) + 1
            
        # Create chart
        import pandas as pd
        df = pd.DataFrame(list(status_counts.items()), columns=['Status', 'Count'])
        
        st.bar_chart(df.set_index('Status'))
        
    # Error analysis
    st.header("Error Analysis")
    
    error_tasks = [
        (name, info) for name, info in tasks.items()
        if info.get('error_count', 0) > 0
    ]
    
    if error_tasks:
        st.warning(f"{len(error_tasks)} tasks have errors")
        
        for task_name, task_info in error_tasks:
            st.write(f"**{task_name}:** {task_info.get('error_count', 0)} errors")
    else:
        st.success("No tasks with errors")
        
    # Health score
    st.header("Health Score")
    
    total_tasks = status.get('total_tasks', 0)
    failed_tasks = status.get('failed_tasks', 0)
    
    if total_tasks > 0:
        health_score = ((total_tasks - failed_tasks) / total_tasks) * 100
        st.metric("Health Score", f"{health_score:.1f}%")
        
        # Health indicator
        if health_score >= 90:
            st.success("🟢 Excellent")
        elif health_score >= 70:
            st.warning("🟡 Good")
        else:
            st.error("🔴 Poor")
    else:
        st.info("No tasks to evaluate")


def render_scheduler_logs():
    """Render scheduler logs page."""
    st.title("📋 Scheduler Logs")
    
    # Log level filter
    log_level = st.selectbox(
        "Filter by Log Level",
        options=["ALL", "DEBUG", "INFO", "WARNING", "ERROR"],
        key="log_level_filter"
    )
    
    # Number of lines
    num_lines = st.slider(
        "Number of lines to show",
        min_value=10,
        max_value=1000,
        value=100,
        key="num_log_lines"
    )
    
    # View logs button
    if st.button("View Logs", key="view_logs"):
        try:
            with open('scheduler.log', 'r') as f:
                logs = f.readlines()
                
            # Filter by log level
            if log_level != "ALL":
                filtered_logs = [
                    log for log in logs
                    if log_level in log
                ]
            else:
                filtered_logs = logs
                
            # Show last N lines
            recent_logs = filtered_logs[-num_lines:]
            
            # Display logs
            log_text = "".join(recent_logs)
            st.text_area("Logs", log_text, height=400)
            
        except FileNotFoundError:
            st.warning("Log file not found")
        except Exception as e:
            st.error(f"Error reading logs: {e}")
            
    # Download logs button
    if st.button("Download Logs", key="download_logs"):
        try:
            with open('scheduler.log', 'r') as f:
                logs = f.read()
                
            st.download_button(
                label="Download Log File",
                data=logs,
                file_name=f"scheduler_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                mime="text/plain"
            )
            
        except FileNotFoundError:
            st.warning("Log file not found")
        except Exception as e:
            st.error(f"Error downloading logs: {e}")


def render_scheduler_config():
    """Render scheduler configuration page."""
    st.title("⚙️ Scheduler Configuration")
    
    scheduler = setup_scheduler_in_app()
    
    # Configuration sections
    st.header("Task Configuration")
    
    # Task intervals
    st.subheader("Task Intervals")
    
    intervals = {
        "update_market_data": "1 hour",
        "fetch_news": "30 minutes",
        "process_news_pipeline": "2 hours",
        "calculate_indicators": "1 hour",
        "generate_signals": "1 hour",
        "send_notifications": "15 minutes"
    }
    
    for task_name, interval in intervals.items():
        st.write(f"**{task_name}:** {interval}")
        
    # Task priorities
    st.subheader("Task Priorities")
    
    priorities = {
        "update_market_data": 10,
        "send_notifications": 9,
        "calculate_indicators": 8,
        "generate_signals": 7,
        "fetch_news": 5,
        "process_news_pipeline": 3
    }
    
    for task_name, priority in priorities.items():
        st.write(f"**{task_name}:** {priority}")
        
    # Market hours
    st.subheader("Market Hours")
    
    market_hours = {
        "MOEX": "10:00 - 18:45 MSK",
        "NYSE": "09:30 - 16:00 EST",
        "NASDAQ": "09:30 - 16:00 EST"
    }
    
    for market, hours in market_hours.items():
        st.write(f"**{market}:** {hours}")
        
    # Configuration controls
    st.header("Configuration Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export Configuration"):
            st.info("Configuration export not implemented yet")
            
    with col2:
        if st.button("Import Configuration"):
            st.info("Configuration import not implemented yet")
            
    # Advanced settings
    st.header("Advanced Settings")
    
    with st.expander("Advanced Settings", expanded=False):
        st.write("These settings are not yet configurable through the UI")
        
        st.write("**Retry Configuration:**")
        st.write("- Max retries: 3")
        st.write("- Base delay: 60 seconds")
        st.write("- Exponential backoff: enabled")
        
        st.write("**Performance Configuration:**")
        st.write("- Max concurrent tasks: 5")
        st.write("- Task timeout: 300 seconds")
        st.write("- Memory limit: 512MB")


def render_scheduler_help():
    """Render scheduler help page."""
    st.title("❓ Scheduler Help")
    
    # Overview
    st.header("Overview")
    st.write("""
    The Task Scheduler is a powerful tool for automating various tasks in your trading system.
    It can schedule and execute tasks at specific intervals, manage dependencies between tasks,
    and provide intelligent scheduling based on market conditions.
    """)
    
    # Features
    st.header("Features")
    
    features = [
        "Automated task scheduling",
        "Market-aware scheduling",
        "Task dependencies",
        "Error handling and retries",
        "Real-time monitoring",
        "Performance metrics",
        "Logging and debugging"
    ]
    
    for feature in features:
        st.write(f"• {feature}")
        
    # Task Types
    st.header("Task Types")
    
    task_types = {
        "Market Data Updates": "Automatically update market data from various sources",
        "News Fetching": "Fetch and process news from RSS feeds",
        "Technical Analysis": "Calculate technical indicators and generate signals",
        "Notifications": "Send alerts and notifications for important events"
    }
    
    for task_type, description in task_types.items():
        st.write(f"**{task_type}:** {description}")
        
    # Getting Started
    st.header("Getting Started")
    
    st.write("""
    1. **Start the Scheduler:** Click the "Start Scheduler" button to begin automated task execution
    2. **Monitor Tasks:** Use the "Tasks" tab to view and manage individual tasks
    3. **Check Metrics:** Use the "Metrics" tab to monitor performance and health
    4. **View Logs:** Use the "Logs" tab to troubleshoot issues
    """)
    
    # Troubleshooting
    st.header("Troubleshooting")
    
    st.write("""
    **Common Issues:**
    
    - **Tasks not running:** Check if the scheduler is started and tasks are enabled
    - **Task failures:** Review error logs and check task dependencies
    - **Performance issues:** Monitor system resources and adjust task intervals
    - **Database errors:** Ensure database is accessible and migrations are up to date
    """)
    
    # Support
    st.header("Support")
    
    st.write("""
    For additional help:
    
    - Check the documentation in the `core/scheduler/` directory
    - Review the API documentation in `core/scheduler/API.md`
    - Check the deployment guide in `core/scheduler/DEPLOYMENT.md`
    - Review error logs for specific error messages
    """)


def main():
    """Main function for the scheduler example."""
    st.set_page_config(
        page_title="Trading System - Scheduler",
        page_icon="📅",
        layout="wide"
    )
    
    # Sidebar
    render_scheduler_sidebar()
    
    # Main content
    st.title("Trading System - Task Scheduler")
    
    # Navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Status", "Tasks", "Metrics", "Logs", "Config", "Help"
    ])
    
    with tab1:
        render_scheduler_page()
        
    with tab2:
        render_scheduler_page()
        
    with tab3:
        render_scheduler_metrics()
        
    with tab4:
        render_scheduler_logs()
        
    with tab5:
        render_scheduler_config()
        
    with tab6:
        render_scheduler_help()


if __name__ == "__main__":
    main()

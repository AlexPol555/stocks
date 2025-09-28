"""Streamlit app for the task scheduler.

This module provides a complete Streamlit application
for managing the task scheduler.
"""

import streamlit as st
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .scheduler import TaskScheduler, TaskStatus
from .trading_calendar import TradingCalendar, Market
from .integration import SchedulerIntegration
from .real_integration import RealSchedulerIntegration

logger = logging.getLogger(__name__)


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scheduler.log')
        ]
    )


@st.cache_resource
def get_scheduler_integration(api_key: Optional[str] = None) -> RealSchedulerIntegration:
    """Get cached scheduler integration instance.
    
    Args:
        api_key: Tinkoff API key for market data
        
    Returns:
        Scheduler integration instance
    """
    return RealSchedulerIntegration(api_key)


def render_header():
    """Render page header."""
    st.title("📅 Task Scheduler")
    st.markdown("Automated task scheduling for your trading system")
    
    # Status indicator
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = get_scheduler_integration()
        
    scheduler = st.session_state.scheduler
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
            
        # Overall status
        if status.get('running', False):
            st.success("🟢 Scheduler is running")
        else:
            st.error("🔴 Scheduler is stopped")
    else:
        st.warning("Unable to get scheduler status")


def render_scheduler_controls():
    """Render scheduler control buttons."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = get_scheduler_integration()
        
    scheduler = st.session_state.scheduler
    
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


def render_task_management():
    """Render task management interface."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = get_scheduler_integration()
        
    scheduler = st.session_state.scheduler
    
    st.header("Task Management")
    
    # Get status
    status = scheduler.get_status()
    
    if not status:
        st.error("Unable to get scheduler status")
        return
        
    # Task list
    tasks = status.get('tasks', {})
    
    if not tasks:
        st.warning("No tasks configured")
        return
        
    # Create DataFrame for better display
    task_data = []
    for name, info in tasks.items():
        task_data.append({
            'Task Name': name,
            'Status': info.get('status', 'Unknown'),
            'Enabled': info.get('enabled', False),
            'Error Count': info.get('error_count', 0),
            'Last Run': info.get('last_run', 'Never'),
            'Next Run': info.get('next_run', 'Not scheduled')
        })
        
    df = pd.DataFrame(task_data)
    
    # Display tasks
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )
    
    # Task controls
    st.subheader("Task Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_task = st.selectbox(
            "Select Task",
            options=list(tasks.keys()),
            key="task_selector"
        )
        
    with col2:
        if selected_task:
            task_info = tasks[selected_task]
            enabled = task_info.get('enabled', False)
            
            if enabled:
                if st.button("Disable Task", key="disable_task"):
                    scheduler.disable_task(selected_task)
                    st.rerun()
            else:
                if st.button("Enable Task", key="enable_task"):
                    scheduler.enable_task(selected_task)
                    st.rerun()
                    
    # Task details
    if selected_task:
        st.subheader(f"Task Details: {selected_task}")
        
        task_info = tasks[selected_task]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Status:** {task_info.get('status', 'Unknown')}")
            st.write(f"**Enabled:** {task_info.get('enabled', False)}")
            st.write(f"**Error Count:** {task_info.get('error_count', 0)}")
            
        with col2:
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


def render_metrics():
    """Render scheduler metrics and charts."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = get_scheduler_integration()
        
    scheduler = st.session_state.scheduler
    
    st.header("Performance Metrics")
    
    # Get status
    status = scheduler.get_status()
    
    if not status:
        st.error("Unable to get scheduler status")
        return
        
    # Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_tasks = status.get('total_tasks', 0)
        st.metric("Total Tasks", total_tasks)
        
    with col2:
        enabled_tasks = status.get('enabled_tasks', 0)
        st.metric("Enabled Tasks", enabled_tasks)
        
    with col3:
        failed_tasks = status.get('failed_tasks', 0)
        st.metric("Failed Tasks", failed_tasks)
        
    # Task status chart
    st.subheader("Task Status Distribution")
    
    tasks = status.get('tasks', {})
    if tasks:
        # Count tasks by status
        status_counts = {}
        for task_info in tasks.values():
            task_status = task_info.get('status', 'unknown')
            status_counts[task_status] = status_counts.get(task_status, 0) + 1
            
        # Create pie chart
        fig = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            title="Task Status Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
        
    # Error analysis
    st.subheader("Error Analysis")
    
    error_tasks = [
        (name, info) for name, info in tasks.items()
        if info.get('error_count', 0) > 0
    ]
    
    if error_tasks:
        st.warning(f"{len(error_tasks)} tasks have errors")
        
        # Create error chart
        error_data = []
        for task_name, task_info in error_tasks:
            error_data.append({
                'Task': task_name,
                'Error Count': task_info.get('error_count', 0)
            })
            
        error_df = pd.DataFrame(error_data)
        
        fig = px.bar(
            error_df,
            x='Task',
            y='Error Count',
            title="Task Error Counts"
        )
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.success("No tasks with errors")
        
    # Health score
    st.subheader("Health Score")
    
    total_tasks = status.get('total_tasks', 0)
    failed_tasks = status.get('failed_tasks', 0)
    
    if total_tasks > 0:
        health_score = ((total_tasks - failed_tasks) / total_tasks) * 100
        
        # Health score gauge
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = health_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Health Score (%)"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
        
        # Health status
        if health_score >= 90:
            st.success("🟢 Excellent health")
        elif health_score >= 70:
            st.warning("🟡 Good health")
        else:
            st.error("🔴 Poor health")
    else:
        st.info("No tasks to evaluate")


def render_schedule():
    """Render next scheduled tasks."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = get_scheduler_integration()
        
    scheduler = st.session_state.scheduler
    
    st.header("Next Scheduled Tasks")
    
    # Get next run times
    next_runs = scheduler.get_next_run_times()
    
    if not next_runs:
        st.warning("Unable to get next run times")
        return
        
    # Filter and sort tasks
    scheduled_tasks = [
        (name, time) for name, time in next_runs.items()
        if time is not None
    ]
    
    if not scheduled_tasks:
        st.info("No tasks scheduled")
        return
        
    # Sort by next run time
    scheduled_tasks.sort(key=lambda x: x[1])
    
    # Create DataFrame
    task_data = []
    for task_name, next_run in scheduled_tasks:
        task_data.append({
            'Task Name': task_name,
            'Next Run': next_run,
            'Time Until': str(next_run - datetime.now()) if next_run > datetime.now() else "Overdue"
        })
        
    df = pd.DataFrame(task_data)
    
    # Display
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Timeline chart
    if len(scheduled_tasks) > 1:
        st.subheader("Task Timeline")
        
        # Create timeline data
        timeline_data = []
        for task_name, next_run in scheduled_tasks:
            timeline_data.append({
                'Task': task_name,
                'Next Run': next_run,
                'Time': next_run.timestamp()
            })
            
        timeline_df = pd.DataFrame(timeline_data)
        
        # Create timeline chart
        fig = px.scatter(
            timeline_df,
            x='Next Run',
            y='Task',
            title="Task Execution Timeline",
            labels={'Next Run': 'Scheduled Time', 'Task': 'Task Name'}
        )
        
        fig.update_layout(
            xaxis_title="Scheduled Time",
            yaxis_title="Task Name"
        )
        
        st.plotly_chart(fig, use_container_width=True)


def render_logs():
    """Render scheduler logs."""
    st.header("Scheduler Logs")
    
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


def render_config():
    """Render scheduler configuration."""
    st.header("Scheduler Configuration")
    
    # Configuration sections
    st.subheader("Task Configuration")
    
    # Task intervals
    st.write("**Task Intervals:**")
    intervals = {
        "update_market_data": "1 hour",
        "fetch_news": "30 minutes",
        "process_news_pipeline": "2 hours",
        "calculate_indicators": "1 hour",
        "generate_signals": "1 hour",
        "send_notifications": "15 minutes"
    }
    
    for task_name, interval in intervals.items():
        st.write(f"• {task_name}: {interval}")
        
    # Task priorities
    st.write("**Task Priorities:**")
    priorities = {
        "update_market_data": 10,
        "send_notifications": 9,
        "calculate_indicators": 8,
        "generate_signals": 7,
        "fetch_news": 5,
        "process_news_pipeline": 3
    }
    
    for task_name, priority in priorities.items():
        st.write(f"• {task_name}: {priority}")
        
    # Market hours
    st.subheader("Market Hours")
    
    market_hours = {
        "MOEX": "10:00 - 18:45 MSK",
        "NYSE": "09:30 - 16:00 EST",
        "NASDAQ": "09:30 - 16:00 EST"
    }
    
    for market, hours in market_hours.items():
        st.write(f"• {market}: {hours}")
        
    # Configuration controls
    st.subheader("Configuration Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export Configuration"):
            st.info("Configuration export not implemented yet")
            
    with col2:
        if st.button("Import Configuration"):
            st.info("Configuration import not implemented yet")


def render_help():
    """Render help and documentation."""
    st.header("Help & Documentation")
    
    # Overview
    st.subheader("Overview")
    st.write("""
    The Task Scheduler is a powerful tool for automating various tasks in your trading system.
    It can schedule and execute tasks at specific intervals, manage dependencies between tasks,
    and provide intelligent scheduling based on market conditions.
    """)
    
    # Features
    st.subheader("Features")
    
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
    st.subheader("Task Types")
    
    task_types = {
        "Market Data Updates": "Automatically update market data from various sources",
        "News Fetching": "Fetch and process news from RSS feeds",
        "Technical Analysis": "Calculate technical indicators and generate signals",
        "Notifications": "Send alerts and notifications for important events"
    }
    
    for task_type, description in task_types.items():
        st.write(f"**{task_type}:** {description}")
        
    # Getting Started
    st.subheader("Getting Started")
    
    st.write("""
    1. **Start the Scheduler:** Click the "Start Scheduler" button to begin automated task execution
    2. **Monitor Tasks:** Use the "Tasks" tab to view and manage individual tasks
    3. **Check Metrics:** Use the "Metrics" tab to monitor performance and health
    4. **View Logs:** Use the "Logs" tab to troubleshoot issues
    """)
    
    # Troubleshooting
    st.subheader("Troubleshooting")
    
    st.write("""
    **Common Issues:**
    
    - **Tasks not running:** Check if the scheduler is started and tasks are enabled
    - **Task failures:** Review error logs and check task dependencies
    - **Performance issues:** Monitor system resources and adjust task intervals
    - **Database errors:** Ensure database is accessible and migrations are up to date
    """)


def main():
    """Main function for the Streamlit app."""
    # Setup logging
    setup_logging()
    
    # Page config
    st.set_page_config(
        page_title="Task Scheduler",
        page_icon="📅",
        layout="wide"
    )
    
    # Header
    render_header()
    
    # Navigation
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Controls", "Tasks", "Metrics", "Schedule", "Logs", "Config", "Help"
    ])
    
    with tab1:
        render_scheduler_controls()
        
    with tab2:
        render_task_management()
        
    with tab3:
        render_metrics()
        
    with tab4:
        render_schedule()
        
    with tab5:
        render_logs()
        
    with tab6:
        render_config()
        
    with tab7:
        render_help()


if __name__ == "__main__":
    main()

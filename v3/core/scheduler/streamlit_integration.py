"""Streamlit integration for the task scheduler.

This module provides Streamlit components for integrating
the task scheduler into the main application.
"""

import streamlit as st
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .scheduler import TaskScheduler, TaskStatus
from .trading_calendar import TradingCalendar, Market
from .integration import SchedulerIntegration
from .real_integration import RealSchedulerIntegration

logger = logging.getLogger(__name__)


@st.cache_resource
def get_scheduler_integration(api_key: Optional[str] = None) -> RealSchedulerIntegration:
    """Get cached scheduler integration instance.
    
    Args:
        api_key: Tinkoff API key for market data
        
    Returns:
        Scheduler integration instance
    """
    return RealSchedulerIntegration(api_key)


def render_scheduler_status_card():
    """Render scheduler status card."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = get_scheduler_integration()
        
    scheduler = st.session_state.scheduler
    
    # Get status
    status = scheduler.get_status()
    
    if not status:
        st.error("Unable to get scheduler status")
        return
        
    # Status card
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Tasks",
                status.get('total_tasks', 0),
                delta=None
            )
            
        with col2:
            st.metric(
                "Enabled Tasks",
                status.get('enabled_tasks', 0),
                delta=None
            )
            
        with col3:
            st.metric(
                "Running Tasks",
                status.get('running_tasks', 0),
                delta=None
            )
            
        with col4:
            failed_tasks = status.get('failed_tasks', 0)
            st.metric(
                "Failed Tasks",
                failed_tasks,
                delta=None,
                delta_color="inverse" if failed_tasks > 0 else "normal"
            )
            
        # Overall status
        if status.get('running', False):
            st.success("🟢 Scheduler is running")
        else:
            st.error("🔴 Scheduler is stopped")


def render_task_list():
    """Render task list with controls."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = get_scheduler_integration()
        
    scheduler = st.session_state.scheduler
    
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


def render_scheduler_controls():
    """Render scheduler control buttons."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = get_scheduler_integration()
        
    scheduler = st.session_state.scheduler
    
    # Get status
    status = scheduler.get_status()
    running = status.get('running', False) if status else False
    
    # Control buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not running:
            if st.button("Start Scheduler", type="primary", key="start_scheduler"):
                scheduler.start_scheduler()
                st.rerun()
        else:
            if st.button("Stop Scheduler", key="stop_scheduler"):
                scheduler.stop_scheduler()
                st.rerun()
                
    with col2:
        if st.button("Refresh Status", key="refresh_status"):
            st.rerun()
            
    with col3:
        if st.button("Reset Tasks", key="reset_tasks"):
            # This would reset all tasks to their default state
            st.warning("Reset functionality not implemented yet")
            
    # Status indicator
    if running:
        st.success("🟢 Scheduler is running")
    else:
        st.error("🔴 Scheduler is stopped")


def render_task_metrics():
    """Render task metrics and charts."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = get_scheduler_integration()
        
    scheduler = st.session_state.scheduler
    
    # Get status
    status = scheduler.get_status()
    
    if not status:
        st.error("Unable to get scheduler status")
        return
        
    # Metrics
    st.subheader("Performance Metrics")
    
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


def render_next_scheduled_tasks():
    """Render next scheduled tasks."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = get_scheduler_integration()
        
    scheduler = st.session_state.scheduler
    
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
    st.subheader("Next Scheduled Tasks")
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


def render_scheduler_logs():
    """Render scheduler logs."""
    st.subheader("Scheduler Logs")
    
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


def render_scheduler_page():
    """Render complete scheduler page."""
    st.title("📅 Task Scheduler")
    
    # Status card
    render_scheduler_status_card()
    
    st.divider()
    
    # Controls
    render_scheduler_controls()
    
    st.divider()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Tasks", "Metrics", "Schedule", "Logs"])
    
    with tab1:
        render_task_list()
        
    with tab2:
        render_task_metrics()
        
    with tab3:
        render_next_scheduled_tasks()
        
    with tab4:
        render_scheduler_logs()


# Example usage in main app
def main():
    """Example usage in main application."""
    st.set_page_config(
        page_title="Trading System - Scheduler",
        page_icon="📅",
        layout="wide"
    )
    
    # Render scheduler page
    render_scheduler_page()


if __name__ == "__main__":
    main()

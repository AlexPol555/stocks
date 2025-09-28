"""Integration example for the main application.

This module demonstrates how to integrate the task scheduler
into the main Streamlit application with proper error handling
and configuration.
"""

import streamlit as st
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import traceback

from .scheduler import TaskScheduler
from .trading_calendar import TradingCalendar, Market
from .integration import SchedulerIntegration
from .real_integration import RealSchedulerIntegration

logger = logging.getLogger(__name__)


class AppSchedulerManager:
    """Manager class for integrating scheduler with the main app."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize scheduler manager.
        
        Args:
            api_key: Tinkoff API key for market data
        """
        self.api_key = api_key
        self.scheduler = None
        self.integration = None
        self._initialized = False
        self._error = None
        
    def initialize(self) -> bool:
        """Initialize scheduler and integration.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if self._initialized:
                return True
                
            # Create real integration
            self.integration = RealSchedulerIntegration(self.api_key)
            self.scheduler = self.integration.scheduler
            
            self._initialized = True
            self._error = None
            
            logger.info("Scheduler manager initialized successfully")
            return True
            
        except Exception as e:
            self._error = str(e)
            logger.error(f"Error initializing scheduler manager: {e}")
            logger.error(traceback.format_exc())
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status.
        
        Returns:
            Dictionary with scheduler status
        """
        if not self._initialized or not self.integration:
            return {"error": "Scheduler not initialized"}
            
        try:
            return self.integration.get_task_status()
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {"error": str(e)}
            
    def start_scheduler(self) -> bool:
        """Start the scheduler.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self._initialized or not self.integration:
            logger.error("Scheduler not initialized")
            return False
            
        try:
            self.integration.start_scheduler()
            logger.info("Scheduler started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            return False
            
    def stop_scheduler(self) -> bool:
        """Stop the scheduler.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if not self._initialized or not self.integration:
            logger.error("Scheduler not initialized")
            return False
            
        try:
            self.integration.stop_scheduler()
            logger.info("Scheduler stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            return False
            
    def enable_task(self, task_name: str) -> bool:
        """Enable a task.
        
        Args:
            task_name: Name of task to enable
            
        Returns:
            True if enabled successfully, False otherwise
        """
        if not self._initialized or not self.integration:
            logger.error("Scheduler not initialized")
            return False
            
        try:
            self.integration.enable_task(task_name)
            logger.info(f"Task '{task_name}' enabled successfully")
            return True
        except Exception as e:
            logger.error(f"Error enabling task '{task_name}': {e}")
            return False
            
    def disable_task(self, task_name: str) -> bool:
        """Disable a task.
        
        Args:
            task_name: Name of task to disable
            
        Returns:
            True if disabled successfully, False otherwise
        """
        if not self._initialized or not self.integration:
            logger.error("Scheduler not initialized")
            return False
            
        try:
            self.integration.disable_task(task_name)
            logger.info(f"Task '{task_name}' disabled successfully")
            return True
        except Exception as e:
            logger.error(f"Error disabling task '{task_name}': {e}")
            return False
            
    def get_next_run_times(self) -> Dict[str, Optional[datetime]]:
        """Get next run times for all tasks.
        
        Returns:
            Dictionary mapping task names to next run times
        """
        if not self._initialized or not self.integration:
            return {}
            
        try:
            return self.integration.get_next_run_times()
        except Exception as e:
            logger.error(f"Error getting next run times: {e}")
            return {}
            
    def is_initialized(self) -> bool:
        """Check if scheduler is initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized
        
    def get_error(self) -> Optional[str]:
        """Get last error message.
        
        Returns:
            Error message or None if no error
        """
        return self._error


def get_scheduler_manager() -> AppSchedulerManager:
    """Get or create scheduler manager instance.
    
    Returns:
        Scheduler manager instance
    """
    if 'scheduler_manager' not in st.session_state:
        # Get API key from session state or environment
        api_key = st.session_state.get('tinkoff_api_key')
        st.session_state.scheduler_manager = AppSchedulerManager(api_key)
        
    return st.session_state.scheduler_manager


def render_scheduler_sidebar():
    """Render scheduler status in sidebar."""
    manager = get_scheduler_manager()
    
    with st.sidebar:
        st.title("📅 Scheduler")
        
        # Initialize if not already done
        if not manager.is_initialized():
            if st.button("Initialize Scheduler"):
                if manager.initialize():
                    st.success("Scheduler initialized")
                    st.rerun()
                else:
                    st.error(f"Failed to initialize: {manager.get_error()}")
                    return
        else:
            # Get status
            status = manager.get_status()
            
            if "error" in status:
                st.error(f"Scheduler error: {status['error']}")
                return
                
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
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Start"):
                    if manager.start_scheduler():
                        st.success("Scheduler started")
                        st.rerun()
                    else:
                        st.error("Failed to start scheduler")
                        
            with col2:
                if st.button("Stop"):
                    if manager.stop_scheduler():
                        st.success("Scheduler stopped")
                        st.rerun()
                    else:
                        st.error("Failed to stop scheduler")


def render_scheduler_page():
    """Render dedicated scheduler page."""
    st.title("📅 Task Scheduler")
    
    manager = get_scheduler_manager()
    
    # Initialize if not already done
    if not manager.is_initialized():
        st.warning("Scheduler not initialized. Click 'Initialize Scheduler' in the sidebar.")
        return
        
    # Status overview
    st.header("Status Overview")
    
    status = manager.get_status()
    if "error" in status:
        st.error(f"Scheduler error: {status['error']}")
        return
        
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
                            if manager.disable_task(task_name):
                                st.success("Task disabled")
                                st.rerun()
                            else:
                                st.error("Failed to disable task")
                    else:
                        if st.button("Enable", key=f"enable_{task_name}"):
                            if manager.enable_task(task_name):
                                st.success("Task enabled")
                                st.rerun()
                            else:
                                st.error("Failed to enable task")
                                
    else:
        st.warning("No tasks configured")
        
    # Scheduler controls
    st.header("Scheduler Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Start Scheduler", type="primary"):
            if manager.start_scheduler():
                st.success("Scheduler started")
                st.rerun()
            else:
                st.error("Failed to start scheduler")
                
    with col2:
        if st.button("Stop Scheduler"):
            if manager.stop_scheduler():
                st.success("Scheduler stopped")
                st.rerun()
            else:
                st.error("Failed to stop scheduler")
                
    with col3:
        if st.button("Refresh Status"):
            st.rerun()
            
    # Next scheduled tasks
    st.header("Next Scheduled Tasks")
    
    next_runs = manager.get_next_run_times()
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
    
    manager = get_scheduler_manager()
    
    if not manager.is_initialized():
        st.warning("Scheduler not initialized. Click 'Initialize Scheduler' in the sidebar.")
        return
        
    # Get status
    status = manager.get_status()
    if "error" in status:
        st.error(f"Scheduler error: {status['error']}")
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
    tab1, tab2, tab3 = st.tabs(["Status", "Metrics", "Logs"])
    
    with tab1:
        render_scheduler_page()
        
    with tab2:
        render_scheduler_metrics()
        
    with tab3:
        render_scheduler_logs()


if __name__ == "__main__":
    main()

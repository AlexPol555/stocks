"""Integration example for the main application.

This module demonstrates how to integrate the task scheduler
with the main Streamlit application.
"""

import asyncio
import logging
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from .scheduler import TaskScheduler
from .trading_calendar import TradingCalendar, Market
from .integration import SchedulerIntegration
from .real_integration import RealSchedulerIntegration

logger = logging.getLogger(__name__)


class AppSchedulerIntegration:
    """Integration class for the main Streamlit application."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize app integration.
        
        Args:
            api_key: Tinkoff API key for market data
        """
        self.api_key = api_key
        self.scheduler = None
        self.integration = None
        self._setup_scheduler()
        
    def _setup_scheduler(self):
        """Setup scheduler and integration."""
        try:
            # Create real integration
            self.integration = RealSchedulerIntegration(self.api_key)
            self.scheduler = self.integration.scheduler
            
            logger.info("Scheduler integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing scheduler: {e}")
            # Fallback to basic integration
            self._setup_fallback_scheduler()
            
    def _setup_fallback_scheduler(self):
        """Setup fallback scheduler without real integrations."""
        try:
            trading_calendar = TradingCalendar()
            self.scheduler = TaskScheduler(trading_calendar)
            self.integration = SchedulerIntegration(self.scheduler, trading_calendar)
            
            # Setup basic tasks
            self.integration.setup_all_tasks(
                data_loader_func=self._dummy_data_loader,
                news_fetch_func=self._dummy_news_fetch,
                news_process_func=self._dummy_news_process,
                indicators_func=self._dummy_indicators,
                signals_func=self._dummy_signals,
                notification_func=self._dummy_notifications
            )
            
            logger.info("Fallback scheduler initialized")
            
        except Exception as e:
            logger.error(f"Error initializing fallback scheduler: {e}")
            raise
            
    def _dummy_data_loader(self):
        """Dummy data loader for fallback mode."""
        logger.info("Dummy data loader executed")
        
    def _dummy_news_fetch(self):
        """Dummy news fetch for fallback mode."""
        logger.info("Dummy news fetch executed")
        
    def _dummy_news_process(self):
        """Dummy news process for fallback mode."""
        logger.info("Dummy news process executed")
        
    def _dummy_indicators(self):
        """Dummy indicators calculation for fallback mode."""
        logger.info("Dummy indicators calculation executed")
        
    def _dummy_signals(self):
        """Dummy signals generation for fallback mode."""
        logger.info("Dummy signals generation executed")
        
    def _dummy_notifications(self):
        """Dummy notifications for fallback mode."""
        logger.info("Dummy notifications executed")
        
    def start_scheduler(self):
        """Start the scheduler."""
        if self.integration and not self.scheduler.running:
            self.integration.start_scheduler()
            logger.info("Scheduler started")
            
    def stop_scheduler(self):
        """Stop the scheduler."""
        if self.integration and self.scheduler.running:
            self.integration.stop_scheduler()
            logger.info("Scheduler stopped")
            
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        if self.integration:
            return self.integration.get_task_status()
        return {}
        
    def get_next_run_times(self) -> Dict[str, Optional[datetime]]:
        """Get next run times for all tasks."""
        if self.integration:
            return self.integration.get_next_run_times()
        return {}
        
    def enable_task(self, task_name: str):
        """Enable a task."""
        if self.integration:
            self.integration.enable_task(task_name)
            
    def disable_task(self, task_name: str):
        """Disable a task."""
        if self.integration:
            self.integration.disable_task(task_name)


def render_scheduler_sidebar():
    """Render scheduler status in sidebar."""
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = AppSchedulerIntegration()
        
    scheduler = st.session_state.scheduler
    
    with st.sidebar:
        st.title("📅 Scheduler Status")
        
        # Get status
        status = scheduler.get_status()
        
        if status:
            # Overall status
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Tasks", status.get('total_tasks', 0))
            with col2:
                st.metric("Enabled Tasks", status.get('enabled_tasks', 0))
                
            # Running status
            if status.get('running', False):
                st.success("🟢 Scheduler Running")
            else:
                st.error("🔴 Scheduler Stopped")
                
            # Task details
            if st.expander("Task Details", expanded=False):
                for task_name, task_info in status.get('tasks', {}).items():
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**{task_name}**")
                            st.write(f"Status: {task_info.get('status', 'Unknown')}")
                            
                        with col2:
                            if task_info.get('enabled', False):
                                if st.button("Disable", key=f"disable_{task_name}"):
                                    scheduler.disable_task(task_name)
                                    st.rerun()
                            else:
                                if st.button("Enable", key=f"enable_{task_name}"):
                                    scheduler.enable_task(task_name)
                                    st.rerun()
                                    
                        # Next run time
                        next_run = task_info.get('next_run')
                        if next_run:
                            st.write(f"Next run: {next_run}")
                        else:
                            st.write("Not scheduled")
                            
                        st.divider()
                        
            # Control buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Start Scheduler"):
                    scheduler.start_scheduler()
                    st.rerun()
                    
            with col2:
                if st.button("Stop Scheduler"):
                    scheduler.stop_scheduler()
                    st.rerun()
                    
        else:
            st.warning("Scheduler not available")


def render_scheduler_page():
    """Render dedicated scheduler page."""
    st.title("📅 Task Scheduler")
    
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = AppSchedulerIntegration()
        
    scheduler = st.session_state.scheduler
    
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
        
    # Logs
    st.header("Recent Logs")
    
    if st.button("View Logs"):
        try:
            with open('scheduler.log', 'r') as f:
                logs = f.readlines()
                
            # Show last 50 lines
            recent_logs = logs[-50:]
            for log in recent_logs:
                st.text(log.strip())
                
        except FileNotFoundError:
            st.warning("Log file not found")
        except Exception as e:
            st.error(f"Error reading logs: {e}")


def render_scheduler_metrics():
    """Render scheduler metrics page."""
    st.title("📊 Scheduler Metrics")
    
    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = AppSchedulerIntegration()
        
    scheduler = st.session_state.scheduler
    
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


# Example usage in main app
def main():
    """Example usage in main application."""
    st.set_page_config(
        page_title="Trading System",
        page_icon="📈",
        layout="wide"
    )
    
    # Add scheduler to sidebar
    render_scheduler_sidebar()
    
    # Main content
    st.title("Trading System Dashboard")
    
    # Add scheduler page to navigation
    if st.button("Go to Scheduler"):
        render_scheduler_page()
        
    if st.button("Go to Metrics"):
        render_scheduler_metrics()


if __name__ == "__main__":
    main()

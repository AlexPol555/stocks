"""Tests for the task scheduler module."""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from core.scheduler import TaskScheduler, TaskStatus
from core.scheduler.trading_calendar import TradingCalendar, Market
from core.scheduler.integration import SchedulerIntegration


class TestTaskScheduler:
    """Test cases for TaskScheduler class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.scheduler = TaskScheduler()
        self.mock_func = Mock()
        
    def test_add_task(self):
        """Test adding a task."""
        self.scheduler.add_task(
            name="test_task",
            func=self.mock_func,
            interval=timedelta(minutes=5)
        )
        
        assert "test_task" in self.scheduler.tasks
        assert self.scheduler.tasks["test_task"].name == "test_task"
        assert self.scheduler.tasks["test_task"].func == self.mock_func
        assert self.scheduler.tasks["test_task"].interval == timedelta(minutes=5)
        
    def test_add_duplicate_task(self):
        """Test adding duplicate task raises error."""
        self.scheduler.add_task(
            name="test_task",
            func=self.mock_func,
            interval=timedelta(minutes=5)
        )
        
        with pytest.raises(ValueError, match="Task 'test_task' already exists"):
            self.scheduler.add_task(
                name="test_task",
                func=self.mock_func,
                interval=timedelta(minutes=10)
            )
            
    def test_remove_task(self):
        """Test removing a task."""
        self.scheduler.add_task(
            name="test_task",
            func=self.mock_func,
            interval=timedelta(minutes=5)
        )
        
        self.scheduler.remove_task("test_task")
        assert "test_task" not in self.scheduler.tasks
        
    def test_enable_disable_task(self):
        """Test enabling and disabling tasks."""
        self.scheduler.add_task(
            name="test_task",
            func=self.mock_func,
            interval=timedelta(minutes=5)
        )
        
        # Test disable
        self.scheduler.disable_task("test_task")
        assert not self.scheduler.tasks["test_task"].enabled
        
        # Test enable
        self.scheduler.enable_task("test_task")
        assert self.scheduler.tasks["test_task"].enabled
        
    def test_get_task_status(self):
        """Test getting task status."""
        self.scheduler.add_task(
            name="test_task",
            func=self.mock_func,
            interval=timedelta(minutes=5)
        )
        
        status = self.scheduler.get_task_status("test_task")
        assert status == TaskStatus.PENDING
        
        # Test non-existent task
        status = self.scheduler.get_task_status("non_existent")
        assert status is None
        
    def test_get_next_run_time(self):
        """Test getting next run time."""
        self.scheduler.add_task(
            name="test_task",
            func=self.mock_func,
            interval=timedelta(minutes=5)
        )
        
        next_run = self.scheduler.get_next_run_time("test_task")
        assert next_run is not None
        assert isinstance(next_run, datetime)
        
        # Test non-existent task
        next_run = self.scheduler.get_next_run_time("non_existent")
        assert next_run is None
        
    def test_get_ready_tasks(self):
        """Test getting ready tasks."""
        # Add a task that should be ready
        self.scheduler.add_task(
            name="ready_task",
            func=self.mock_func,
            interval=timedelta(seconds=1)
        )
        
        # Add a task that should not be ready
        self.scheduler.add_task(
            name="not_ready_task",
            func=self.mock_func,
            interval=timedelta(hours=1)
        )
        
        # Wait a bit for the first task to be ready
        import time
        time.sleep(1.1)
        
        ready_tasks = self.scheduler._get_ready_tasks()
        assert len(ready_tasks) == 1
        assert ready_tasks[0].name == "ready_task"
        
    def test_check_dependencies(self):
        """Test dependency checking."""
        # Add tasks with dependencies
        self.scheduler.add_task(
            name="task1",
            func=self.mock_func,
            interval=timedelta(minutes=5)
        )
        
        self.scheduler.add_task(
            name="task2",
            func=self.mock_func,
            interval=timedelta(minutes=5),
            dependencies=["task1"]
        )
        
        # Task1 should have no dependencies
        assert self.scheduler._check_dependencies(self.scheduler.tasks["task1"])
        
        # Task2 should depend on task1
        assert not self.scheduler._check_dependencies(self.scheduler.tasks["task2"])
        
        # Mark task1 as completed
        self.scheduler.tasks["task1"].status = TaskStatus.COMPLETED
        assert self.scheduler._check_dependencies(self.scheduler.tasks["task2"])
        
    @pytest.mark.asyncio
    async def test_execute_task_success(self):
        """Test successful task execution."""
        self.scheduler.add_task(
            name="test_task",
            func=self.mock_func,
            interval=timedelta(minutes=5)
        )
        
        task = self.scheduler.tasks["test_task"]
        await self.scheduler._execute_task(task)
        
        assert task.status == TaskStatus.COMPLETED
        assert task.error_count == 0
        assert task.last_run is not None
        self.mock_func.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_execute_task_failure(self):
        """Test task execution failure."""
        # Create a function that raises an exception
        def failing_func():
            raise Exception("Test error")
            
        self.scheduler.add_task(
            name="failing_task",
            func=failing_func,
            interval=timedelta(minutes=5),
            max_errors=2
        )
        
        task = self.scheduler.tasks["failing_task"]
        await self.scheduler._execute_task(task)
        
        assert task.status == TaskStatus.FAILED
        assert task.error_count == 1
        assert task.enabled  # Should still be enabled
        
        # Execute again to exceed max errors
        await self.scheduler._execute_task(task)
        assert task.error_count == 2
        assert not task.enabled  # Should be disabled now
        
    def test_get_status(self):
        """Test getting scheduler status."""
        self.scheduler.add_task(
            name="test_task",
            func=self.mock_func,
            interval=timedelta(minutes=5)
        )
        
        status = self.scheduler.get_status()
        
        assert "running" in status
        assert "total_tasks" in status
        assert "enabled_tasks" in status
        assert "running_tasks" in status
        assert "failed_tasks" in status
        assert "tasks" in status
        
        assert status["total_tasks"] == 1
        assert status["enabled_tasks"] == 1
        assert status["running_tasks"] == 0
        assert status["failed_tasks"] == 0


class TestTradingCalendar:
    """Test cases for TradingCalendar class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.calendar = TradingCalendar()
        
    def test_is_trading_day(self):
        """Test trading day detection."""
        # Monday should be a trading day
        monday = datetime(2024, 1, 1)  # Assuming this is a Monday
        assert self.calendar.is_trading_day(monday)
        
        # Saturday should not be a trading day
        saturday = datetime(2024, 1, 6)  # Assuming this is a Saturday
        assert not self.calendar.is_trading_day(saturday)
        
    def test_is_market_open(self):
        """Test market open detection."""
        # Test during trading hours
        trading_time = datetime(2024, 1, 1, 12, 0)  # Monday 12:00
        assert self.calendar.is_market_open(Market.MOEX, trading_time)
        
        # Test outside trading hours
        non_trading_time = datetime(2024, 1, 1, 20, 0)  # Monday 20:00
        assert not self.calendar.is_market_open(Market.MOEX, non_trading_time)
        
    def test_get_next_trading_day(self):
        """Test getting next trading day."""
        # Test from a weekday
        monday = datetime(2024, 1, 1)  # Assuming this is a Monday
        next_day = self.calendar.get_next_trading_day(monday)
        assert next_day.weekday() == 1  # Should be Tuesday
        
        # Test from a weekend
        saturday = datetime(2024, 1, 6)  # Assuming this is a Saturday
        next_day = self.calendar.get_next_trading_day(saturday)
        assert next_day.weekday() == 0  # Should be Monday
        
    def test_get_trading_sessions(self):
        """Test getting trading sessions."""
        sessions = self.calendar.get_trading_sessions()
        assert len(sessions) > 0
        
        # Test filtering by market
        moex_sessions = self.calendar.get_trading_sessions(Market.MOEX)
        assert len(moex_sessions) == 1
        assert moex_sessions[0].market == Market.MOEX
        
    def test_get_market_hours(self):
        """Test getting market hours."""
        hours = self.calendar.get_market_hours(Market.MOEX)
        assert hours is not None
        assert len(hours) == 2
        assert hours[0] is not None  # start_time
        assert hours[1] is not None  # end_time
        
    def test_should_run_task(self):
        """Test task run decision logic."""
        # Market data task should run during trading hours
        assert self.calendar.should_run_task("update_market_data", Market.MOEX)
        
        # News task should always run
        assert self.calendar.should_run_task("fetch_news")
        
        # Analysis task should run on trading days
        assert self.calendar.should_run_task("calculate_indicators")
        
    def test_get_optimal_run_time(self):
        """Test getting optimal run time."""
        optimal_time = self.calendar.get_optimal_run_time("update_market_data", Market.MOEX)
        assert isinstance(optimal_time, datetime)
        assert optimal_time > datetime.now()


class TestSchedulerIntegration:
    """Test cases for SchedulerIntegration class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.trading_calendar = TradingCalendar()
        self.scheduler = TaskScheduler(self.trading_calendar)
        self.integration = SchedulerIntegration(self.scheduler, self.trading_calendar)
        
    def test_setup_market_data_tasks(self):
        """Test setting up market data tasks."""
        mock_func = Mock()
        self.integration.setup_market_data_tasks(mock_func)
        
        assert "update_market_data" in self.scheduler.tasks
        task = self.scheduler.tasks["update_market_data"]
        assert task.func == mock_func
        assert task.interval == timedelta(hours=1)
        assert task.priority == 10
        
    def test_setup_news_tasks(self):
        """Test setting up news tasks."""
        mock_fetch = Mock()
        mock_process = Mock()
        self.integration.setup_news_tasks(mock_fetch, mock_process)
        
        assert "fetch_news" in self.scheduler.tasks
        assert "process_news_pipeline" in self.scheduler.tasks
        
        fetch_task = self.scheduler.tasks["fetch_news"]
        assert fetch_task.func == mock_fetch
        assert fetch_task.interval == timedelta(minutes=30)
        
        process_task = self.scheduler.tasks["process_news_pipeline"]
        assert process_task.func == mock_process
        assert process_task.interval == timedelta(hours=2)
        assert "fetch_news" in process_task.dependencies
        
    def test_setup_analysis_tasks(self):
        """Test setting up analysis tasks."""
        mock_indicators = Mock()
        mock_signals = Mock()
        self.integration.setup_analysis_tasks(mock_indicators, mock_signals)
        
        assert "calculate_indicators" in self.scheduler.tasks
        assert "generate_signals" in self.scheduler.tasks
        
        indicators_task = self.scheduler.tasks["calculate_indicators"]
        assert indicators_task.func == mock_indicators
        assert "update_market_data" in indicators_task.dependencies
        
        signals_task = self.scheduler.tasks["generate_signals"]
        assert signals_task.func == mock_signals
        assert "calculate_indicators" in signals_task.dependencies
        
    def test_setup_notification_tasks(self):
        """Test setting up notification tasks."""
        mock_notifications = Mock()
        self.integration.setup_notification_tasks(mock_notifications)
        
        assert "send_notifications" in self.scheduler.tasks
        task = self.scheduler.tasks["send_notifications"]
        assert task.func == mock_notifications
        assert task.interval == timedelta(minutes=15)
        assert task.priority == 9
        
    def test_get_task_status(self):
        """Test getting task status."""
        self.integration.setup_market_data_tasks(Mock())
        status = self.integration.get_task_status()
        
        assert "total_tasks" in status
        assert status["total_tasks"] == 1
        
    def test_enable_disable_task(self):
        """Test enabling and disabling tasks."""
        self.integration.setup_market_data_tasks(Mock())
        
        self.integration.disable_task("update_market_data")
        assert not self.scheduler.tasks["update_market_data"].enabled
        
        self.integration.enable_task("update_market_data")
        assert self.scheduler.tasks["update_market_data"].enabled
        
    def test_get_next_run_times(self):
        """Test getting next run times."""
        self.integration.setup_market_data_tasks(Mock())
        next_runs = self.integration.get_next_run_times()
        
        assert "update_market_data" in next_runs
        assert next_runs["update_market_data"] is not None

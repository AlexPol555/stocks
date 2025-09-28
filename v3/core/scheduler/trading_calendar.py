"""Trading calendar implementation for market-aware scheduling.

This module provides functionality to determine trading sessions,
holidays, and market hours for intelligent task scheduling.
"""

import logging
from datetime import datetime, time, timedelta
from typing import List, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Market(Enum):
    """Supported markets."""
    MOEX = "moex"  # Moscow Exchange
    NYSE = "nyse"  # New York Stock Exchange
    NASDAQ = "nasdaq"  # NASDAQ


@dataclass
class TradingSession:
    """Represents a trading session."""
    market: Market
    start_time: time
    end_time: time
    timezone: str
    weekdays: Set[int]  # 0=Monday, 6=Sunday


class TradingCalendar:
    """Trading calendar for market-aware scheduling.
    
    Provides functionality to determine:
    - Trading sessions
    - Market holidays
    - Active trading hours
    """
    
    def __init__(self):
        """Initialize trading calendar."""
        self.sessions = self._initialize_sessions()
        self.holidays = self._initialize_holidays()
        
    def _initialize_sessions(self) -> List[TradingSession]:
        """Initialize trading sessions for different markets.
        
        Returns:
            List of trading sessions
        """
        sessions = []
        
        # MOEX (Moscow Exchange) - Monday to Friday, 10:00-18:45 MSK
        sessions.append(TradingSession(
            market=Market.MOEX,
            start_time=time(10, 0),
            end_time=time(18, 45),
            timezone="Europe/Moscow",
            weekdays={0, 1, 2, 3, 4}  # Monday to Friday
        ))
        
        # NYSE - Monday to Friday, 9:30-16:00 EST
        sessions.append(TradingSession(
            market=Market.NYSE,
            start_time=time(9, 30),
            end_time=time(16, 0),
            timezone="America/New_York",
            weekdays={0, 1, 2, 3, 4}  # Monday to Friday
        ))
        
        # NASDAQ - Monday to Friday, 9:30-16:00 EST
        sessions.append(TradingSession(
            market=Market.NASDAQ,
            start_time=time(9, 30),
            end_time=time(16, 0),
            timezone="America/New_York",
            weekdays={0, 1, 2, 3, 4}  # Monday to Friday
        ))
        
        return sessions
        
    def _initialize_holidays(self) -> Set[datetime]:
        """Initialize market holidays.
        
        Returns:
            Set of holiday dates
        """
        # This is a simplified implementation
        # In production, you would load holidays from a database or API
        holidays = set()
        
        # Add some common holidays (simplified)
        current_year = datetime.now().year
        
        # New Year's Day
        holidays.add(datetime(current_year, 1, 1))
        
        # Christmas
        holidays.add(datetime(current_year, 12, 25))
        
        # Add more holidays as needed...
        
        return holidays
        
    def is_trading_day(self, date: Optional[datetime] = None) -> bool:
        """Check if a date is a trading day.
        
        Args:
            date: Date to check (defaults to today)
            
        Returns:
            True if it's a trading day
        """
        if date is None:
            date = datetime.now()
            
        # Check if it's a holiday
        if date.date() in {h.date() for h in self.holidays}:
            return False
            
        # Check if it's a weekday
        return date.weekday() < 5  # Monday=0, Sunday=6
        
    def is_market_open(self, market: Market, date: Optional[datetime] = None) -> bool:
        """Check if a market is open at a specific time.
        
        Args:
            market: Market to check
            date: Date/time to check (defaults to now)
            
        Returns:
            True if market is open
        """
        if date is None:
            date = datetime.now()
            
        # Check if it's a trading day
        if not self.is_trading_day(date):
            return False
            
        # Find the trading session for this market
        session = next((s for s in self.sessions if s.market == market), None)
        if not session:
            logger.warning(f"No trading session found for market {market}")
            return False
            
        # Check if current time is within trading hours
        current_time = date.time()
        return session.start_time <= current_time <= session.end_time
        
    def get_next_trading_day(self, date: Optional[datetime] = None) -> datetime:
        """Get the next trading day.
        
        Args:
            date: Starting date (defaults to today)
            
        Returns:
            Next trading day
        """
        if date is None:
            date = datetime.now()
            
        # Start from next day
        next_day = date + timedelta(days=1)
        
        # Find next trading day
        while not self.is_trading_day(next_day):
            next_day += timedelta(days=1)
            
        return next_day
        
    def get_trading_sessions(self, market: Optional[Market] = None) -> List[TradingSession]:
        """Get trading sessions.
        
        Args:
            market: Filter by market (optional)
            
        Returns:
            List of trading sessions
        """
        if market:
            return [s for s in self.sessions if s.market == market]
        return self.sessions
        
    def get_market_hours(self, market: Market) -> Optional[tuple]:
        """Get market trading hours.
        
        Args:
            market: Market to get hours for
            
        Returns:
            Tuple of (start_time, end_time) or None if not found
        """
        session = next((s for s in self.sessions if s.market == market), None)
        if session:
            return (session.start_time, session.end_time)
        return None
        
    def should_run_task(self, task_name: str, market: Optional[Market] = None) -> bool:
        """Determine if a task should run based on market conditions.
        
        Args:
            task_name: Name of the task
            market: Market to check (optional)
            
        Returns:
            True if task should run
        """
        now = datetime.now()
        
        # Market data updates should only run during trading hours
        if "market_data" in task_name.lower():
            if market:
                return self.is_market_open(market, now)
            else:
                # Check if any market is open
                return any(self.is_market_open(m, now) for m in Market)
                
        # News fetching can run anytime
        if "news" in task_name.lower():
            return True
            
        # Technical analysis can run after market close
        if "indicators" in task_name.lower() or "analysis" in task_name.lower():
            return self.is_trading_day(now)
            
        # Default: run on trading days
        return self.is_trading_day(now)
        
    def get_optimal_run_time(self, task_name: str, market: Optional[Market] = None) -> datetime:
        """Get optimal time to run a task.
        
        Args:
            task_name: Name of the task
            market: Market to consider (optional)
            
        Returns:
            Optimal run time
        """
        now = datetime.now()
        
        # Market data updates should run at market open
        if "market_data" in task_name.lower():
            if market:
                session = next((s for s in self.sessions if s.market == market), None)
                if session:
                    next_trading_day = self.get_next_trading_day(now)
                    return datetime.combine(next_trading_day.date(), session.start_time)
            else:
                # Use MOEX as default
                return self.get_optimal_run_time(task_name, Market.MOEX)
                
        # News fetching should run every 30 minutes
        if "news" in task_name.lower():
            return now + timedelta(minutes=30)
            
        # Technical analysis should run after market close
        if "indicators" in task_name.lower() or "analysis" in task_name.lower():
            next_trading_day = self.get_next_trading_day(now)
            return next_trading_day.replace(hour=19, minute=0, second=0, microsecond=0)
            
        # Default: run in 1 hour
        return now + timedelta(hours=1)

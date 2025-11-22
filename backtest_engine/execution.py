"""
Order execution model for backtesting.
Handles order placement and execution timing.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class Order:
    """Represents a pending order."""
    ticker: str
    action: str  # 'BUY' or 'SELL'
    amount: Optional[float] = None  # Dollar amount
    shares: Optional[float] = None  # Number of shares
    reason: Optional[str] = None
    priority: int = 0  # Higher priority executes first


class ExecutionModel:
    """Handles order execution timing and logic."""
    
    def __init__(self, execution_when: str = "next_open"):
        """
        Initialize execution model.
        
        Args:
            execution_when: 'next_open', 'market_close', 'same_day'
        """
        self.execution_when = execution_when
        self.pending_orders: List[Order] = []
    
    def place_order(self, order: Order):
        """Add an order to the pending queue."""
        self.pending_orders.append(order)
        # Sort by priority (higher first)
        self.pending_orders.sort(key=lambda x: x.priority, reverse=True)
    
    def get_executable_orders(self, current_date: datetime, last_trade_date: Optional[datetime], is_first_day: bool = False) -> List[Order]:
        """
        Get orders that should be executed on the current date.
        
        Args:
            current_date: Current simulation date
            last_trade_date: Date of last trade (for cooldown logic)
            is_first_day: Whether this is the first day of the backtest
            
        Returns:
            List of orders to execute
        """
        if self.execution_when == "same_day":
            return self.pending_orders.copy()
        elif self.execution_when == "next_open":
            # Execute orders placed on previous day OR on first day
            # For rebalancing strategies, execute immediately when orders are placed
            if is_first_day or (last_trade_date is None) or (current_date > last_trade_date):
                return self.pending_orders.copy()
        elif self.execution_when == "market_close":
            # Execute at end of trading day
            return self.pending_orders.copy()
        elif self.execution_when == "first_day_only":
            # Only execute on first day
            if is_first_day:
                return self.pending_orders.copy()
        
        return []
    
    def clear_executed_orders(self, executed: List[Order]):
        """Remove executed orders from pending queue."""
        for order in executed:
            if order in self.pending_orders:
                self.pending_orders.remove(order)
    
    def clear_all_orders(self):
        """Clear all pending orders."""
        self.pending_orders.clear()


class RebalanceScheduler:
    """Manages rebalancing schedule (weekly, monthly, etc.)."""
    
    @staticmethod
    def should_rebalance(
        current_date: datetime,
        last_rebalance_date: Optional[datetime],
        frequency: str,
        trading_days_since: int = 0
    ) -> bool:
        """
        Check if rebalancing should occur on current date.
        
        Args:
            current_date: Current simulation date
            last_rebalance_date: Date of last rebalance
            frequency: 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'
            trading_days_since: Number of trading days since last rebalance
            
        Returns:
            True if rebalancing should occur
        """
        if last_rebalance_date is None:
            return True
        
        if frequency == "daily":
            return True
        elif frequency == "weekly":
            # Rebalance every 5 trading days (approximately weekly)
            # Or if 7+ calendar days have passed
            calendar_days = (current_date - last_rebalance_date).days
            return trading_days_since >= 5 or calendar_days >= 7
        elif frequency == "monthly":
            # Rebalance on same day of month or if 20+ trading days
            calendar_days = (current_date - last_rebalance_date).days
            return (current_date.year != last_rebalance_date.year or 
                   current_date.month != last_rebalance_date.month) or trading_days_since >= 20
        elif frequency == "quarterly":
            calendar_days = (current_date - last_rebalance_date).days
            return (current_date.year != last_rebalance_date.year or
                   (current_date.month - 1) // 3 != (last_rebalance_date.month - 1) // 3) or trading_days_since >= 60
        elif frequency == "yearly":
            return current_date.year != last_rebalance_date.year
        
        return False
    
    @staticmethod
    def get_contribution_dates(
        start_date: datetime,
        end_date: datetime,
        frequency: str,
        amount: float
    ) -> Dict[pd.Timestamp, float]:
        """
        Get dates when recurring contributions should be made.
        Uses trading days to align with rebalancing schedule.
        
        Args:
            start_date: Start of period
            end_date: End of period
            frequency: 'weekly', 'monthly'
            amount: Contribution amount
            
        Returns:
            Dictionary mapping trading dates to contribution amounts
        """
        import pandas as pd
        
        contributions = {}
        
        # Create a date range of trading days
        trading_days = pd.bdate_range(start=start_date, end=end_date)
        
        if frequency == "weekly":
            # Find first Monday (or first trading day if Monday not available)
            current = start_date
            while current <= end_date:
                # Find next Monday (or first trading day of week)
                days_until_monday = (7 - current.weekday()) % 7
                if days_until_monday == 0 and current.weekday() != 0:
                    days_until_monday = 7
                next_date = current + timedelta(days=days_until_monday)
                
                # Find closest trading day
                available_days = trading_days[trading_days >= pd.Timestamp(next_date)]
                if len(available_days) > 0:
                    contribution_date = available_days[0]
                    if contribution_date <= pd.Timestamp(end_date):
                        contributions[contribution_date] = amount
                    current = contribution_date + timedelta(days=1)
                else:
                    break
                    
        elif frequency == "monthly":
            # First trading day of each month
            current = start_date
            while current <= end_date:
                # First day of current month
                first_of_month = current.replace(day=1)
                # Find first trading day of that month
                available_days = trading_days[trading_days >= pd.Timestamp(first_of_month)]
                if len(available_days) > 0:
                    contribution_date = available_days[0]
                    if contribution_date <= pd.Timestamp(end_date) and contribution_date not in contributions:
                        contributions[contribution_date] = amount
                
                # Move to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1, day=1)
                else:
                    current = current.replace(month=current.month + 1, day=1)
                    
        elif frequency == "daily":
            # Every trading day
            for day in trading_days:
                contributions[day] = amount
        
        return contributions


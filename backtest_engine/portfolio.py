"""
Portfolio management for backtesting.
Tracks positions, cash, and portfolio value over time.
"""
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents a position in a single asset."""
    ticker: str
    shares: float
    avg_cost: float
    entry_date: datetime
    
    @property
    def cost_basis(self) -> float:
        """Total cost basis for this position."""
        return self.shares * self.avg_cost
    
    def add_shares(self, shares: float, price: float):
        """Add shares to position (updates average cost)."""
        total_cost = self.cost_basis + (shares * price)
        self.shares += shares
        if self.shares > 0:
            self.avg_cost = total_cost / self.shares
    
    def remove_shares(self, shares: float) -> float:
        """Remove shares from position. Returns cost basis of removed shares."""
        if shares > self.shares:
            shares = self.shares
        
        cost_basis_removed = shares * self.avg_cost
        self.shares -= shares
        return cost_basis_removed


@dataclass
class Trade:
    """Represents a completed trade."""
    ticker: str
    date: datetime
    action: str  # 'BUY' or 'SELL'
    shares: float
    price: float
    value: float
    reason: Optional[str] = None
    commission: float = 0.0


@dataclass
class PortfolioState:
    """Snapshot of portfolio state at a point in time."""
    date: datetime
    cash: float
    positions: Dict[str, Position]
    total_value: float
    equity_curve: float  # Cumulative return %
    
    def get_position_value(self, ticker: str, current_price: float) -> float:
        """Get current value of a position."""
        if ticker not in self.positions:
            return 0.0
        return self.positions[ticker].shares * current_price


class Portfolio:
    """Manages portfolio state during backtesting."""
    
    def __init__(self, initial_cash: float = 10000.0):
        """Initialize portfolio with starting cash."""
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_states: List[PortfolioState] = []
        self.price_data: Dict[str, pd.DataFrame] = {}
    
    def set_price_data(self, ticker: str, price_df: pd.DataFrame):
        """Set price data for a ticker."""
        self.price_data[ticker] = price_df
    
    def get_price(self, ticker: str, date: datetime) -> Optional[float]:
        """Get adjusted close price for a ticker on a given date."""
        if ticker not in self.price_data:
            return None
        
        df = self.price_data[ticker]
        if df.empty:
            return None
        
        date_pd = pd.to_datetime(date)
        
        # Normalize timezone - remove timezone info for comparison
        if df.index.tz is not None:
            df_index = df.index.tz_localize(None)
        else:
            df_index = df.index
        
        # Normalize input date (remove time, keep just date)
        date_pd_normalized = pd.to_datetime(date_pd.date())
        
        # Find closest available date (forward fill)
        available_dates = df_index[df_index <= date_pd_normalized]
        if len(available_dates) == 0:
            return None
        
        closest_date = available_dates[-1]
        # Use original index if it has timezone
        if df.index.tz is not None:
            closest_date_original = df.index[df_index <= date_pd_normalized][-1]
        else:
            closest_date_original = closest_date
        
        price = df.loc[closest_date_original, 'adj_close']
        return float(price) if price is not None and not pd.isna(price) else None
    
    def buy(
        self, 
        ticker: str, 
        date: datetime, 
        amount: float, 
        price: Optional[float] = None,
        reason: Optional[str] = None,
        allow_fractional: bool = True
    ) -> bool:
        """
        Buy shares of a ticker using available cash.
        
        Args:
            ticker: Ticker symbol
            date: Trade date
            amount: Dollar amount to invest (or None for all cash)
            price: Price per share (if None, uses current market price)
            reason: Reason for trade
            allow_fractional: Allow fractional shares
            
        Returns:
            True if trade executed, False otherwise
        """
        if price is None:
            price = self.get_price(ticker, date)
            if price is None or price <= 0:
                logger.warning(f"No price data for {ticker} on {date}")
                return False
        
        if amount is None:
            amount = self.cash
        
        if amount <= 0 or self.cash < amount:
            return False
        
        shares = amount / price
        if not allow_fractional:
            shares = int(shares)
            amount = shares * price
        
        if shares <= 0:
            return False
        
        # Execute trade
        self.cash -= amount
        
        if ticker in self.positions:
            self.positions[ticker].add_shares(shares, price)
        else:
            self.positions[ticker] = Position(
                ticker=ticker,
                shares=shares,
                avg_cost=price,
                entry_date=date
            )
        
        trade = Trade(
            ticker=ticker,
            date=date,
            action='BUY',
            shares=shares,
            price=price,
            value=amount,
            reason=reason
        )
        self.trades.append(trade)
        
        logger.debug(f"Bought {shares:.4f} shares of {ticker} at ${price:.2f} on {date}")
        return True
    
    def sell(
        self, 
        ticker: str, 
        date: datetime, 
        shares: Optional[float] = None,
        amount: Optional[float] = None,
        price: Optional[float] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Sell shares of a ticker.
        
        Args:
            ticker: Ticker symbol
            date: Trade date
            shares: Number of shares to sell (or None to sell all)
            amount: Dollar amount to sell (alternative to shares)
            price: Price per share (if None, uses current market price)
            reason: Reason for trade
            
        Returns:
            True if trade executed, False otherwise
        """
        if ticker not in self.positions or self.positions[ticker].shares <= 0:
            return False
        
        if price is None:
            price = self.get_price(ticker, date)
            if price is None or price <= 0:
                logger.warning(f"No price data for {ticker} on {date}")
                return False
        
        position = self.positions[ticker]
        
        if shares is None:
            if amount is not None:
                shares = amount / price
            else:
                shares = position.shares
        
        if shares > position.shares:
            shares = position.shares
        
        if shares <= 0:
            return False
        
        # Execute trade
        proceeds = shares * price
        cost_basis = position.remove_shares(shares)
        profit = proceeds - cost_basis
        
        self.cash += proceeds
        
        # Remove position if fully sold
        if position.shares <= 0.0001:  # Small threshold for floating point
            del self.positions[ticker]
        
        trade = Trade(
            ticker=ticker,
            date=date,
            action='SELL',
            shares=shares,
            price=price,
            value=proceeds,
            reason=reason
        )
        self.trades.append(trade)
        
        logger.debug(f"Sold {shares:.4f} shares of {ticker} at ${price:.2f} on {date} (profit: ${profit:.2f})")
        return True
    
    def get_total_value(self, date: datetime) -> float:
        """Calculate total portfolio value (cash + positions) on a given date."""
        total = self.cash
        
        for ticker, position in self.positions.items():
            price = self.get_price(ticker, date)
            if price is not None:
                total += position.shares * price
        
        return total
    
    def snapshot(self, date: datetime):
        """Take a snapshot of portfolio state."""
        total_value = self.get_total_value(date)
        equity_curve = ((total_value - self.initial_cash) / self.initial_cash) * 100
        
        state = PortfolioState(
            date=date,
            cash=self.cash,
            positions=self.positions.copy(),
            total_value=total_value,
            equity_curve=equity_curve
        )
        self.daily_states.append(state)
    
    def get_equity_curve(self) -> pd.DataFrame:
        """Get equity curve as DataFrame."""
        if not self.daily_states:
            return pd.DataFrame()
        
        data = {
            'date': [s.date for s in self.daily_states],
            'total_value': [s.total_value for s in self.daily_states],
            'cash': [s.cash for s in self.daily_states],
            'equity_curve_pct': [s.equity_curve for s in self.daily_states]
        }
        
        df = pd.DataFrame(data)
        df.set_index('date', inplace=True)
        return df
    
    def get_trades_df(self) -> pd.DataFrame:
        """Get trades as DataFrame."""
        if not self.trades:
            return pd.DataFrame()
        
        data = {
            'date': [t.date for t in self.trades],
            'ticker': [t.ticker for t in self.trades],
            'action': [t.action for t in self.trades],
            'shares': [t.shares for t in self.trades],
            'price': [t.price for t in self.trades],
            'value': [t.value for t in self.trades],
            'reason': [t.reason for t in self.trades]
        }
        
        df = pd.DataFrame(data)
        return df


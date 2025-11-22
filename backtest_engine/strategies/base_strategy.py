"""
Base strategy class that all strategies inherit from.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize strategy with configuration."""
        self.config = config
        self.name = config.get('name', 'unknown')
        self.universe = config.get('universe', [])
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.start_date = None
        self.end_date = None
        self.last_trade_dates: Dict[str, datetime] = {}  # For cooldown tracking
    
    def initialize(self, price_data: Dict[str, pd.DataFrame], start_date: str, end_date: str):
        """Initialize strategy with price data and date range."""
        self.price_data = price_data
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.last_trade_dates = {}
    
    def get_assets(self) -> List[str]:
        """Get list of assets in strategy universe."""
        return self.universe
    
    @abstractmethod
    def generate_signals(self, current_date: datetime, should_rebalance: bool = False) -> List[Dict[str, Any]]:
        """
        Generate trading signals for the current date.
        
        Args:
            current_date: Current simulation date
            should_rebalance: Whether rebalancing should occur
            
        Returns:
            List of signal dictionaries with keys: ticker, action, amount, shares, reason
        """
        pass
    
    def get_price(self, ticker: str, date: datetime) -> Optional[float]:
        """Get adjusted close price for a ticker on a date."""
        if ticker not in self.price_data:
            return None
        
        df = self.price_data[ticker]
        date_pd = pd.to_datetime(date)
        
        # Find closest available date
        available_dates = df.index[df.index <= date_pd]
        if len(available_dates) == 0:
            return None
        
        closest_date = available_dates[-1]
        return df.loc[closest_date, 'adj_close']
    
    def get_returns(self, ticker: str, date: datetime, lookback_days: int) -> Optional[float]:
        """Calculate return over lookback period."""
        if ticker not in self.price_data:
            return None
        
        df = self.price_data[ticker]
        date_pd = pd.to_datetime(date)
        
        # Find current price
        current_price = self.get_price(ticker, date)
        if current_price is None:
            return None
        
        # Find lookback date
        lookback_date = date_pd - pd.Timedelta(days=lookback_days)
        lookback_price = self.get_price(ticker, lookback_date.to_pydatetime())
        
        if lookback_price is None or lookback_price == 0:
            return None
        
        return ((current_price - lookback_price) / lookback_price) * 100
    
    def calculate_rsi(self, ticker: str, date: datetime, period: int = 14) -> Optional[float]:
        """Calculate RSI for a ticker."""
        if ticker not in self.price_data:
            return None
        
        df = self.price_data[ticker]
        date_pd = pd.to_datetime(date)
        
        # Get historical data up to current date
        available_data = df[df.index <= date_pd].tail(period + 1)
        
        if len(available_data) < period + 1:
            return None
        
        # Calculate price changes
        deltas = available_data['adj_close'].diff()
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)
        
        avg_gain = gains.rolling(window=period).mean().iloc[-1]
        avg_loss = losses.rolling(window=period).mean().iloc[-1]
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_sma(self, ticker: str, date: datetime, window: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if ticker not in self.price_data:
            return None
        
        df = self.price_data[ticker]
        date_pd = pd.to_datetime(date)
        
        available_data = df[df.index <= date_pd].tail(window)
        
        if len(available_data) < window:
            return None
        
        return available_data['adj_close'].mean()
    
    def is_in_cooldown(self, ticker: str, current_date: datetime, cooldown_days: int) -> bool:
        """Check if a ticker is in cooldown period."""
        if ticker not in self.last_trade_dates:
            return False
        
        last_trade = self.last_trade_dates[ticker]
        days_since = (current_date - last_trade).days
        return days_since < cooldown_days
    
    def record_trade(self, ticker: str, date: datetime):
        """Record that a trade occurred for cooldown tracking."""
        self.last_trade_dates[ticker] = date


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
        
        # Validate data availability
        self._validate_data_availability()
    
    def _validate_data_availability(self):
        """Validate that sufficient price data exists for strategy calculations."""
        if not self.price_data:
            logger.warning("No price data provided to strategy")
            return
        
        # Check if strategy needs lookback period
        lookback_days = 0
        if hasattr(self, 'lookback_days'):
            lookback_days = self.lookback_days
        elif hasattr(self, 'config') and 'parameters' in self.config:
            lookback_days = self.config['parameters'].get('lookback_days', 0)
        
        if lookback_days > 0:
            # Check each ticker has sufficient data
            for ticker, df in self.price_data.items():
                if df.empty:
                    logger.warning(f"Strategy validation: {ticker} has no price data")
                    continue
                
                # Normalize timezone for comparison
                earliest_date = df.index.min()
                if earliest_date.tz is not None:
                    earliest_date = earliest_date.tz_localize(None)
                
                required_start = self.start_date - pd.Timedelta(days=lookback_days + 5)  # +5 for buffer
                if required_start.tz is not None:
                    required_start = required_start.tz_localize(None)
                
                if earliest_date > required_start:
                    days_missing = (required_start - earliest_date).days
                    logger.warning(f"Strategy validation: {ticker} may have insufficient data. "
                                 f"Earliest date: {earliest_date.date()}, "
                                 f"need data from: {required_start.date()} "
                                 f"({days_missing} days missing)")
                else:
                    logger.debug(f"Strategy validation: {ticker} has sufficient data "
                               f"(earliest: {earliest_date.date()}, need: {required_start.date()})")
    
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
            logger.debug(f"get_price: No price data for {ticker}")
            return None
        
        df = self.price_data[ticker]
        if df.empty:
            logger.debug(f"get_price: Empty DataFrame for {ticker}")
            return None
        
        date_pd = pd.to_datetime(date)
        
        # Normalize timezone - remove timezone info for comparison
        if df.index.tz is not None:
            df_index = df.index.tz_localize(None)
        else:
            df_index = df.index
        
        # Normalize input date (remove time, keep just date)
        date_pd_normalized = pd.to_datetime(date_pd.date())
        
        # Find closest available date
        available_dates = df_index[df_index <= date_pd_normalized]
        if len(available_dates) == 0:
            logger.debug(f"get_price: No dates <= {date_pd_normalized} for {ticker}. "
                        f"Earliest: {df_index.min()}, Latest: {df_index.max()}")
            return None
        
        closest_date = available_dates[-1]
        # Use original index if it has timezone
        if df.index.tz is not None:
            closest_date_original = df.index[df_index <= date_pd_normalized][-1]
        else:
            closest_date_original = closest_date
        
        price = df.loc[closest_date_original, 'adj_close']
        if price is not None and not pd.isna(price):
            logger.debug(f"get_price: {ticker} on {date_pd_normalized.date()} -> {closest_date_original.date()} = ${price:.2f}")
        else:
            logger.debug(f"get_price: {ticker} on {date_pd_normalized.date()} -> {closest_date_original.date()} = None/NaN")
        return float(price) if price is not None and not pd.isna(price) else None
    
    def get_returns(self, ticker: str, date: datetime, lookback_days: int) -> Optional[float]:
        """
        Calculate return over lookback period.
        Uses closest available trading days if exact dates don't exist.
        """
        if ticker not in self.price_data:
            logger.warning(f"get_returns: No price data for {ticker}")
            return None
        
        df = self.price_data[ticker]
        date_pd = pd.to_datetime(date)
        
        # Find current price (uses closest available date <= current_date)
        current_price = self.get_price(ticker, date)
        if current_price is None:
            logger.debug(f"get_returns: No current price for {ticker} on {date}")
            return None
        
        # Find lookback date - use closest available trading day
        lookback_date_target = date_pd - pd.Timedelta(days=lookback_days)
        
        # Get all available dates up to the target lookback date
        available_dates = df.index[df.index <= lookback_date_target]
        
        if len(available_dates) == 0:
            # No data before lookback date - try using earliest available date
            earliest_date = df.index.min()
            if earliest_date < date_pd:
                # Use earliest available date as lookback
                lookback_price = df.loc[earliest_date, 'adj_close']
                actual_lookback_days = (date_pd - earliest_date).days
                if actual_lookback_days < lookback_days * 0.5:  # Less than 50% of requested
                    logger.warning(f"get_returns: {ticker} - insufficient data. "
                                 f"Using earliest date {earliest_date.date()} "
                                 f"(only {actual_lookback_days} days vs {lookback_days} requested)")
            else:
                logger.warning(f"get_returns: {ticker} - no data before {date_pd.date()}. "
                             f"Earliest: {earliest_date.date()}")
                return None
        else:
            # Use closest available date to target lookback date
            lookback_date = available_dates[-1]
            lookback_price = df.loc[lookback_date, 'adj_close']
            actual_lookback_days = (date_pd - lookback_date).days
            # Only log if significantly different from target
            if abs(actual_lookback_days - lookback_days) > 2:
                logger.debug(f"get_returns: {ticker} - using {lookback_date.date()} "
                           f"({actual_lookback_days} days vs {lookback_days} target)")
        
        if lookback_price is None or lookback_price == 0:
            logger.warning(f"get_returns: Invalid lookback price for {ticker} (price: {lookback_price})")
            return None
        
        # Calculate return
        return_pct = ((current_price - lookback_price) / lookback_price) * 100
        return return_pct
    
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


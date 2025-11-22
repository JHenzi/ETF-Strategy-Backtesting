"""
Main backtesting engine.
Orchestrates strategy execution, portfolio management, and order execution.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from .portfolio import Portfolio
from .execution import ExecutionModel, RebalanceScheduler
from .metrics import MetricsCalculator

# Import data fetcher - adjust path as needed
try:
    from data.fetcher import DataFetcher
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data.fetcher import DataFetcher

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Main backtesting engine that runs strategies."""
    
    def __init__(self, data_fetcher: DataFetcher):
        """Initialize the backtesting engine."""
        self.data_fetcher = data_fetcher
        self.portfolio = None
        self.execution_model = None
        self.rebalance_scheduler = RebalanceScheduler()
    
    def run_backtest(
        self,
        strategy: Any,  # Strategy object
        start_date: str,
        end_date: str,
        initial_cash: float = 10000.0,
        recurring_contribution: Optional[Dict[str, Any]] = None,
        execution_when: str = "next_open"
    ) -> Dict[str, Any]:
        """
        Run a backtest with the given strategy.
        
        Args:
            strategy: Strategy object with generate_signals method
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_cash: Starting cash
            recurring_contribution: Dict with 'amount' and 'frequency'
            execution_when: When to execute orders
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Initialize portfolio
        self.portfolio = Portfolio(initial_cash=initial_cash)
        self.execution_model = ExecutionModel(execution_when=execution_when)
        
        # Validate and fetch data for all assets
        assets = strategy.get_assets()
        logger.info(f"Validating {len(assets)} tickers: {assets}")
        
        # Validate all tickers first
        valid, invalid = self.data_fetcher.validate_tickers(assets)
        if invalid:
            raise ValueError(f"Invalid tickers: {', '.join(invalid)}. Please validate tickers before running backtest.")
        
        logger.info(f"All {len(valid)} tickers validated successfully")
        
        # Fetch price data
        price_data = {}
        for ticker in valid:
            try:
                df = self.data_fetcher.fetch_ticker_data(ticker, start_date, end_date)
                if df.empty:
                    raise ValueError(f"No data for {ticker}")
                price_data[ticker] = df
                self.portfolio.set_price_data(ticker, df)
                logger.info(f"Fetched {len(df)} days of data for {ticker}")
            except Exception as e:
                logger.error(f"Failed to fetch data for {ticker}: {e}")
                raise
        
        # Get date range
        all_dates = set()
        for df in price_data.values():
            all_dates.update(df.index)
        date_range = sorted([d for d in all_dates if pd.to_datetime(start_date) <= d <= pd.to_datetime(end_date)])
        
        if not date_range:
            raise ValueError("No valid dates in range")
        
        # Handle recurring contributions
        contribution_dates = {}
        if recurring_contribution:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            contribution_dates = self.rebalance_scheduler.get_contribution_dates(
                start_dt, end_dt,
                recurring_contribution.get('frequency', 'weekly'),
                recurring_contribution.get('amount', 0)
            )
        
        # Initialize strategy
        strategy.initialize(price_data, start_date, end_date)
        
        last_rebalance_date = None
        last_trade_date = None
        first_day = True
        
        # Main simulation loop
        for idx, current_date in enumerate(date_range):
            current_date_dt = pd.to_datetime(current_date).to_pydatetime()
            is_first_day = (idx == 0)
            
            # Add recurring contribution
            if current_date in contribution_dates:
                amount = contribution_dates[current_date]
                self.portfolio.cash += amount
                logger.debug(f"Added ${amount:.2f} contribution on {current_date}")
            
            # Check if rebalancing is needed
            should_rebalance = False
            rebalance_freq = getattr(strategy, 'rebalance_frequency', None) or strategy.config.get('rebalance_frequency')
            if rebalance_freq:
                should_rebalance = self.rebalance_scheduler.should_rebalance(
                    current_date_dt, last_rebalance_date, rebalance_freq
                )
                # Always rebalance on first day if strategy has rebalance_frequency
                if is_first_day and rebalance_freq:
                    should_rebalance = True
            
            # Generate signals from strategy
            signals = strategy.generate_signals(current_date_dt, should_rebalance)
            
            if signals:
                logger.info(f"Generated {len(signals)} signals on {current_date} (rebalance: {should_rebalance})")
            
            # Process signals into orders
            for signal in signals:
                order = self._signal_to_order(signal, current_date_dt)
                if order:
                    self.execution_model.place_order(order)
            
            # Execute pending orders immediately for rebalancing strategies
            # or based on execution_when setting
            executable = self.execution_model.get_executable_orders(
                current_date_dt, last_trade_date, is_first_day=is_first_day
            )
            
            # If we have signals and should_rebalance, execute immediately (same day)
            # This ensures rebalancing strategies execute trades on rebalance days
            if signals and should_rebalance:
                # For rebalancing, execute orders immediately (same day execution)
                if not executable and self.execution_model.pending_orders:
                    executable = self.execution_model.pending_orders.copy()
                    logger.info(f"Force executing {len(executable)} rebalancing orders on {current_date}")
            
            if executable:
                logger.info(f"Executing {len(executable)} orders on {current_date}")
            
            # For buy orders with amount=None, split cash equally across all pending buy orders
            pending_buys = [o for o in executable if o.action == 'BUY' and o.amount is None]
            if pending_buys:
                if len(pending_buys) > 1:
                    # Split cash equally across all buy orders
                    cash_per_order = self.portfolio.cash / len(pending_buys)
                    for order in pending_buys:
                        order.amount = cash_per_order
                    logger.debug(f"Splitting ${self.portfolio.cash:.2f} across {len(pending_buys)} buy orders")
                else:
                    # Single buy order, use all cash
                    pending_buys[0].amount = self.portfolio.cash
            
            for order in executable:
                if order.action == 'BUY':
                    price = self.portfolio.get_price(order.ticker, current_date_dt)
                    if price:
                        amount = order.amount if order.amount else self.portfolio.cash
                        if amount > 0:
                            self.portfolio.buy(
                                order.ticker, current_date_dt, amount, price,
                                reason=order.reason, allow_fractional=True
                            )
                            last_trade_date = current_date_dt
                elif order.action == 'SELL':
                    price = self.portfolio.get_price(order.ticker, current_date_dt)
                    if price:
                        shares = order.shares
                        if shares:
                            self.portfolio.sell(
                                order.ticker, current_date_dt, shares, price=price,
                                reason=order.reason
                            )
                            last_trade_date = current_date_dt
            
            self.execution_model.clear_executed_orders(executable)
            
            if should_rebalance:
                last_rebalance_date = current_date_dt
            
            # Take daily snapshot
            self.portfolio.snapshot(current_date_dt)
        
        # Calculate metrics
        equity_curve = self.portfolio.get_equity_curve()
        trades = self.portfolio.get_trades_df()
        
        if equity_curve.empty:
            raise ValueError("No equity curve data generated")
        
        metrics_calc = MetricsCalculator(equity_curve, trades)
        metrics = metrics_calc.calculate_all_metrics()
        
        # Prepare results
        results = {
            'equity_curve': equity_curve,
            'trades': trades,
            'metrics': metrics,
            'portfolio': self.portfolio,
            'rolling_metrics_30': metrics_calc.get_rolling_metrics(30),
            'rolling_metrics_60': metrics_calc.get_rolling_metrics(60),
            'rolling_metrics_90': metrics_calc.get_rolling_metrics(90),
            'underwater_plot': metrics_calc.get_underwater_plot(),
            'start_date': start_date,
            'end_date': end_date,
            'initial_cash': initial_cash
        }
        
        logger.info(f"Backtest completed. Final value: ${self.portfolio.get_total_value(date_range[-1]):.2f}")
        return results
    
    def _signal_to_order(self, signal: Dict[str, Any], date: datetime) -> Optional[Any]:
        """Convert a strategy signal to an order."""
        from .execution import Order
        
        ticker = signal.get('ticker')
        action = signal.get('action')
        amount = signal.get('amount')
        shares = signal.get('shares')
        reason = signal.get('reason')
        
        if not ticker or not action:
            return None
        
        return Order(
            ticker=ticker,
            action=action,
            amount=amount,
            shares=shares,
            reason=reason
        )
    
    def validate_strategy(self, strategy: Any, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Validate a strategy before running (dry run).
        
        Returns:
            Dict with validation results and any errors
        """
        errors = []
        warnings = []
        
        # Check assets
        try:
            assets = strategy.get_assets()
            if not assets:
                errors.append("Strategy has no assets defined")
            
            # Validate tickers
            valid, invalid = self.data_fetcher.validate_tickers(assets)
            if invalid:
                errors.append(f"Invalid tickers: {', '.join(invalid)}")
            
            # Check data availability
            for ticker in valid:
                try:
                    df = self.data_fetcher.fetch_ticker_data(ticker, start_date, end_date)
                    if df.empty:
                        warnings.append(f"No data available for {ticker} in date range")
                except Exception as e:
                    errors.append(f"Failed to fetch data for {ticker}: {str(e)}")
        
        except Exception as e:
            errors.append(f"Strategy validation error: {str(e)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


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
        
        # Fetch data for all assets
        assets = strategy.get_assets()
        price_data = {}
        for ticker in assets:
            try:
                df = self.data_fetcher.fetch_ticker_data(ticker, start_date, end_date)
                if df.empty:
                    raise ValueError(f"No data for {ticker}")
                price_data[ticker] = df
                self.portfolio.set_price_data(ticker, df)
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
        
        # Main simulation loop
        for current_date in date_range:
            current_date_dt = pd.to_datetime(current_date).to_pydatetime()
            
            # Add recurring contribution
            if current_date in contribution_dates:
                amount = contribution_dates[current_date]
                self.portfolio.cash += amount
                logger.debug(f"Added ${amount:.2f} contribution on {current_date}")
            
            # Check if rebalancing is needed
            should_rebalance = False
            if hasattr(strategy, 'rebalance_frequency'):
                should_rebalance = self.rebalance_scheduler.should_rebalance(
                    current_date_dt, last_rebalance_date, strategy.rebalance_frequency
                )
            
            # Generate signals from strategy
            signals = strategy.generate_signals(current_date, should_rebalance)
            
            # Process signals into orders
            for signal in signals:
                order = self._signal_to_order(signal, current_date_dt)
                if order:
                    self.execution_model.place_order(order)
            
            # Execute pending orders
            executable = self.execution_model.get_executable_orders(
                current_date_dt, last_trade_date
            )
            
            for order in executable:
                if order.action == 'BUY':
                    price = self.portfolio.get_price(order.ticker, current_date_dt)
                    if price:
                        amount = order.amount if order.amount else self.portfolio.cash
                        self.portfolio.buy(
                            order.ticker, current_date_dt, amount, price,
                            reason=order.reason, allow_fractional=True
                        )
                        last_trade_date = current_date_dt
                elif order.action == 'SELL':
                    price = self.portfolio.get_price(order.ticker, current_date_dt)
                    if price:
                        shares = order.shares
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


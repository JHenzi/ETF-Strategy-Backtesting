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
        
        # Get date range (intersection of all assets' trading days)
        all_dates = set()
        for ticker, df in price_data.items():
            ticker_dates = set(df.index)
            all_dates.update(ticker_dates)
            logger.debug(f"{ticker}: {len(ticker_dates)} trading days available")
        
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        date_range = sorted([d for d in all_dates if start_dt <= d <= end_dt])
        
        if not date_range:
            raise ValueError(f"No valid trading days in range {start_date} to {end_date}")
        
        logger.info(f"Date range: {date_range[0]} to {date_range[-1]} ({len(date_range)} trading days)")
        
        # Warn if date range is very short
        if len(date_range) < 10:
            logger.warning(f"Very short date range: only {len(date_range)} trading days. "
                         f"Results may not be meaningful.")
        
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
        
        # Initialize strategy (validates data availability)
        strategy.initialize(price_data, start_date, end_date)
        logger.info(f"Strategy '{strategy.name}' initialized with {len(price_data)} assets")
        
        last_rebalance_date = None
        last_trade_date = None
        trading_days_since_rebalance = 0
        
        # Main simulation loop - iterate through each TRADING DAY
        for idx, current_date in enumerate(date_range):
            current_date_dt = pd.to_datetime(current_date).to_pydatetime()
            current_date_ts = pd.Timestamp(current_date)  # For contribution_dates lookup
            is_first_day = (idx == 0)
            
            # Increment trading days counter
            if last_rebalance_date:
                trading_days_since_rebalance += 1
            
            # Check if rebalancing is needed (using trading days)
            should_rebalance = False
            rebalance_freq = getattr(strategy, 'rebalance_frequency', None) or strategy.config.get('rebalance_frequency')
            if rebalance_freq:
                should_rebalance = self.rebalance_scheduler.should_rebalance(
                    current_date_dt, last_rebalance_date, rebalance_freq, trading_days_since_rebalance
                )
                # Always rebalance on first day if strategy has rebalance_frequency
                if is_first_day and rebalance_freq:
                    should_rebalance = True
                    trading_days_since_rebalance = 0
            
            # Add recurring contribution BEFORE rebalancing (so it's available for investment)
            # Check both Timestamp and datetime formats for contribution dates
            contribution_added = False
            for contrib_date, contrib_amount in contribution_dates.items():
                if (pd.Timestamp(contrib_date).date() == current_date_dt.date() or 
                    pd.Timestamp(contrib_date) == current_date_ts):
                    self.portfolio.cash += contrib_amount
                    logger.info(f"Added ${contrib_amount:.2f} recurring contribution on {current_date} (cash now: ${self.portfolio.cash:.2f})")
                    contribution_added = True
                    break
            
            # Generate signals from strategy
            signals = strategy.generate_signals(current_date_dt, should_rebalance)
            
            if signals:
                logger.info(f"[{current_date}] Rebalance: {should_rebalance}, Generated {len(signals)} signals")
            
            # Process signals into orders
            orders_placed = 0
            for signal in signals:
                order = self._signal_to_order(signal, current_date_dt)
                if order:
                    self.execution_model.place_order(order)
                    orders_placed += 1
            
            # For rebalancing strategies, execute orders SAME DAY
            # For "next_open", we still execute same day if it's a rebalance day
            executable = []
            if should_rebalance and signals:
                # Rebalancing: execute immediately on same day
                executable = self.execution_model.pending_orders.copy()
                logger.info(f"[{current_date}] Rebalance day - executing {len(executable)} orders immediately")
            else:
                # Normal execution based on execution_when
                executable = self.execution_model.get_executable_orders(
                    current_date_dt, last_trade_date, is_first_day=is_first_day
                )
            
            if executable:
                logger.info(f"[{current_date}] Executing {len(executable)} orders")
            
            # For buy orders with amount=None, split cash equally across all pending buy orders
            # This ensures we divide total cash by number of stocks/ETFs
            pending_buys = [o for o in executable if o.action == 'BUY' and o.amount is None]
            if pending_buys:
                # Always split cash equally across all buy orders (even if just one)
                # This ensures consistent allocation
                cash_per_order = self.portfolio.cash / len(pending_buys)
                for order in pending_buys:
                    order.amount = cash_per_order
                logger.info(f"Splitting ${self.portfolio.cash:.2f} across {len(pending_buys)} buy orders (${cash_per_order:.2f} each)")
            
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
                        # If shares is None, sell all shares of this ticker
                        if order.shares is None:
                            # Get current position
                            if order.ticker in self.portfolio.positions:
                                position = self.portfolio.positions[order.ticker]
                                shares_to_sell = position.shares
                                if shares_to_sell > 0:
                                    self.portfolio.sell(
                                        order.ticker, current_date_dt, shares_to_sell, price=price,
                                        reason=order.reason
                                    )
                                    last_trade_date = current_date_dt
                                    logger.info(f"Sold all {shares_to_sell:.4f} shares of {order.ticker} at ${price:.2f}")
                        else:
                            shares = order.shares
                            if shares and shares > 0:
                                self.portfolio.sell(
                                    order.ticker, current_date_dt, shares, price=price,
                                    reason=order.reason
                                )
                                last_trade_date = current_date_dt
            
            self.execution_model.clear_executed_orders(executable)
            
            # Sync strategy's position tracking with actual portfolio
            if hasattr(strategy, 'current_positions'):
                # Update strategy's current_positions to match portfolio
                strategy.current_positions = set(self.portfolio.positions.keys())
            
            if should_rebalance:
                last_rebalance_date = current_date_dt
                trading_days_since_rebalance = 0
                total_value = self.portfolio.get_total_value(current_date_dt)
                positions_summary = {t: f"{p.shares:.2f} @ ${p.avg_cost:.2f}" 
                                   for t, p in self.portfolio.positions.items()}
                logger.info(f"[{current_date}] Rebalance completed. Value: ${total_value:.2f}, Cash: ${self.portfolio.cash:.2f}, Positions: {positions_summary}")
            
            # Take daily snapshot (track portfolio value every day)
            self.portfolio.snapshot(current_date_dt)
            
            # Log portfolio state periodically
            if idx % 20 == 0 or executable:
                total_value = self.portfolio.get_total_value(current_date_dt)
                logger.debug(f"[{current_date}] Portfolio: ${total_value:.2f} (Cash: ${self.portfolio.cash:.2f}, Positions: {len(self.portfolio.positions)})")
        
        # Calculate metrics
        equity_curve = self.portfolio.get_equity_curve()
        trades = self.portfolio.get_trades_df()
        
        if equity_curve.empty:
            raise ValueError("No equity curve data generated")
        
        logger.info(f"Calculating metrics: {len(equity_curve)} equity curve points, {len(trades)} trades")
        
        metrics_calc = MetricsCalculator(equity_curve, trades)
        metrics = metrics_calc.calculate_all_metrics()
        
        logger.info(f"Metrics calculated: total_return={metrics.get('total_return', 0):.2f}%, "
                   f"total_trades={metrics.get('total_trades', 0)}")
        
        # Calculate QQQ baseline comparison
        logger.info("Fetching QQQ baseline data...")
        qqq_data = self.data_fetcher.fetch_ticker_data('QQQ', start_date, end_date)
        if not qqq_data.empty and 'adj_close' in qqq_data.columns:
            # Calculate QQQ equity curve (buy and hold with same initial cash)
            qqq_initial_price = qqq_data['adj_close'].iloc[0]
            qqq_shares = initial_cash / qqq_initial_price
            qqq_equity_curve = pd.DataFrame({
                'date': qqq_data.index,
                'total_value': qqq_data['adj_close'] * qqq_shares
            })
            qqq_equity_curve.set_index('date', inplace=True)
            
            # Calculate QQQ metrics
            qqq_metrics_calc = MetricsCalculator(qqq_equity_curve, pd.DataFrame())  # No trades for buy-and-hold
            qqq_metrics = qqq_metrics_calc.calculate_all_metrics()
            
            # Calculate relative performance
            strategy_return = metrics.get('total_return', 0)
            qqq_return = qqq_metrics.get('total_return', 0)
            relative_return = strategy_return - qqq_return
            
            metrics['qqq_baseline_return'] = qqq_return
            metrics['qqq_baseline_cagr'] = qqq_metrics.get('cagr', 0)
            metrics['relative_return'] = relative_return
            metrics['beat_qqq'] = relative_return > 0
            
            logger.info(f"QQQ baseline: {qqq_return:.2f}% return, Strategy: {strategy_return:.2f}% return, "
                       f"Relative: {relative_return:.2f}%")
        else:
            logger.warning("Could not fetch QQQ data for baseline comparison")
            qqq_equity_curve = pd.DataFrame()
            qqq_metrics = {}
        
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
            'qqq_equity_curve': qqq_equity_curve,
            'qqq_metrics': qqq_metrics,
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


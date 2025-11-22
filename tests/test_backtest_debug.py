"""
Debug test to identify why backtests return zero values.
Tests the engine directly and traces execution flow.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta
import logging

from data.fetcher import DataFetcher
from backtest_engine.engine import BacktestEngine
from backtest_engine.strategies.strategy_factory import StrategyFactory
from backtest_engine.portfolio import Portfolio

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BacktestDebugger:
    """Debug class to trace backtest execution and identify issues."""
    
    def __init__(self):
        self.data_fetcher = DataFetcher()
        self.engine = BacktestEngine(self.data_fetcher)
        self.factory = StrategyFactory()
    
    def test_data_fetch(self, tickers, start_date, end_date):
        """Test 1: Verify data can be fetched."""
        print("\n" + "="*80)
        print("TEST 1: Data Fetching")
        print("="*80)
        
        results = {}
        for ticker in tickers:
            try:
                df = self.data_fetcher.fetch_ticker_data(ticker, start_date, end_date)
                results[ticker] = {
                    'success': True,
                    'rows': len(df),
                    'date_range': (df.index.min(), df.index.max()) if not df.empty else None,
                    'columns': list(df.columns) if not df.empty else []
                }
                print(f"✅ {ticker}: {len(df)} rows, range: {df.index.min()} to {df.index.max()}")
            except Exception as e:
                results[ticker] = {'success': False, 'error': str(e)}
                print(f"❌ {ticker}: {e}")
        
        return results
    
    def test_strategy_creation(self, yaml_str):
        """Test 2: Verify strategy can be created."""
        print("\n" + "="*80)
        print("TEST 2: Strategy Creation")
        print("="*80)
        
        try:
            strategy = self.factory.create_strategy(yaml_string=yaml_str)
            print(f"✅ Strategy created: {strategy.name}")
            print(f"   Universe: {strategy.universe}")
            print(f"   Config: {strategy.config}")
            return strategy
        except Exception as e:
            print(f"❌ Strategy creation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_signal_generation(self, strategy, price_data, test_date):
        """Test 3: Verify signals are generated."""
        print("\n" + "="*80)
        print("TEST 3: Signal Generation")
        print("="*80)
        
        strategy.initialize(price_data, '2023-01-01', '2023-12-31')
        test_date_dt = pd.to_datetime(test_date).to_pydatetime()
        
        # Debug: Check DataFrame structure
        print("\n--- DataFrame Structure Check ---")
        for ticker in strategy.universe[:1]:  # Check first ticker only
            if ticker in price_data:
                df = price_data[ticker]
                print(f"{ticker} DataFrame:")
                print(f"  Index type: {type(df.index)}")
                print(f"  Index sample: {df.index[:3].tolist()}")
                print(f"  Columns: {list(df.columns)}")
                print(f"  Shape: {df.shape}")
                print(f"  Sample data:")
                print(df.head(3))
                break
        
        # Test return calculation for each ticker
        print("\n--- Testing Return Calculations ---")
        if hasattr(strategy, 'lookback_days'):
            lookback = strategy.lookback_days
        else:
            lookback = strategy.config.get('parameters', {}).get('lookback_days', 20)
        
        for ticker in strategy.universe:
            if ticker in price_data:
                returns = strategy.get_returns(ticker, test_date_dt, lookback)
                current_price = strategy.get_price(ticker, test_date_dt)
                print(f"{ticker}:")
                print(f"  Current price: ${current_price:.2f}" if current_price else "  Current price: None")
                print(f"  Returns ({lookback}d): {returns:.2f}%" if returns is not None else "  Returns: None")
            else:
                print(f"{ticker}: No price data")
        
        # Test signal generation
        print("\n--- Testing Signal Generation ---")
        signals = strategy.generate_signals(test_date_dt, should_rebalance=True)
        print(f"Generated {len(signals)} signals:")
        for signal in signals:
            print(f"  {signal}")
        
        return signals
    
    def test_portfolio_execution(self, strategy, price_data, start_date, end_date, initial_cash=10000):
        """Test 4: Test full portfolio execution."""
        print("\n" + "="*80)
        print("TEST 4: Portfolio Execution")
        print("="*80)
        
        # Create portfolio manually to trace
        portfolio = Portfolio(initial_cash=initial_cash)
        
        # Set price data
        for ticker, df in price_data.items():
            portfolio.set_price_data(ticker, df)
        
        # Get a sample date
        sample_date = pd.to_datetime(start_date) + pd.Timedelta(days=30)
        sample_date_dt = sample_date.to_pydatetime()
        
        print(f"\nTesting on date: {sample_date_dt}")
        print(f"Initial cash: ${portfolio.cash:.2f}")
        
        # Test buying
        test_ticker = strategy.universe[0]
        price = portfolio.get_price(test_ticker, sample_date_dt)
        print(f"\nTest buy: {test_ticker} at ${price if price else 'None'}")
        
        if price:
            success = portfolio.buy(test_ticker, sample_date_dt, 1000, price, reason="Test buy")
            print(f"Buy successful: {success}")
            print(f"Cash after buy: ${portfolio.cash:.2f}")
            print(f"Positions: {list(portfolio.positions.keys())}")
            if test_ticker in portfolio.positions:
                pos = portfolio.positions[test_ticker]
                print(f"  {test_ticker}: {pos.shares:.4f} shares @ ${pos.avg_cost:.2f}")
        
        # Test portfolio value
        total_value = portfolio.get_total_value(sample_date_dt)
        print(f"\nTotal portfolio value: ${total_value:.2f}")
        
        # Test snapshot
        portfolio.snapshot(sample_date_dt)
        print(f"Snapshots taken: {len(portfolio.daily_states)}")
        
        return portfolio
    
    def test_full_backtest(self, yaml_str, start_date, end_date, initial_cash=10000):
        """Test 5: Run full backtest and trace execution."""
        print("\n" + "="*80)
        print("TEST 5: Full Backtest Execution")
        print("="*80)
        
        try:
            # Create strategy
            strategy = self.factory.create_strategy(yaml_string=yaml_str)
            print(f"✅ Strategy: {strategy.name}")
            
            # Run backtest
            print(f"\nRunning backtest: {start_date} to {end_date}")
            results = self.engine.run_backtest(
                strategy=strategy,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash,
                execution_when='next_open'
            )
            
            # Analyze results
            print("\n" + "-"*80)
            print("RESULTS ANALYSIS")
            print("-"*80)
            
            equity_curve = results.get('equity_curve', pd.DataFrame())
            trades = results.get('trades', pd.DataFrame())
            metrics = results.get('metrics', {})
            
            print(f"\nEquity Curve:")
            print(f"  Rows: {len(equity_curve)}")
            if not equity_curve.empty:
                print(f"  Date range: {equity_curve.index.min()} to {equity_curve.index.max()}")
                print(f"  First value: ${equity_curve['total_value'].iloc[0]:.2f}")
                print(f"  Last value: ${equity_curve['total_value'].iloc[-1]:.2f}")
                print(f"  Sample rows:")
                print(equity_curve.head(5).to_string())
            
            print(f"\nTrades:")
            print(f"  Total trades: {len(trades)}")
            if not trades.empty:
                print(f"  Trade types: {trades['action'].value_counts().to_dict()}")
                print(f"  Sample trades:")
                print(trades.head(10).to_string())
            
            print(f"\nMetrics:")
            for key, value in metrics.items():
                print(f"  {key}: {value}")
            
            # Check for zeros
            print(f"\n⚠️  ZERO CHECK:")
            zero_metrics = [k for k, v in metrics.items() if v == 0]
            if zero_metrics:
                print(f"  Zero metrics: {zero_metrics}")
            else:
                print("  ✅ No zero metrics!")
            
            if len(trades) == 0:
                print("  ⚠️  WARNING: No trades executed!")
            
            if equity_curve.empty:
                print("  ⚠️  WARNING: Empty equity curve!")
            elif equity_curve['total_value'].iloc[-1] == equity_curve['total_value'].iloc[0]:
                print("  ⚠️  WARNING: Portfolio value didn't change!")
            
            return results
            
        except Exception as e:
            print(f"\n❌ Backtest failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_all_tests(self, yaml_str, tickers, start_date, end_date):
        """Run all diagnostic tests."""
        print("\n" + "="*80)
        print("BACKTEST DEBUGGING SUITE")
        print("="*80)
        print(f"Strategy YAML:\n{yaml_str}")
        print(f"\nTickers: {tickers}")
        print(f"Date Range: {start_date} to {end_date}")
        
        # Test 1: Data fetch
        data_results = self.test_data_fetch(tickers, start_date, end_date)
        
        # Check if data fetch succeeded
        failed_tickers = [t for t, r in data_results.items() if not r.get('success')]
        if failed_tickers:
            print(f"\n❌ Cannot proceed - data fetch failed for: {failed_tickers}")
            return
        
        # Test 2: Strategy creation
        strategy = self.test_strategy_creation(yaml_str)
        if not strategy:
            print("\n❌ Cannot proceed - strategy creation failed")
            return
        
        # Fetch price data
        price_data = {}
        for ticker in tickers:
            df = self.data_fetcher.fetch_ticker_data(ticker, start_date, end_date)
            price_data[ticker] = df
        
        # Test 3: Signal generation
        test_date = pd.to_datetime(start_date) + pd.Timedelta(days=30)
        signals = self.test_signal_generation(strategy, price_data, test_date)
        
        if len(signals) == 0:
            print("\n⚠️  WARNING: No signals generated! This is likely the problem.")
        
        # Test 4: Portfolio execution
        portfolio = self.test_portfolio_execution(strategy, price_data, start_date, end_date)
        
        # Test 5: Full backtest
        results = self.test_full_backtest(yaml_str, start_date, end_date)
        
        print("\n" + "="*80)
        print("DEBUGGING COMPLETE")
        print("="*80)


if __name__ == '__main__':
    # Test configuration
    yaml_str = """
name: laggard_rotation
universe:
  - XLP
  - XLY
  - XLK
  - XLE
  - XLF
parameters:
  lookback_days: 20
  laggard_count: 1
  cooldown_days: 30
rebalance_frequency: weekly
position_sizing: equal_weight
execution: next_open
"""
    
    tickers = ['XLP', 'XLY', 'XLK', 'XLE', 'XLF']
    start_date = '2023-01-01'
    end_date = '2023-12-31'
    
    debugger = BacktestDebugger()
    debugger.run_all_tests(yaml_str, tickers, start_date, end_date)


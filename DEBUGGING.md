# Debugging Guide: Zero Results Issue

## Problem

Backtests are returning all-zero metrics:
```json
{
  "total_trades": 0,
  "total_return": 0,
  "cagr": 0,
  ...
}
```

This indicates trades are not being executed or portfolio is not being tracked.

## Diagnostic Steps

### 1. Check Logs for Signal Generation

Look for this log message:
```
INFO:backtest_engine.engine:[2023-01-01] Rebalance: True, Generated 2 signals
```

**If missing**: Strategy is not generating signals. Check:
- Is `rebalance_frequency` set in YAML?
- Is the date range long enough for rebalancing?
- Are there enough trading days in the range?

### 2. Check Logs for Order Execution

Look for:
```
INFO:backtest_engine.engine:[2023-01-01] Executing 2 orders
INFO:backtest_engine.portfolio:Bought 10.5000 shares of XLP at $75.23
```

**If missing**: Orders are not being executed. Check:
- Execution timing logic (should execute same-day for rebalancing)
- Price data availability for execution date
- Cash availability in portfolio

### 3. Check Portfolio State

Look for:
```
INFO:backtest_engine.engine:[2023-01-01] Rebalance completed. Value: $10050.00, Cash: $0.00, Positions: {'XLP': '10.50 @ $75.23'}
```

**If missing or value doesn't change**: Portfolio is not being updated. Check:
- Are trades actually completing?
- Is `portfolio.snapshot()` being called?
- Is equity curve being populated?

### 4. Verify Data Flow

Run this test in Python:
```python
from data.fetcher import DataFetcher
from backtest_engine.engine import BacktestEngine
from backtest_engine.strategies.strategy_factory import StrategyFactory

# Test data fetch
fetcher = DataFetcher()
df = fetcher.fetch_ticker_data('XLP', '2023-01-01', '2023-12-31')
print(f"Data points: {len(df)}")
print(f"Date range: {df.index.min()} to {df.index.max()}")

# Test strategy
factory = StrategyFactory()
strategy = factory.create_strategy(yaml_string="""
name: laggard_rotation
universe: [XLP, XLY, XLK]
parameters:
  lookback_days: 20
  laggard_count: 1
rebalance_frequency: weekly
""")

# Test signal generation
strategy.initialize({'XLP': df, 'XLY': df, 'XLK': df}, '2023-01-01', '2023-12-31')
signals = strategy.generate_signals(pd.to_datetime('2023-01-15'), should_rebalance=True)
print(f"Signals generated: {len(signals)}")
```

### 5. Check Database

Query the database directly:
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/backtests.db')

# Check runs
runs = pd.read_sql("SELECT * FROM runs", conn)
print(f"Total runs: {len(runs)}")

# Check trades for latest run
if len(runs) > 0:
    latest_run = runs.iloc[-1]['run_id']
    trades = pd.read_sql(f"SELECT * FROM trades WHERE run_id = {latest_run}", conn)
    print(f"Trades: {len(trades)}")
    print(trades.head())
    
    equity = pd.read_sql(f"SELECT * FROM equity_curve WHERE run_id = {latest_run}", conn)
    print(f"Equity curve points: {len(equity)}")
    print(equity.head())

conn.close()
```

## Common Fixes

### Fix 1: Ensure Rebalancing Triggers

Add this to `engine.py` before signal generation:
```python
if should_rebalance:
    logger.info(f"REBALANCE TRIGGERED on {current_date}")
    logger.info(f"Last rebalance: {last_rebalance_date}")
    logger.info(f"Trading days since: {trading_days_since_rebalance}")
```

### Fix 2: Force Same-Day Execution

Modify execution logic to always execute on rebalance days:
```python
# In engine.py, after placing orders
if should_rebalance:
    # Force immediate execution for rebalancing
    executable = self.execution_model.pending_orders.copy()
    logger.info(f"FORCING execution of {len(executable)} orders on rebalance day")
```

### Fix 3: Verify Portfolio Updates

Add logging to portfolio methods:
```python
# In portfolio.py buy() method
logger.info(f"BUY: {ticker}, amount: ${amount}, price: ${price}, shares: {shares}")
logger.info(f"Portfolio after buy: cash=${self.cash}, positions={list(self.positions.keys())}")
```

### Fix 4: Check Date Range

Ensure date range has valid trading days:
```python
# In engine.py
print(f"Date range: {date_range[0]} to {date_range[-1]}")
print(f"Total trading days: {len(date_range)}")
```

## Expected Log Output

A working backtest should produce logs like:

```
INFO:backtest_engine.engine:Starting backtest from 2023-01-01 to 2023-12-31
INFO:backtest_engine.engine:Validating 3 tickers: ['XLP', 'XLY', 'XLK']
INFO:backtest_engine.engine:All 3 tickers validated successfully
INFO:backtest_engine.engine:Fetched 252 days of data for XLP
INFO:backtest_engine.engine:[2023-01-03] Rebalance: True, Generated 1 signals
INFO:backtest_engine.engine:[2023-01-03] Rebalance day - executing 1 orders immediately
INFO:backtest_engine.engine:[2023-01-03] Executing 1 orders
INFO:backtest_engine.portfolio:Bought 133.3333 shares of XLP at $75.00
INFO:backtest_engine.engine:[2023-01-03] Rebalance completed. Value: $10000.00, Cash: $0.00, Positions: {'XLP': '133.33 @ $75.00'}
...
INFO:backtest_engine.engine:[2023-01-09] Rebalance: True, Generated 2 signals
INFO:backtest_engine.engine:[2023-01-09] Rebalance day - executing 2 orders immediately
INFO:backtest_engine.portfolio:Sold 133.3333 shares of XLP at $76.00
INFO:backtest_engine.portfolio:Bought 131.5789 shares of XLY at $76.50
INFO:backtest_engine.engine:[2023-01-09] Rebalance completed. Value: $10066.67, Cash: $0.00, Positions: {'XLY': '131.58 @ $76.50'}
...
INFO:backtest_engine.engine:Backtest completed. Final value: $10500.00
```

## Next Steps

If logs show signals but no execution:
1. Check execution model logic
2. Verify price data exists for execution dates
3. Check cash availability

If logs show execution but no portfolio updates:
1. Check portfolio.buy() and portfolio.sell() methods
2. Verify trades are being recorded
3. Check snapshot() is being called

If everything looks correct but still zeros:
1. Check metrics calculation
2. Verify equity curve has data
3. Check data types in persistence layer


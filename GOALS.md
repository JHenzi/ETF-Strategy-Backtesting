## Mission

Build a flexible, local-first Python backtesting and analysis suite for ETFs and stocks that lets a single user define, run, compare, and visualize trading strategies. The system should ship with a set of common baseline strategies (Buy & Hold, DCA, Momentum, Lagging Sector, etc.), accept user-editable YAML strategies, cache market data from free sources, and present results in an interactive Flask + Tailwind + Plotly dashboard. All completed backtest runs must be saved for later comparison.

## Core Principles

- **Local-first**: Runs on a user's machine; easy to install and run. Optional notes how it could be lifted into SaaS.
    
- **Flexible strategy definitions**: Default pre-coded strategies plus editable YAML representation with schema validation.
    
- **Reproducible backtests**: Deterministic execution given the same inputs and data cache.
    
- **Extensible data layer**: Start with Yahoo Finance via `yfinance`, with robust per-ticker caching to SQLite.
    
- **Usability & analysis**: Rich visualizations (equity curves, drawdowns, metrics) and side-by-side strategy comparisons.
    

## Success Criteria (Definition of DONE)

A user can:

- Select an asset universe of ETFs/stocks (mixing both) and choose one of the out-of-the-box strategies or provide a YAML strategy.
    
- Run a backtest over a chosen date range and capital schedule (lump-sum or recurring deposits).
    
- View the equity curve, key metrics (CAGR, Sharpe, Sortino, max drawdown, win rate, volatility, time-in-negative, etc.), trades list and a timeline of trades.
    
- Compare two completed runs with overlaid return % curves and a table of differences and identify a winner.
    
- Persist all completed runs into the local SQLite store for future recall.
    

## Non-Goals (initial release)

- Live order execution or brokerage integration.
    
- Precise modeling of commissions, taxes, or micro-slippage (these can be added later).
    
- Multitenant SaaS scaling. The product is single-user by design.

---

## Current Problem: Zero Results in Backtests

### Problem Description

When running backtests (particularly rebalancing strategies like `laggard_rotation`), the system returns all-zero metrics:
- `total_trades: 0`
- `total_return: 0`
- `cagr: 0`
- All other metrics: 0

This indicates that **trades are not being executed** or **portfolio state is not being tracked** during the simulation.

### Expected Behavior

The backtesting engine should:

1. **Day-by-Day Simulation**: Iterate through each trading day in the date range
2. **Rebalancing Logic**: On rebalance days (e.g., weekly), determine which assets to buy/sell
3. **Trade Execution**: Execute buy/sell orders immediately on rebalance days
4. **Portfolio Tracking**: Update portfolio value daily (cash + positions)
5. **Baseline Comparison**: Track QQQ (or another benchmark) for relative performance
6. **Metrics Calculation**: Compute performance metrics from the equity curve

### Root Cause Analysis

Possible issues:

1. **Orders Not Executing**: Orders are generated but not executed due to execution timing logic
2. **Portfolio Not Updating**: Trades execute but portfolio value isn't calculated correctly
3. **Equity Curve Empty**: Daily snapshots aren't being taken or saved
4. **Date Range Issues**: Trading days aren't being identified correctly
5. **Price Data Missing**: Can't get prices for execution dates
6. **Strategy Logic**: Strategy isn't generating signals on rebalance days

### Root Cause Identified (from logs)

**The Actual Problem**: `get_returns()` method is failing for all tickers, returning `None`.

**Evidence from logs**:
```
WARNING:backtest_engine.strategies.builtin.laggard_rotation:Could not calculate returns for XLP
WARNING:backtest_engine.strategies.builtin.laggard_rotation:Could not calculate returns for XLY
...
WARNING:backtest_engine.strategies.builtin.laggard_rotation:No asset returns calculated - cannot generate signals
```

**Why this happens**:
1. Strategy tries to calculate returns over `lookback_days` (e.g., 20 days)
2. `get_returns()` looks for price at `current_date - lookback_days`
3. If that date doesn't exist in price data (weekend, holiday, or before start date), it returns `None`
4. Without returns, no signals can be generated
5. No signals = no trades = zero results

### Solution Plan (Prioritized)

#### ✅ Phase 1: Fix Return Calculation (CRITICAL - Blocks Everything)

**Problem**: `get_returns()` fails when lookback date doesn't exist in price data.

**Solution**: Make return calculation robust:
1. **Use available data**: If exact lookback date doesn't exist, find closest earlier date
2. **Handle edge cases**: 
   - If current_date is before lookback_days from start, use earliest available data
   - If no historical data exists, skip that ticker with clear warning
3. **Add validation**: Check data availability before attempting calculation
4. **Better error messages**: Log why calculation failed (no data, date out of range, etc.)

**Implementation Steps**:
```python
# In base_strategy.py get_returns() method:
1. Find closest available date <= (current_date - lookback_days)
2. If no date found, try using earliest available date
3. If still no data, return None with detailed log message
4. Calculate return using available dates (even if not exactly lookback_days)
```

**Files to modify**:
- `backtest_engine/strategies/base_strategy.py` - Fix `get_returns()` method
- Add helper method `_find_closest_date()` to find nearest available trading day

**Status**: ✅ **COMPLETED**
- ✅ Fixed `get_returns()` to use closest available trading day
- ✅ Added fallback to earliest available date if lookback date not found
- ✅ Added smart logging (warnings only when data is significantly insufficient)
- ✅ Added data availability validation in `initialize()`
- ✅ Optimized logging verbosity (debug level for normal operations)

**Success Criteria**:
- ✅ Returns calculated successfully for all tickers with sufficient data
- ✅ Clear warnings when data is insufficient
- ✅ Strategy generates signals on rebalance days

#### Phase 2: Data Availability Validation

**Problem**: No upfront check that sufficient historical data exists for return calculations.

**Solution**: Validate data availability during strategy initialization:
1. Check that price data exists for at least `lookback_days` before first rebalance
2. Warn user if data is insufficient
3. Suggest adjusting `lookback_days` or date range

**Implementation**:
- Add `validate_data_availability()` method to BaseStrategy
- Call during strategy initialization
- Log warnings for insufficient data

**Status**: ✅ **COMPLETED**
- ✅ Added `_validate_data_availability()` method
- ✅ Called automatically during `initialize()`
- ✅ Checks for sufficient data based on lookback_days
- ✅ Logs warnings when data is insufficient

#### Phase 3: Improve Execution Model

**Problem**: Complex execution timing may still cause issues.

**Solution**: For rebalancing strategies, always execute same-day:
- ✅ Already implemented - verify it's working correctly
- Add test to ensure orders execute on rebalance days

#### Phase 4: Add Comprehensive Logging

**Problem**: Need better visibility into what's happening.

**Solution**: Enhanced logging (partially done, expand):
- ✅ Rebalance triggers - DONE
- ✅ Signal generation - DONE  
- ✅ Return calculation - DONE (with detailed debug logging)
- ✅ Data availability checks - DONE
- ✅ Price lookup details - DONE (in get_returns)
- ⚠️ Add: Date range validation warnings

#### Phase 5: Baseline Comparison Integration

**Problem**: No benchmark comparison (QQQ).

**Solution**: Always fetch QQQ and calculate relative performance:
- Add QQQ to required data fetch
- Calculate QQQ equity curve in parallel
- Include in results and metrics
- Show comparison charts

**Implementation**:
- Modify `engine.run_backtest()` to always fetch QQQ
- Calculate QQQ metrics alongside strategy metrics
- Add QQQ equity curve to results
- Update UI to show comparison

#### Phase 6: Test Suite

**Problem**: No automated tests to catch regressions.

**Solution**: Create test suite:
- Test return calculation with various scenarios
- Test rebalancing logic
- Test trade execution
- Test metrics calculation
- Test with real data samples

### Immediate Action Items

1. ✅ **Fix `get_returns()` method** (Phase 1) - **COMPLETED** - Now handles missing dates gracefully
2. ✅ **Add data validation** (Phase 2) - **COMPLETED** - Validates data availability on init
3. ⚠️ **Test with real date ranges** - Use 2023-2024 data, not future dates (needs testing)
4. ⚠️ **Verify buy_and_hold works** - Ensure basic engine functionality (needs testing)
5. ⚠️ **Add QQQ baseline** (Phase 5) - Critical for meaningful results (next priority)

### Progress Summary

**Completed**:
- ✅ Phase 1: Fixed `get_returns()` to use closest available trading days
- ✅ Phase 2: Added data availability validation
- ✅ Phase 4: Enhanced logging for return calculations and data validation
- ✅ Added date range validation and warnings
- ✅ Phase 5: QQQ baseline comparison implemented in engine
- ✅ Beautiful results page with charts and metrics
- ✅ Fixed strategies to be accumulation-only (no selling)
- ✅ Added recurring reinvestment support

**In Progress**:
- ⚠️ QQQ chart display on results page (data saved but chart not rendering correctly)
- ⚠️ Recurring reinvestment UI integration (backend ready, UI needs testing)

**Next Steps**:
1. ✅ Test the fixes with laggard_rotation strategy - **DONE**
2. ✅ Verify trades are now executing - **DONE**
3. ✅ Implement QQQ baseline comparison - **DONE**
4. ⚠️ Fix QQQ chart rendering on results page
5. ⚠️ Test recurring reinvestment feature end-to-end
6. ⚠️ Add comprehensive test suite

### Debugging Checklist

When backtest returns zeros, check in this order:

1. **Return Calculation** (Most Common Issue):
   - [ ] Check logs for "Could not calculate returns" warnings
   - [ ] Verify price data exists for lookback period
   - [ ] Check if date range starts before first rebalance + lookback_days
   - [ ] Verify `get_returns()` is finding price data correctly

2. **Signal Generation**:
   - [ ] Are signals being generated? (Check logs for "Generated X signals")
   - [ ] If no signals, check why (no returns calculated, all in cooldown, etc.)

3. **Order Execution**:
   - [ ] Are orders being placed? (Check logs for order placement)
   - [ ] Are orders being executed? (Check logs for "Executing X orders")
   - [ ] Is execution happening on rebalance days? (Check "Rebalance day - executing")

4. **Portfolio Updates**:
   - [ ] Is portfolio cash being used? (Check logs for portfolio cash changes)
   - [ ] Are positions being created? (Check logs for "Bought X shares")
   - [ ] Is portfolio value changing? (Check "Portfolio value: $X" logs)

5. **Data & Dates**:
   - [ ] Is price data available? (Verify data fetcher returns data)
   - [ ] Are dates valid trading days? (Check date_range has valid dates)
   - [ ] Are daily snapshots being taken? (Check equity_curve has data)

### Implementation Priority

**CRITICAL (Fix First)**:
1. Fix `get_returns()` to handle missing dates gracefully
2. Add data availability validation
3. Test with realistic date ranges (past dates, not future)

**HIGH PRIORITY**:
4. Verify execution model works for rebalancing
5. Add QQQ baseline comparison
6. Improve error messages and logging

**MEDIUM PRIORITY**:
7. Add test suite
8. Enhance UI with better error display
9. Add data quality checks

### Success Criteria

A working backtest should show:
- ✅ `total_trades > 0`
- ✅ `total_return != 0` (unless market was flat)
- ✅ Equity curve with multiple data points
- ✅ Portfolio value changing over time
- ✅ Trades recorded in trades table
- ✅ Comparison metrics vs QQQ baseline

### Baseline Comparison Requirement

**Critical Feature**: All backtests must be compared against QQQ (or a user-selected benchmark).

**Why**: Without a baseline, we can't determine if a strategy is actually good. A 10% return might sound good, but if QQQ returned 15% in the same period, the strategy underperformed.

**Implementation Requirements**:
1. Always fetch QQQ data alongside strategy assets
2. Calculate QQQ performance in parallel with strategy
3. Include QQQ metrics in results (CAGR, Sharpe, etc.)
4. Calculate relative performance (strategy return - QQQ return)
5. Display QQQ equity curve alongside strategy curve
6. Show "Did strategy beat QQQ?" indicator

**Current Status**: ✅ **IMPLEMENTED** - QQQ baseline is calculated and saved, but chart display needs fixing.

**Implementation Details**:
- ✅ Engine fetches QQQ data and calculates buy-and-hold performance
- ✅ QQQ metrics saved to database (CAGR, Sharpe, return, etc.)
- ✅ Relative performance calculated (strategy return - QQQ return)
- ✅ QQQ equity curve saved in metadata
- ⚠️ **TODO**: Fix QQQ chart rendering on results page (data exists but chart not showing QQQ line)
- ⚠️ **TODO**: Ensure QQQ comparison metrics display correctly in UI
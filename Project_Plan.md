## High-level Epics

- **Epic 1 — Data Layer**: Ingest, cache, and serve historical OHLCV data.
    
- **Epic 2 — Core Backtesting Engine**: Strategy runner, order/execution model, portfolio accounting, metrics calculator.
    
- **Epic 3 — Strategy Configuration**: YAML schema, validator, set of built-in strategies.
    
- **Epic 4 — Persistence & Results Store**: Save completed runs, results blobs, and metadata to SQLite.
    
- **Epic 5 — Flask UI**: Asset selector, strategy runner UI, result visualizer and comparison UI.
    
- **Epic 6 — Live Mode & Alerts**: Daily price fetch, simulated live portfolio, alerts page.
    
- **Epic 7 — Documentation & Agent Artifacts**: Goals.md, Project Plan, Workflow, examples, README, sample strategies.
    

## Features & Stories (by Epic)

### Epic 1 — Data Layer

- Feature: Yahoo Finance ingestion using `yfinance`.
    
    - Task: Implement per-ticker caching to SQLite (OHLCV + adj close + last fetch timestamp).
        
    - Task: Fetch wrapper that checks cache for requested date-range and only downloads missing ranges.
        
    - Task: Robust ticker validation and error messages when an indicator in YAML references a ticker that has no data.
        
    - Task: Export cached time series to CSV for debugging.
        

### Epic 2 — Core Backtesting Engine

- Feature: Deterministic portfolio simulation.
    
    - Task: Build order model with fractional shares (dollar-based buys) and next-day `execution` option.
        
    - Task: Implement fully-invested cash handling (buy when signal; hold cash otherwise).
        
    - Task: Implement recurring contribution schedule handling (weekly, monthly) and lump-sum.
        
    - Task: Ignore commissions/slippage by default (configurable later).
        
    - Task: Trade ledger + trade-level metadata (entry, exit, size, price, reason).

    - Task: Backtesting engine should have test classes for strategy YAML files (i.e. before running, engine should validate/dry run and give the user feedback)
        
- Feature: Metrics engine.
    
    - Task: Implement annualized return, CAGR, Sharpe, Sortino, max drawdown, volatility, win rate, profit factor, time-in-negative, underwater plot
        
    - Task: Rolling metrics (30/60/90 day) generator.
        

### Epic 3 — Strategy Configuration

- Feature: YAML strategy parser & schema validator.
    
    - Task: Define YAML schema (see example below) and implement validation (raise clear errors on unsupported indicators).
        
    - Task: Implement built-in strategies as YAML or Python implementations that can be exported to YAML.
        
    - Task: Provide CLI / UI to import custom YAML strategies.
        
- Feature: Built-in strategies (out of the box):
    
    - Buy & Hold (per asset / equal-weight portfolio)
        
    - DCA (weekly/monthly recurring contribution)
        
    - Momentum Rotation (rank by lookback return)
        
    - Lagging Sector Buy (buy N lowest performers subject to cooldown)
        
    - Mix (buy winners and losers allocation)
        

### Epic 4 — Persistence & Results Store

- Feature: Save completed runs.
    
    - Task: Design SQLite schema: runs table, run\_metadata (JSON), strategy\_yaml, trades table, timeseries (cached in separate table or file), metrics table.
        
    - Task: UI endpoints to list, load, delete runs.
        

### Epic 5 — Flask UI

- Feature: Backtest Runner UX
    
    - Task: Asset universe selector with type tags (ETF, Stock).
        
    - Task: Strategy selector and YAML editor.
        
    - Task: Parameters: start/end date, initial cash, recurring deposit schedule, rebalance frequency.
        
- Feature: Results Dashboard
    
    - Task: Equity curve (Plotly) and overlaid comparisons.
        
    - Task: Metrics table, downloadable CSV of trades and results.
        
    - Task: Trades timeline, underwater plot, rolling metric charts.
        
    - Task: Strategy comparison view (overlay, differences table, pick winner button).
        

### Epic 6 — Live Mode & Alerts

- Feature: Daily price update worker
    
    - Task: Implement a daily cron-like job (user-run script or scheduled OS cron) to fetch prices and update cache.
        
    - Task: Live strategy runner that simulates trades daily and stores simulated portfolio states.
        
    - Task: Alerts page showing recommended buys/sells from strategy logic (simulation only).
        

### Epic 7 — Docs & Agent Artifacts

- Feature: Developer and user docs, examples, and sample strategies.
    
    - Task: Create `examples/` with sample YAML files and `notebooks/` demonstrating backtests.
        
    - Task: Create README with quickstart and install instructions.
        

## Minimal Viable Scope (MVS) for initial release

- ✅ Data ingestion + per-ticker caching (yfinance) - **COMPLETE**
- ✅ Core backtesting engine supporting fractional shares, recurring contributions, fully-invested logic, and trade ledger - **COMPLETE**
- ✅ YAML schema + 5 built-in strategies: Buy & Hold, DCA, Momentum Winner, Laggard Rotation, Mixed Winners/Losers - **COMPLETE** (exceeded MVS)
- ✅ Flask UI: run a backtest, show equity curve, metrics table, trades list, and compare two runs - **COMPLETE**
- ✅ Persist completed runs to SQLite and be able to load them - **COMPLETE**

**Status**: ✅ **MVS EXCEEDED** - All core features implemented plus additional enhancements (Strategy Builder, QQQ comparison, ticker validation, etc.)

---

## Recent Accomplishments (November 2025)

### ✅ Completed Features

**Epic 1 — Data Layer** ✅ COMPLETE
- ✅ Yahoo Finance ingestion with SQLite caching
- ✅ Per-ticker caching with date range checking
- ✅ Ticker validation endpoint
- ✅ CSV export capability (in fetcher)

**Epic 2 — Core Backtesting Engine** ✅ COMPLETE
- ✅ Portfolio simulation with fractional shares
- ✅ Order execution model (next_open, first_day_only, same_day, market_close)
- ✅ Recurring contribution handling (weekly, monthly)
- ✅ Trade ledger with metadata
- ✅ Strategy validation/dry-run before execution
- ✅ Comprehensive metrics calculator (CAGR, Sharpe, Sortino, max drawdown, win rate, volatility, profit factor, time-in-negative)
- ✅ Rolling metrics (30/60/90 day windows)
- ✅ Underwater plot data generation
- ✅ Fixed execution timing bugs (first_day_only, next_open)
- ✅ Fixed cash splitting for multiple buy orders

**Epic 3 — Strategy Configuration** 🟡 PARTIALLY COMPLETE
- ✅ YAML schema validator with clear error messages
- ✅ Strategy factory for loading strategies
- ✅ Built-in strategies implemented (5/10):
  - ✅ Buy & Hold
  - ✅ DCA (Dollar Cost Averaging)
  - ✅ Laggard Rotation (with accumulation logic)
  - ✅ Momentum Winner (with accumulation logic)
  - ✅ Mixed Winners/Losers (with accumulation logic)
- ✅ Sample YAML files in examples/sample_strategies/
- ⏳ **TODO**: Additional strategies to implement (5 remaining):
  - ⏳ RSI Mean Reversion
  - ⏳ SMA Crossover
  - ⏳ Relative Strength vs Benchmark
  - ⏳ Buy the Dip
  - ⏳ Equal Weight Rebalance

**Epic 4 — Persistence & Results Store** ✅ COMPLETE
- ✅ SQLite schema: runs, metrics, trades, equity_curve, run_metadata
- ✅ Save/load/delete runs
- ✅ Fixed type conversion issues (pandas Timestamps, numpy types → SQLite compatible)
- ✅ Fixed DataFrame JSON serialization

**Epic 5 — Flask UI** ✅ COMPLETE
- ✅ Backtest runner UI with YAML editor
- ✅ Strategy file selector dropdown (loads from examples/sample_strategies/)
- ✅ **NEW**: Strategy Builder UI with type-ahead ticker search and validation
- ✅ Strategy validation UI
- ✅ Results list view with QQQ beat indicators (chips/badges)
- ✅ Detailed results view with interactive Plotly charts
- ✅ Run comparison view with conditional highlighting and overall winner
- ✅ Job status tracking with progress bars
- ✅ API endpoints for all operations
- ✅ Equity curve visualization with QQQ overlay (Plotly)
- ✅ Drawdown charts
- ✅ Trades table with pagination
- ✅ Metric comparison with plain English labels and explanations
- ⚠️ **TODO**: Downloadable CSV exports (LOW PRIORITY)
- ⚠️ **TODO**: Rolling metrics charts (LOW PRIORITY)

**Epic 7 — Documentation** ✅ COMPLETE
- ✅ README with quickstart
- ✅ Sample strategy YAML files
- ✅ Project structure documentation

### 🐛 Bugs Fixed

1. **Race condition in job initialization** - Fixed job dictionary initialization before thread start
2. **SQLite type binding errors** - Added type conversion for pandas/numpy types
3. **DataFrame JSON serialization** - Fixed DataFrame to dict conversion in API responses
4. **Order execution timing** - Fixed first_day_only and next_open execution modes
5. **Cash splitting** - Fixed equal-weight allocation across multiple buy orders
6. **Date comparison** - Fixed datetime comparison in buy_and_hold strategy
7. **Zero results bug** - Fixed execution logic, rebalance timing, and position tracking
8. **QQQ chart alignment** - Fixed date format normalization for proper overlay
9. **QQQ calculation** - Fixed to simulate QQQ with same investment pattern as strategy
10. **Ticker validation** - Fixed to properly cache and validate tickers with company names
11. **API path issues** - Fixed to work with NGINX subdirectory routing (/back prefix)

---

## Future Enhancements

### High Priority

**Epic 3 — Additional Strategies** (5 remaining from Predefined Strategies.md)
- [ ] **RSI Mean Reversion Strategy** - Buy oversold assets (RSI < 30), sell overbought (RSI > 70)
  - Requires: RSI calculation function, oversold/overbought thresholds
  - Implementation: `backtest_engine/strategies/builtin/rsi_mean_reversion.py`
  - YAML example: `examples/sample_strategies/rsi_mean_reversion.yaml`
- [ ] **SMA Crossover Strategy** - Trend-following: buy when short SMA > long SMA
  - Requires: SMA calculation, crossover detection logic
  - Implementation: `backtest_engine/strategies/builtin/sma_crossover.py`
  - YAML example: `examples/sample_strategies/sma_crossover.yaml`
- [ ] **Relative Strength vs Benchmark** - Buy assets outperforming benchmark (e.g., SPY)
  - Requires: Benchmark comparison logic, relative return calculation
  - Implementation: `backtest_engine/strategies/builtin/relative_strength.py`
  - YAML example: `examples/sample_strategies/relative_strength.yaml`
- [ ] **Buy the Dip Strategy** - Deploy cash when markets fall by large % (e.g., -10%)
  - Requires: Drawdown calculation, threshold-based signals
  - Implementation: `backtest_engine/strategies/builtin/buy_the_dip.py`
  - YAML example: `examples/sample_strategies/buy_the_dip.yaml`
- [ ] **Equal Weight Rebalance Strategy** - Maintain equal weights across all assets on schedule
  - Requires: Rebalancing logic to sell/buy to restore equal weights
  - Implementation: `backtest_engine/strategies/builtin/equal_weight_rebalance.py`
  - YAML example: `examples/sample_strategies/equal_weight_rebalance.yaml`

**Epic 5 — UI Enhancements (Remaining)**
- [ ] Rolling metrics charts (30/60/90 day windows)
- [ ] Friendlier backtesting result names needed
- [ ] ~~CSV export for trades and equity curve~~
- [ ] Enhanced comparison view with side-by-side charts (already has overlay)
- [ ] PDF export for results

### Medium Priority

**Epic 2 — Engine Enhancements**
- [ ] Commission/slippage modeling (configurable)
- [ ] More sophisticated position sizing options
- [ ] Stop-loss and take-profit support
- [ ] Portfolio rebalancing logic improvements

**Epic 5 — UI Enhancements (Additional)**
- ✅ Asset universe selector with type-ahead search and validation (Strategy Builder)
- ✅ Strategy builder UI (visual YAML editor with guided form)
- [ ] Real-time backtest progress with streaming logs
- [ ] Strategy templates library (beyond current file selector)
- [ ] Export results to PDF
- [ ] Fix bugs/align reinvesting amount and term fields across YAML and Strategy builder pages (currently inconsistent, values aren't passed)

**Epic 6 — Live Mode & Alerts** (Future)
- [ ] Daily price update script
- [ ] Live portfolio simulation
- [ ] Alerts page for strategy signals
- [ ] Email/SMS notifications

### Low Priority

- [ ] ~~Multi-currency support~~ No Plans
- [ ] ~~Options/derivatives support~~ No Plans (potential is to add crypto)
- [ ] Portfolio optimization (Modern Portfolio Theory - IS THIS HIGH VALUE?)
- [ ] Monte Carlo simulation (How can we use this?)
- [ ] Walk-forward analysis (Document in file use case)
- [ ] Parameter optimization (Document in file use case)
- [ ] Strategy backtesting API (for programmatic access)
- [ ] Docker containerization (Low priority)
- [ ] Cloud deployment guide and/or documentation on running behind a proxy
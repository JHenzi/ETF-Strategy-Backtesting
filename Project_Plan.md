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

- Data ingestion + per-ticker caching (yfinance).
    
- Core backtesting engine supporting fractional shares, recurring contributions, fully-invested logic, and trade ledger.
    
- YAML schema + 4 built-in strategies: Buy & Hold, DCA, Momentum Rotation, Lagging Sector.
    
- Flask UI: run a backtest, show equity curve, metrics table, trades list, and compare two runs.
    
- Persist completed runs to SQLite and be able to load them.
Files and repo layout (suggested)

backtester/
├─ backtest_engine/
│ ├─ engine.py
│ ├─ portfolio.py
│ ├─ execution.py
│ ├─ metrics.py
│ └─ strategies/
│ ├─ builtin/
│ └─ yaml_schema.py
├─ data/
│ ├─ cache.db (SQLite)
│ └─ fetcher.py
├─ webapp/
│ ├─ app.py (Flask)
│ ├─ api.py
│ └─ templates/
├─ examples/
│ └─ sample_strategies/*.yaml
├─ notebooks/
├─ tests/
└─ README.md

YAML Strategy Schema (example)

```yaml
name: laggard_rotation
description: "Buy the worst performing assets (mean reversion)"
universe:
  - XLP
  - XLY
  - XLK
  - XLE
  - XLF
parameters:
  lookback_days: 20
  laggard_count: 0  # 0 or 1 = buy ALL laggards, >1 = buy that many laggards
  cooldown_days: 30
rebalance_frequency: weekly
position_sizing: equal_weight
execution: next_open
```

**Key Implementation Details**:
- `universe` (not `assets`) - list of ticker symbols
- `parameters` - strategy-specific parameters (lookback_days, laggard_count, etc.)
- `rebalance_frequency` - weekly, monthly, etc.
- `position_sizing` - equal_weight (cash split equally)
- `execution` - next_open, same_day, first_day_only, market_close
- Recurring contributions handled via API (not in YAML) - see web UI

Notes:

- Any indicator referenced in `parameters` must be understood by the engine. If YAML references unsupported indicator (e.g. RSI) and the engine lacks RSI, validation should fail with a clear message.
    
- Pre-built strategies should be expressible in YAML and editable.
    

## AI Agent Workflow (step-by-step for automating tasks)

Use these steps for an AI agent (or a human) to add a new strategy, run tests, and update the UI.

1. **Add or edit YAML strategy**
    
    - Place YAML into `examples/sample_strategies/` or via the web UI YAML editor.
        
    - Run YAML validator. If invalid, return validation errors to the user.
        
2. **Ensure data availability**
    
    - Call the data fetcher for every ticker in the `assets` list and the requested date-range.
        
    - The fetcher should check `cache.db` and only download missing periods via `yfinance`.
        
    - If any ticker fails, report a clear error and halt the run.
        
3. **Run backtest**
    
    - Parse YAML into an executable strategy object.
        
    - Use `engine.py` to simulate ordered events by date; produce a trade ledger and daily portfolio states.
        
    - **Cash Allocation**: Available cash is divided equally across all buy orders (e.g., 5 stocks = cash/5 each).
        
    - **Recurring Reinvestments**: Contributions added before rebalancing, then split equally across targets.
        
    - **QQQ Baseline**: Automatically simulates QQQ with same investment pattern for comparison.
        
    - Persist the run: save strategy\_yaml, run\_metadata, trades, daily\_timeseries, metrics, QQQ data into SQLite.
        
4. **Compute metrics & artifacts**
    
    - Run metrics engine to compute all configured metrics and rolling windows.
        
    - Calculate QQQ metrics in parallel (CAGR, Sharpe, return, etc.).
        
    - Calculate relative performance (strategy return - QQQ return).
        
    - Generate visual assets: Plotly JSON for charts that the Flask UI can render.
        
    - Equity curve charts with QQQ overlay (aligned by date).
        
5. **Populate UI**
    
    - Index the new run in the runs table.
        
    - If run is started from the UI, stream progress logs back to the frontend until completion.
        
6. **Comparison**
    
    - When comparing two runs: load both runs (timeseries and metrics), align date axes, compute differential series (A-B), and compute difference metrics.
        
    - Store comparison metadata and offer a "select winner" button to mark a run as preferred (UI-only flag stored in DB).
        
7. **Live mode / Daily job**
    
    - An OS cron or user-run scheduler triggers `scripts/update_prices.py` daily.
        
    - The live-mode simulator uses the cached data and the chosen strategy to produce "simulated current recommended actions" and saves a snapshot to the DB.
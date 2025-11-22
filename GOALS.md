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
# Stock/ETF Backtesting Engine

A flexible, local-first Python backtesting and analysis suite for ETFs and stocks. Define, run, compare, and visualize trading strategies with an interactive web dashboard.

## Features

- **Multiple Built-in Strategies**: Buy & Hold, DCA, Momentum, Laggard Rotation, Mixed Winners/Losers, and more
- **YAML Strategy Configuration**: Define custom strategies using YAML files
- **Data Caching**: Automatic caching of market data from Yahoo Finance to SQLite
- **Comprehensive Metrics**: CAGR, Sharpe, Sortino, max drawdown, win rate, volatility, and more
- **Interactive Dashboard**: Flask web interface with Plotly visualizations
- **Run Comparison**: Compare multiple backtest runs side-by-side
- **Persistent Storage**: All runs saved to SQLite for later analysis

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd buylow
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create necessary directories:
```bash
mkdir -p data webapp/templates examples/sample_strategies
```

## Quick Start

1. Start the Flask web server:
```bash
python run.py
```

Or alternatively:
```bash
python webapp/app.py
```

2. Open your browser to `http://localhost:5000`

3. Run a backtest:
   - Select the "Run Backtest" tab
   - Paste a YAML strategy (or use one from `examples/sample_strategies/`)
   - Set start/end dates and initial cash
   - Click "Run Backtest"

4. View results:
   - Go to the "Results" tab to see all completed runs
   - Click "View" on any run to see detailed metrics and charts

5. Compare runs:
   - Go to the "Compare" tab
   - Select two runs to compare
   - View side-by-side metrics and differences

## Strategy YAML Format

Strategies are defined in YAML format. Here's an example:

```yaml
name: laggard_rotation
description: "Buy the worst performing assets"
universe:
  - XLP
  - XLY
  - XLK
parameters:
  lookback_days: 20
  laggard_count: 1
  cooldown_days: 30
rebalance_frequency: weekly
position_sizing: equal_weight
execution: next_open
```

### Available Strategies

- **buy_and_hold**: Buy assets at start and hold
- **dca**: Dollar Cost Averaging with regular contributions
- **laggard_rotation**: Buy worst performing assets
- **momentum_winner**: Buy best performing assets
- **mixed_winners_losers**: Buy both winners and losers

See `examples/sample_strategies/` for complete examples.

## Project Structure

```
buylow/
├── backtest_engine/          # Core backtesting engine
│   ├── engine.py            # Main backtesting orchestrator
│   ├── portfolio.py         # Portfolio management
│   ├── execution.py         # Order execution model
│   ├── metrics.py           # Performance metrics calculator
│   ├── persistence.py       # SQLite persistence layer
│   └── strategies/          # Strategy implementations
│       ├── base_strategy.py
│       ├── yaml_schema.py
│       ├── strategy_factory.py
│       └── builtin/         # Built-in strategies
├── data/                    # Data layer
│   ├── fetcher.py          # Yahoo Finance data fetcher
│   ├── cache.db            # Price data cache (auto-created)
│   └── backtests.db        # Backtest results (auto-created)
├── webapp/                  # Flask web application
│   ├── app.py              # Flask app and API endpoints
│   └── templates/          # HTML templates
├── examples/                # Example strategies
│   └── sample_strategies/   # YAML strategy files
└── requirements.txt         # Python dependencies
```

## API Endpoints

- `GET /api/runs` - List all backtest runs
- `GET /api/runs/<run_id>` - Get run details
- `DELETE /api/runs/<run_id>` - Delete a run
- `POST /api/backtest/run` - Start a new backtest
- `GET /api/jobs/<job_id>` - Get job status
- `POST /api/compare` - Compare two runs
- `POST /api/backtest/validate` - Validate a strategy

## Metrics Calculated

- **Return Metrics**: Total return, CAGR, Annualized return
- **Risk Metrics**: Sharpe ratio, Sortino ratio, Volatility
- **Drawdown Metrics**: Max drawdown, Drawdown duration, Time in negative
- **Trade Metrics**: Win rate, Profit factor, Average win/loss

## Data Sources

- **Yahoo Finance**: Historical OHLCV data via `yfinance`
- **Caching**: All data cached locally in SQLite for fast access

## Development

The system is designed to be:
- **Local-first**: Runs entirely on your machine
- **Extensible**: Easy to add new strategies
- **Reproducible**: Deterministic results given same inputs
- **User-friendly**: Web interface for non-technical users

## Recent Changes (November 2025)

### New Features
- **Strategy Builder UI**: Guided form to create YAML strategies without manual editing
- **Ticker Validation & Caching**: Automatic validation and caching of ticker symbols with company names
- **Ticker Library**: Browse all discovered/validated tickers
- **Enhanced Logging**: Detailed logging for debugging backtest execution

### Bug Fixes
- Fixed rebalance logic to use trading days instead of calendar days
- Fixed order execution timing for rebalancing strategies (same-day execution)
- Fixed position tracking synchronization between strategy and portfolio
- Fixed DataFrame JSON serialization in API responses
- Fixed SQLite type conversion for pandas/numpy types

### Known Issues
- **Zero Results Bug**: Some strategies (particularly rebalancing strategies) may return all-zero metrics. See troubleshooting section below.

## Troubleshooting

### Problem: Backtest Returns All Zeros

If your backtest shows all metrics as 0 (total_trades: 0, total_return: 0, etc.), this indicates trades aren't being executed.

#### Step 1: Check the Logs
Look for these log messages in the console:
- `"Generated X signals"` - Strategy is generating buy/sell signals
- `"Executing X orders"` - Orders are being executed
- `"Bought X shares"` - Trades are completing
- `"Portfolio value: $X"` - Portfolio is being tracked

If these messages are missing, the issue is in signal generation or execution.

#### Step 2: Test with Buy & Hold
Try the simplest strategy first:
```yaml
name: buy_and_hold
universe:
  - SPY
position_sizing: equal_weight
execution: first_day_only
```

This should always work and show non-zero returns if the engine is functioning.

#### Step 3: Verify Data Availability
- Check that ticker symbols are valid (use the "Validate All" button in Strategy Builder)
- Ensure date range has trading days (avoid weekends/holidays)
- Verify price data exists for your date range

#### Step 4: Check Rebalance Logic
For rebalancing strategies:
- Ensure `rebalance_frequency` is set (weekly, monthly, etc.)
- Check that the date range spans multiple rebalance periods
- Verify `lookback_days` is reasonable (not longer than date range)

#### Step 5: Enable Debug Logging
The engine logs key events. Check the console output for:
- Rebalance decisions
- Signal generation
- Order execution
- Portfolio updates

### Common Issues

**Issue**: "No data for ticker X"
- **Solution**: Validate ticker first, or use a different ticker

**Issue**: "Strategy validation failed"
- **Solution**: Check YAML syntax and required parameters for your strategy type

**Issue**: "Invalid tickers" error
- **Solution**: Use the ticker validation feature before running backtest

**Issue**: Backtest completes instantly with no trades
- **Solution**: Check that rebalance_frequency is set and date range is long enough

## How It Works

### Backtest Execution Flow

1. **Strategy Loading**: YAML is parsed and validated
2. **Ticker Validation**: All tickers are validated and cached
3. **Data Fetching**: Historical price data is fetched (or loaded from cache)
4. **Simulation Loop**: For each trading day:
   - Check if rebalancing is needed
   - Generate buy/sell signals
   - Place orders
   - Execute orders (on rebalance days, execute immediately)
   - Update portfolio (cash, positions)
   - Take daily snapshot (for equity curve)
5. **Metrics Calculation**: Compute performance metrics from equity curve
6. **Results Storage**: Save to SQLite database

### Portfolio Simulation

The engine simulates a real portfolio:
- **Cash**: Starting cash, reduced by buys, increased by sells
- **Positions**: Dictionary of ticker → shares held
- **Daily Value**: Cash + (shares × current price) for each position
- **Equity Curve**: Portfolio value over time (for metrics calculation)

### Rebalancing Logic

For weekly rebalancing:
- Counts **trading days** since last rebalance (not calendar days)
- Rebalances when 5+ trading days have passed OR 7+ calendar days
- Executes all trades on the same day (immediate execution)
- Splits available cash equally across buy orders

### Baseline Comparison

**TODO**: Currently not implemented. Planned feature:
- Automatically fetch QQQ data
- Calculate QQQ performance in parallel
- Include relative performance metrics
- Show comparison charts

## Future Enhancements

- **Baseline Comparison**: Automatic QQQ (or custom benchmark) comparison
- **Additional Strategies**: RSI, SMA crossover, Relative Strength, Buy the Dip
- **More Sophisticated Position Sizing**: Kelly Criterion, risk-based sizing
- **Commission & Slippage Modeling**: Realistic trading costs
- **Live Mode**: Daily price updates and simulated live portfolio
- **Export Results**: CSV/Excel export for trades and equity curve
- **Enhanced Visualizations**: Plotly charts for equity curves, drawdowns, rolling metrics

## License

MIT License

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.


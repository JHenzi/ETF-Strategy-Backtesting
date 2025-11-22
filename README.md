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

## Screenshots

### Strategy Builder
The Strategy Builder provides a guided interface to create trading strategies without manually editing YAML. Features include type-ahead ticker search with validation, automatic company name lookup, and live YAML preview.

![Strategy Builder](screenshots/Screenshot-Strategy-Builder.png)

### YAML Editor Tab
For advanced users, you can directly edit YAML strategy files with syntax validation and strategy file selection.

![YAML Editor](screenshots/Screenshot-YAML-Tab.png)

### Results Viewer
View detailed backtest results with interactive charts, comprehensive metrics tables, QQQ baseline comparison, and trade history. The equity curve chart shows both strategy and QQQ performance overlaid for easy comparison.

![Results Viewer](screenshots/Screenshot%20-%20Results%20Viewer.png)

### Strategy Comparison
Compare two backtest runs side-by-side with conditional highlighting (winners in green), overall winner declaration, and detailed metric-by-metric comparison. Includes equity curve overlay charts.

![Strategy Comparison](screenshots/Screenshot%20-%20Strategy%20Comparison.png)

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

The server will start on port 5000 by default. If you need to use a different port (e.g., due to port conflicts), use the `--port` argument:
```bash
python run.py --port 5001
```

You can also specify other options:
```bash
python run.py --port 5001 --debug  # Enable debug mode
python run.py --host 127.0.0.1     # Bind to localhost only
```

Or alternatively, run directly:
```bash
python webapp/app.py
```

2. Open your browser to `http://localhost:5000` (or the port you specified)

3. Run a backtest:
   - Select the "Run Backtest" tab
   - Paste a YAML strategy (or use one from `examples/sample_strategies/`)
   - Set start/end dates and initial cash
   - (Optional) Set recurring reinvestment amount and frequency
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

**Key Points**:
- `laggard_count: 0` or `1` means buy **ALL** laggards (all assets in universe)
- `laggard_count > 1` means buy only that many worst performers
- Cash is automatically split equally across all selected laggards
- Strategy accumulates positions (never sells) - builds portfolio over time

### Available Strategies

- **buy_and_hold**: Buy assets at start and hold
- **dca**: Dollar Cost Averaging with regular contributions
- **laggard_rotation**: Buy worst performing assets
- **momentum_winner**: Buy best performing assets
- **mixed_winners_losers**: Buy both winners and losers
- **rsi_mean_reversion**: Buy oversold assets (RSI < 30), sell overbought (RSI > 70)

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
- **QQQ Baseline Comparison**: All backtests now automatically compare against QQQ with same investment pattern
- **Recurring Reinvestment**: Support for weekly/monthly reinvestments with configurable amounts
- **Beautiful Results Page**: Interactive charts, metrics tables, and QQQ comparison visualization
- **Accumulation Strategies**: All rotation strategies now accumulate positions (no selling)

### Bug Fixes
- Fixed rebalance logic to use trading days instead of calendar days
- Fixed order execution timing for rebalancing strategies (same-day execution)
- Fixed position tracking synchronization between strategy and portfolio
- Fixed DataFrame JSON serialization in API responses
- Fixed SQLite type conversion for pandas/numpy types
- Fixed `get_returns()` to handle missing trading days gracefully
- Fixed cash allocation to split equally across all buy orders
- Fixed QQQ chart alignment by date for proper overlay comparison
- Fixed QQQ simulation to match strategy investment pattern (reinvestments)

### Strategy Updates
- **Laggard Rotation**: Now buys ALL laggards when `laggard_count <= 1` (splits cash equally)
- **All Rotation Strategies**: Changed to accumulation-only (no selling, only buying)
- **Cash Allocation**: Always divides available cash equally by number of target stocks/ETFs

### Known Issues
- **Resolved**: Zero results bug has been fixed - strategies now execute trades correctly

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
3. **Data Fetching**: Historical price data is fetched (or loaded from cache) for both strategy assets and QQQ
4. **Simulation Loop**: For each trading day:
   - Add recurring contributions (if configured) to portfolio cash
   - Check if rebalancing is needed (using trading days)
   - Generate buy/sell signals from strategy
   - Place orders
   - **Cash Allocation**: Split available cash equally across all buy orders
   - Execute orders (on rebalance days, execute immediately)
   - Update portfolio (cash, positions)
   - Take daily snapshot (for equity curve)
5. **QQQ Baseline Simulation**: In parallel, simulate QQQ with same investment pattern
6. **Metrics Calculation**: Compute performance metrics from equity curve for both strategy and QQQ
7. **Results Storage**: Save to SQLite database (strategy + QQQ data)

### Portfolio Simulation

The engine simulates a real portfolio:
- **Cash**: Starting cash, reduced by buys, increased by sells
- **Positions**: Dictionary of ticker → shares held
- **Daily Value**: Cash + (shares × current price) for each position
- **Equity Curve**: Portfolio value over time (for metrics calculation)

### Rebalancing Logic

For weekly rebalancing:
- Counts **trading days** since last rebalance (not calendar days)
- Rebalances when 5+ trading days have passed
- Executes all trades on the same day (immediate execution)
- **Cash Allocation**: Splits available cash equally across ALL buy orders
  - Example: $10,000 cash + 5 laggards = $2,000 per stock
  - Example: $100 contribution + 5 laggards = $20 per stock

### Cash Allocation

**How it works**:
- All buy orders with `amount: None` are collected
- Total available cash is divided by number of buy orders
- Each order gets `total_cash / number_of_orders`
- This ensures equal allocation across all target stocks/ETFs

**Example**:
- Initial cash: $10,000
- Strategy selects 5 laggards
- Each laggard gets: $10,000 / 5 = $2,000
- Next week: Add $100 contribution
- Each laggard gets: $100 / 5 = $20

### Baseline Comparison

**✅ IMPLEMENTED**: All backtests automatically compare against QQQ baseline.

**How it works**:
- QQQ portfolio starts with same initial cash as strategy
- QQQ receives same recurring contributions on same schedule
- QQQ reinvests on contribution days (matching strategy pattern)
- Both portfolios tracked day-by-day with same date alignment
- Metrics calculated for both: CAGR, Sharpe, Sortino, max drawdown, etc.
- Relative performance shown: strategy return vs QQQ return
- Chart displays both equity curves overlaid for visual comparison
- "Beat QQQ" indicator shows if strategy outperformed baseline

## Future Enhancements

- **✅ Baseline Comparison**: QQQ comparison implemented (see above)
- **Enhanced Stock/ETF Picker**: Interactive checkbox selection with search/filter (see GOALS.md)
- **Additional Strategies**: RSI, SMA crossover, Relative Strength, Buy the Dip
- **More Sophisticated Position Sizing**: Kelly Criterion, risk-based sizing
- **Commission & Slippage Modeling**: Realistic trading costs
- **Live Mode**: Daily price updates and simulated live portfolio
- **Export Results**: CSV/Excel export for trades and equity curve
- **Custom Benchmark Selection**: Allow users to choose benchmark other than QQQ

## License

MIT License

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.


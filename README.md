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

## Future Enhancements

- Additional built-in strategies (RSI, SMA crossover, etc.)
- More sophisticated position sizing
- Commission and slippage modeling
- Live mode with daily price updates
- Export results to CSV/Excel
- More detailed visualizations

## License

MIT License

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.


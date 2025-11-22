"""
Flask web application for backtesting.
"""
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import json
import threading
import uuid
from datetime import datetime
import logging
import pandas as pd

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backtest_engine.engine import BacktestEngine
from backtest_engine.strategies.strategy_factory import StrategyFactory
from backtest_engine.persistence import BacktestPersistence
from data.fetcher import DataFetcher

app = Flask(__name__)
CORS(app)

# Initialize components
data_fetcher = DataFetcher()
engine = BacktestEngine(data_fetcher)
strategy_factory = StrategyFactory()
persistence = BacktestPersistence()

# Job tracking (in-memory for now, could use Redis in production)
jobs = {}
job_lock = threading.Lock()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/runs', methods=['GET'])
def list_runs():
    """List all saved backtest runs."""
    try:
        runs = persistence.list_runs()
        return jsonify({'success': True, 'runs': runs})
    except Exception as e:
        logger.error(f"Error listing runs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/runs/<int:run_id>', methods=['GET'])
def get_run(run_id):
    """Get details of a specific run."""
    try:
        run_data = persistence.load_run(run_id)
        
        # Convert DataFrames to JSON-serializable format
        if 'equity_curve' in run_data:
            equity_curve = run_data['equity_curve']
            if isinstance(equity_curve, pd.DataFrame):
                if not equity_curve.empty:
                    # Reset index to include date as a column
                    equity_curve_reset = equity_curve.reset_index()
                    run_data['equity_curve'] = equity_curve_reset.to_dict('records')
                else:
                    run_data['equity_curve'] = []
            elif equity_curve is None:
                run_data['equity_curve'] = []
        
        if 'trades' in run_data:
            trades = run_data['trades']
            if isinstance(trades, pd.DataFrame):
                if not trades.empty:
                    run_data['trades'] = trades.to_dict('records')
                else:
                    run_data['trades'] = []
            elif trades is None:
                run_data['trades'] = []
        
        # Convert metadata DataFrames if any
        if 'metadata' in run_data:
            metadata = run_data['metadata']
            if isinstance(metadata, dict):
                # Check for any DataFrames in metadata
                for key, value in metadata.items():
                    if isinstance(value, pd.DataFrame):
                        if not value.empty:
                            metadata[key] = value.reset_index().to_dict('records')
                        else:
                            metadata[key] = []
        
        # Extract QQQ data from metadata for easier access
        if 'metadata' in run_data and isinstance(run_data['metadata'], dict):
            if 'qqq_equity_curve' in run_data['metadata']:
                run_data['qqq_equity_curve'] = run_data['metadata']['qqq_equity_curve']
            if 'qqq_metrics' in run_data['metadata']:
                run_data['qqq_metrics'] = run_data['metadata']['qqq_metrics']
        
        # Convert run_info Series/DataFrame if needed
        if 'run_info' in run_data:
            run_info = run_data['run_info']
            if isinstance(run_info, pd.Series):
                run_data['run_info'] = run_info.to_dict()
            # Flatten run_info into main run object for easier access
            if isinstance(run_info, dict):
                for key, value in run_info.items():
                    if key not in run_data:  # Don't overwrite existing keys
                        run_data[key] = value
        
        return jsonify({'success': True, 'run': run_data})
    except Exception as e:
        import traceback
        logger.error(f"Error loading run {run_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/runs/<int:run_id>', methods=['DELETE'])
def delete_run(run_id):
    """Delete a backtest run."""
    try:
        persistence.delete_run(run_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting run {run_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/runs/<int:run_id>/preferred', methods=['POST'])
def mark_preferred(run_id):
    """Mark a run as preferred."""
    try:
        preferred = request.json.get('preferred', True)
        persistence.mark_preferred(run_id, preferred)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error marking run {run_id} as preferred: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backtest/validate', methods=['POST'])
def validate_backtest():
    """Validate a strategy before running."""
    try:
        data = request.json
        strategy_yaml = data.get('strategy_yaml')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not all([strategy_yaml, start_date, end_date]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Load and validate strategy
        strategy = strategy_factory.create_strategy(yaml_string=strategy_yaml)
        validation = engine.validate_strategy(strategy, start_date, end_date)
        
        return jsonify({
            'success': True,
            'validation': validation
        })
    except Exception as e:
        logger.error(f"Error validating backtest: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backtest/run', methods=['POST'])
def run_backtest():
    """Start a backtest run (async)."""
    try:
        data = request.json
        strategy_yaml = data.get('strategy_yaml')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        initial_cash = data.get('initial_cash', 10000.0)
        recurring_contribution = data.get('recurring_contribution')
        run_name = data.get('run_name')
        
        if not all([strategy_yaml, start_date, end_date]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job BEFORE starting thread to avoid race condition
        with job_lock:
            jobs[job_id] = {
                'status': 'running',
                'progress': 0,
                'message': 'Starting backtest...',
                'created_at': datetime.now().isoformat()
            }
        
        # Start async job
        thread = threading.Thread(
            target=_run_backtest_job,
            args=(job_id, strategy_yaml, start_date, end_date, initial_cash, recurring_contribution, run_name)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id
        })
    except Exception as e:
        logger.error(f"Error starting backtest: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _run_backtest_job(job_id, strategy_yaml, start_date, end_date, initial_cash, recurring_contribution, run_name):
    """Run backtest in background thread."""
    try:
        # Ensure job exists
        with job_lock:
            if job_id not in jobs:
                jobs[job_id] = {
                    'status': 'running',
                    'progress': 0,
                    'message': 'Starting...',
                    'created_at': datetime.now().isoformat()
                }
            jobs[job_id]['message'] = 'Loading strategy...'
        
        # Create strategy
        strategy = strategy_factory.create_strategy(yaml_string=strategy_yaml)
        strategy_name = strategy.name
        
        with job_lock:
            if job_id in jobs:
                jobs[job_id]['message'] = 'Fetching market data...'
                jobs[job_id]['progress'] = 20
        
        # Run backtest
        results = engine.run_backtest(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
            recurring_contribution=recurring_contribution,
            execution_when='next_open'
        )
        
        # Debug: Log results before saving
        logger.info(f"Backtest results keys: {list(results.keys())}")
        if 'metrics' in results:
            logger.info(f"Metrics before save: {results['metrics']}")
        if 'trades' in results:
            trades_df = results['trades']
            logger.info(f"Trades DataFrame: {len(trades_df)} rows, columns: {list(trades_df.columns) if hasattr(trades_df, 'columns') else 'N/A'}")
        if 'equity_curve' in results:
            equity_df = results['equity_curve']
            logger.info(f"Equity curve DataFrame: {len(equity_df)} rows, columns: {list(equity_df.columns) if hasattr(equity_df, 'columns') else 'N/A'}")
        
        with job_lock:
            if job_id in jobs:
                jobs[job_id]['message'] = 'Saving results...'
                jobs[job_id]['progress'] = 90
        
        # Save to persistence
        run_id = persistence.save_run(
            results=results,
            strategy_yaml=strategy_yaml,
            strategy_name=strategy_name,
            run_name=run_name
        )
        
        logger.info(f"Saved backtest run {run_id}")
        
        with job_lock:
            if job_id in jobs:
                jobs[job_id]['status'] = 'completed'
                jobs[job_id]['progress'] = 100
                jobs[job_id]['message'] = 'Backtest completed'
                jobs[job_id]['run_id'] = run_id
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        logger.error(f"Error in backtest job {job_id}: {error_msg}\n{error_traceback}")
        
        with job_lock:
            # Ensure job exists before updating
            if job_id not in jobs:
                jobs[job_id] = {
                    'status': 'failed',
                    'progress': 0,
                    'message': f'Error: {error_msg}',
                    'created_at': datetime.now().isoformat()
                }
            else:
                jobs[job_id]['status'] = 'failed'
                jobs[job_id]['message'] = f'Error: {error_msg}'


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of a running job."""
    with job_lock:
        job = jobs.get(job_id, {'status': 'not_found'})
    
    return jsonify({'success': True, 'job': job})


@app.route('/api/compare', methods=['POST'])
def compare_runs():
    """Compare two backtest runs."""
    try:
        data = request.json
        run_id_1 = data.get('run_id_1')
        run_id_2 = data.get('run_id_2')
        
        if not run_id_1 or not run_id_2:
            return jsonify({'success': False, 'error': 'Must provide two run IDs'}), 400
        
        # Load both runs
        run1 = persistence.load_run(run_id_1)
        run2 = persistence.load_run(run_id_2)
        
        # Compare metrics
        metrics1 = run1['metrics']
        metrics2 = run2['metrics']
        
        comparison = {
            'run1': {
                'run_id': run_id_1,
                'name': run1['run_info']['name'],
                'metrics': metrics1
            },
            'run2': {
                'run_id': run_id_2,
                'name': run2['run_info']['name'],
                'metrics': metrics2
            },
            'differences': {}
        }
        
        # Calculate differences
        for metric in metrics1:
            if metric in metrics2:
                diff = metrics2[metric] - metrics1[metric]
                comparison['differences'][metric] = {
                    'run1': metrics1[metric],
                    'run2': metrics2[metric],
                    'difference': diff,
                    'winner': 'run2' if diff > 0 else 'run1' if diff < 0 else 'tie'
                }
        
        # Align equity curves for overlay
        equity1 = run1['equity_curve']
        equity2 = run2['equity_curve']
        
        # Ensure both are DataFrames
        if isinstance(equity1, pd.DataFrame) and isinstance(equity2, pd.DataFrame):
            if not equity1.empty and not equity2.empty:
                # Merge on date
                merged = equity1.merge(
                    equity2,
                    left_index=True,
                    right_index=True,
                    suffixes=('_1', '_2'),
                    how='outer'
                ).sort_index()
                
                comparison['equity_curves'] = merged.reset_index().to_dict('records')
            else:
                comparison['equity_curves'] = []
        else:
            comparison['equity_curves'] = []
        
        return jsonify({'success': True, 'comparison': comparison})
    except Exception as e:
        logger.error(f"Error comparing runs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tickers/validate', methods=['POST'])
def validate_tickers():
    """Validate ticker symbols."""
    try:
        data = request.json
        tickers = data.get('tickers', [])
        
        if not tickers:
            return jsonify({'success': False, 'error': 'No tickers provided'}), 400
        
        valid, invalid = data_fetcher.validate_tickers(tickers)
        
        # Get info for valid tickers
        ticker_info = []
        for ticker in valid:
            info = data_fetcher.get_ticker_info(ticker)
            if info:
                ticker_info.append(info)
        
        return jsonify({
            'success': True,
            'valid': valid,
            'invalid': invalid,
            'ticker_info': ticker_info
        })
    except Exception as e:
        logger.error(f"Error validating tickers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/tickers/list', methods=['GET'])
def list_tickers():
    """List all discovered/validated tickers."""
    try:
        tickers = data_fetcher.list_tickers()
        return jsonify({
            'success': True,
            'tickers': tickers
        })
    except Exception as e:
        logger.error(f"Error listing tickers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/list', methods=['GET'])
def list_strategies():
    """List available YAML strategy files."""
    try:
        from pathlib import Path
        
        strategies_dir = Path('examples/sample_strategies')
        strategies = []
        
        if strategies_dir.exists():
            for yaml_file in strategies_dir.glob('*.yaml'):
                strategies.append({
                    'name': yaml_file.stem,
                    'filename': yaml_file.name,
                    'path': str(yaml_file)
                })
        
        # Sort by name
        strategies.sort(key=lambda x: x['name'])
        
        return jsonify({
            'success': True,
            'strategies': strategies
        })
    except Exception as e:
        logger.error(f"Error listing strategies: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/strategies/load/<path:filename>', methods=['GET'])
def load_strategy(filename):
    """Load a strategy YAML file by filename."""
    try:
        from pathlib import Path
        
        # Security: only allow files from sample_strategies directory
        strategies_dir = Path('examples/sample_strategies')
        file_path = strategies_dir / filename
        
        # Ensure the file is within the strategies directory (prevent path traversal)
        if not file_path.resolve().is_relative_to(strategies_dir.resolve()):
            return jsonify({'success': False, 'error': 'Invalid file path'}), 400
        
        if not file_path.exists():
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'content': content,
            'filename': filename
        })
    except Exception as e:
        logger.error(f"Error loading strategy {filename}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


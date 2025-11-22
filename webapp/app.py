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
        
        # Convert DataFrames to JSON
        if not run_data['equity_curve'].empty:
            run_data['equity_curve'] = run_data['equity_curve'].reset_index().to_dict('records')
        if not run_data['trades'].empty:
            run_data['trades'] = run_data['trades'].to_dict('records')
        
        return jsonify({'success': True, 'run': run_data})
    except Exception as e:
        logger.error(f"Error loading run {run_id}: {e}")
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
        
        # Start async job
        thread = threading.Thread(
            target=_run_backtest_job,
            args=(job_id, strategy_yaml, start_date, end_date, initial_cash, recurring_contribution, run_name)
        )
        thread.daemon = True
        thread.start()
        
        with job_lock:
            jobs[job_id] = {
                'status': 'running',
                'progress': 0,
                'message': 'Starting backtest...',
                'created_at': datetime.now().isoformat()
            }
        
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
        with job_lock:
            jobs[job_id]['message'] = 'Loading strategy...'
        
        # Create strategy
        strategy = strategy_factory.create_strategy(yaml_string=strategy_yaml)
        strategy_name = strategy.name
        
        with job_lock:
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
        
        with job_lock:
            jobs[job_id]['message'] = 'Saving results...'
            jobs[job_id]['progress'] = 90
        
        # Save to persistence
        run_id = persistence.save_run(
            results=results,
            strategy_yaml=strategy_yaml,
            strategy_name=strategy_name,
            run_name=run_name
        )
        
        with job_lock:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['progress'] = 100
            jobs[job_id]['message'] = 'Backtest completed'
            jobs[job_id]['run_id'] = run_id
        
    except Exception as e:
        logger.error(f"Error in backtest job {job_id}: {e}")
        with job_lock:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['message'] = f'Error: {str(e)}'


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
        
        return jsonify({
            'success': True,
            'valid': valid,
            'invalid': invalid
        })
    except Exception as e:
        logger.error(f"Error validating tickers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


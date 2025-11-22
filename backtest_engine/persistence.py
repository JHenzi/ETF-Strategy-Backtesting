"""
Persistence layer for saving and loading backtest runs.
"""
import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def _convert_to_sqlite_type(value):
    """Convert value to a SQLite-compatible type."""
    if value is None:
        return None
    
    # Handle NaN values
    if pd.isna(value):
        return None
    
    # Handle datetime/timestamp types
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime('%Y-%m-%d')
    
    # Handle numpy types (must check before native Python types)
    if isinstance(value, np.generic):
        if isinstance(value, (np.integer,)):
            return int(value)
        elif isinstance(value, (np.floating,)):
            val = float(value)
            return None if np.isnan(val) else val
        elif isinstance(value, np.bool_):
            return bool(value)
        else:
            return str(value)
    
    # Handle numpy arrays
    if isinstance(value, np.ndarray):
        return value.tolist()
    
    # Handle native Python types
    if isinstance(value, bool):
        return 1 if value else 0
    elif isinstance(value, (float, int, str)):
        # Check for NaN in float
        if isinstance(value, float) and (value != value):  # NaN check
            return None
        return value
    
    # Try to convert to string as last resort
    try:
        return str(value)
    except Exception:
        return None


class BacktestPersistence:
    """Handles persistence of backtest runs to SQLite."""
    
    def __init__(self, db_path: str = "data/backtests.db"):
        """Initialize persistence layer."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                strategy_name TEXT,
                strategy_yaml TEXT,
                start_date DATE,
                end_date DATE,
                initial_cash REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed',
                preferred INTEGER DEFAULT 0
            )
        """)
        
        # Run metadata (JSON)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_metadata (
                run_id INTEGER PRIMARY KEY,
                metadata_json TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                run_id INTEGER,
                metric_name TEXT,
                metric_value REAL,
                PRIMARY KEY (run_id, metric_name),
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                date DATE,
                ticker TEXT,
                action TEXT,
                shares REAL,
                price REAL,
                value REAL,
                reason TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        # Equity curve (daily timeseries)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equity_curve (
                run_id INTEGER,
                date DATE,
                total_value REAL,
                cash REAL,
                equity_curve_pct REAL,
                PRIMARY KEY (run_id, date),
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_run(
        self,
        results: Dict[str, Any],
        strategy_yaml: str,
        strategy_name: str,
        run_name: Optional[str] = None
    ) -> int:
        """
        Save a completed backtest run.
        
        Returns:
            run_id of saved run
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert run record
            if run_name is None:
                run_name = f"{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            cursor.execute("""
                INSERT INTO runs (name, strategy_name, strategy_yaml, start_date, end_date, initial_cash, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                run_name,
                strategy_name,
                strategy_yaml,
                _convert_to_sqlite_type(results.get('start_date')),
                _convert_to_sqlite_type(results.get('end_date')),
                _convert_to_sqlite_type(results.get('initial_cash')),
                'completed'
            ))
            
            run_id = cursor.lastrowid
            
            # Save metrics
            metrics = results.get('metrics', {})
            for metric_name, metric_value in metrics.items():
                cursor.execute("""
                    INSERT INTO metrics (run_id, metric_name, metric_value)
                    VALUES (?, ?, ?)
                """, (run_id, metric_name, _convert_to_sqlite_type(metric_value)))
            
            # Save trades
            trades = results.get('trades', pd.DataFrame())
            if not trades.empty:
                for idx, trade in trades.iterrows():
                    # Use .get() with None default, then convert
                    cursor.execute("""
                        INSERT INTO trades (run_id, date, ticker, action, shares, price, value, reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        run_id,
                        _convert_to_sqlite_type(trade.get('date', None)),
                        _convert_to_sqlite_type(trade.get('ticker', None)),
                        _convert_to_sqlite_type(trade.get('action', None)),
                        _convert_to_sqlite_type(trade.get('shares', None)),
                        _convert_to_sqlite_type(trade.get('price', None)),
                        _convert_to_sqlite_type(trade.get('value', None)),
                        _convert_to_sqlite_type(trade.get('reason', None))
                    ))
            
            # Save equity curve
            equity_curve = results.get('equity_curve', pd.DataFrame())
            if not equity_curve.empty:
                for date, row in equity_curve.iterrows():
                    cursor.execute("""
                        INSERT INTO equity_curve (run_id, date, total_value, cash, equity_curve_pct)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        run_id,
                        _convert_to_sqlite_type(date),
                        _convert_to_sqlite_type(row.get('total_value', None)),
                        _convert_to_sqlite_type(row.get('cash', None)),
                        _convert_to_sqlite_type(row.get('equity_curve_pct', None))
                    ))
            
            # Save metadata
            metadata = {
                'rolling_metrics_30': results.get('rolling_metrics_30', {}),
                'rolling_metrics_60': results.get('rolling_metrics_60', {}),
                'rolling_metrics_90': results.get('rolling_metrics_90', {}),
                'underwater_plot': results.get('underwater_plot', {})
            }
            cursor.execute("""
                INSERT INTO run_metadata (run_id, metadata_json)
                VALUES (?, ?)
            """, (run_id, json.dumps(metadata, default=str)))
            
            conn.commit()
            logger.info(f"Saved backtest run {run_id}: {run_name}")
            return run_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving run: {e}")
            raise
        finally:
            conn.close()
    
    def list_runs(self) -> List[Dict[str, Any]]:
        """List all saved runs."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT run_id, name, strategy_name, start_date, end_date, 
                   initial_cash, created_at, status, preferred
            FROM runs
            ORDER BY created_at DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df.to_dict('records')
    
    def load_run(self, run_id: int) -> Dict[str, Any]:
        """Load a complete backtest run."""
        conn = sqlite3.connect(self.db_path)
        
        # Load run info
        run_df = pd.read_sql_query(
            "SELECT * FROM runs WHERE run_id = ?",
            conn,
            params=(run_id,)
        )
        
        if run_df.empty:
            conn.close()
            raise ValueError(f"Run {run_id} not found")
        
        run_info = run_df.iloc[0].to_dict()
        
        # Load metrics
        metrics_df = pd.read_sql_query(
            "SELECT metric_name, metric_value FROM metrics WHERE run_id = ?",
            conn,
            params=(run_id,)
        )
        metrics = dict(zip(metrics_df['metric_name'], metrics_df['metric_value']))
        
        # Load trades
        trades_df = pd.read_sql_query(
            "SELECT date, ticker, action, shares, price, value, reason FROM trades WHERE run_id = ? ORDER BY date",
            conn,
            params=(run_id,),
            parse_dates=['date']
        )
        
        # Load equity curve
        equity_df = pd.read_sql_query(
            "SELECT date, total_value, cash, equity_curve_pct FROM equity_curve WHERE run_id = ? ORDER BY date",
            conn,
            params=(run_id,),
            parse_dates=['date']
        )
        equity_df.set_index('date', inplace=True)
        
        # Load metadata
        metadata_df = pd.read_sql_query(
            "SELECT metadata_json FROM run_metadata WHERE run_id = ?",
            conn,
            params=(run_id,)
        )
        metadata = {}
        if not metadata_df.empty:
            metadata = json.loads(metadata_df.iloc[0]['metadata_json'])
        
        conn.close()
        
        return {
            'run_id': run_id,
            'run_info': run_info,
            'metrics': metrics,
            'trades': trades_df,
            'equity_curve': equity_df,
            'metadata': metadata
        }
    
    def delete_run(self, run_id: int):
        """Delete a backtest run and all associated data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Delete in order (respecting foreign keys)
            cursor.execute("DELETE FROM metrics WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM trades WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM equity_curve WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM run_metadata WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
            
            conn.commit()
            logger.info(f"Deleted run {run_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting run: {e}")
            raise
        finally:
            conn.close()
    
    def mark_preferred(self, run_id: int, preferred: bool = True):
        """Mark a run as preferred (for comparison UI)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE runs SET preferred = ? WHERE run_id = ?
        """, (1 if preferred else 0, run_id))
        
        conn.commit()
        conn.close()


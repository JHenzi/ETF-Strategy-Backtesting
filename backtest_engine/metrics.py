"""
Metrics calculator for backtest results.
Computes performance metrics like CAGR, Sharpe, Sortino, drawdown, etc.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculates performance metrics from backtest results."""
    
    def __init__(self, equity_curve: pd.DataFrame, trades: pd.DataFrame):
        """
        Initialize metrics calculator.
        
        Args:
            equity_curve: DataFrame with columns: date, total_value, equity_curve_pct
            trades: DataFrame with trade history
        """
        self.equity_curve = equity_curve.copy()
        self.trades = trades.copy()
        self._compute_returns()
    
    def _compute_returns(self):
        """Compute daily returns from equity curve."""
        if len(self.equity_curve) < 2:
            self.equity_curve['returns'] = 0.0
            return
        
        # Calculate daily returns
        self.equity_curve['returns'] = self.equity_curve['total_value'].pct_change().fillna(0.0)
        self.equity_curve['cumulative_returns'] = (1 + self.equity_curve['returns']).cumprod() - 1
    
    def calculate_all_metrics(self) -> Dict[str, float]:
        """Calculate all available metrics."""
        metrics = {}
        
        metrics.update(self.calculate_return_metrics())
        metrics.update(self.calculate_risk_metrics())
        metrics.update(self.calculate_trade_metrics())
        metrics.update(self.calculate_drawdown_metrics())
        
        return metrics
    
    def calculate_return_metrics(self) -> Dict[str, float]:
        """Calculate return-based metrics."""
        if len(self.equity_curve) < 2:
            return {
                'total_return': 0.0,
                'cagr': 0.0,
                'annualized_return': 0.0
            }
        
        total_value = self.equity_curve['total_value'].iloc[-1]
        initial_value = self.equity_curve['total_value'].iloc[0]
        total_return = ((total_value - initial_value) / initial_value) * 100
        
        # Calculate CAGR
        start_date = self.equity_curve.index[0]
        end_date = self.equity_curve.index[-1]
        years = (end_date - start_date).days / 365.25
        
        if years > 0 and total_return > -100:
            cagr = (((total_value / initial_value) ** (1 / years)) - 1) * 100
        else:
            cagr = 0.0
        
        # Annualized return (simple)
        annualized_return = (total_return / years) if years > 0 else 0.0
        
        return {
            'total_return': total_return,
            'cagr': cagr,
            'annualized_return': annualized_return
        }
    
    def calculate_risk_metrics(self) -> Dict[str, float]:
        """Calculate risk metrics (Sharpe, Sortino, volatility)."""
        if len(self.equity_curve) < 2:
            return {
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'volatility': 0.0,
                'max_drawdown': 0.0
            }
        
        returns = self.equity_curve['returns']
        
        # Annualize returns and volatility
        trading_days = len(returns)
        years = trading_days / 252.0  # Approximate trading days per year
        
        if years > 0:
            annualized_return = returns.mean() * 252
            volatility = returns.std() * np.sqrt(252)
        else:
            annualized_return = 0.0
            volatility = 0.0
        
        # Sharpe ratio (assuming risk-free rate of 0)
        sharpe = (annualized_return / volatility) if volatility > 0 else 0.0
        
        # Sortino ratio (only downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std() * np.sqrt(252)
            sortino = (annualized_return / downside_std) if downside_std > 0 else 0.0
        else:
            sortino = 0.0
        
        return {
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'volatility': volatility * 100,  # As percentage
            'annualized_return': annualized_return * 100
        }
    
    def calculate_drawdown_metrics(self) -> Dict[str, float]:
        """Calculate drawdown metrics."""
        if len(self.equity_curve) < 2:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0,
                'time_in_negative': 0.0
            }
        
        # Calculate running maximum
        running_max = self.equity_curve['total_value'].expanding().max()
        drawdown = ((self.equity_curve['total_value'] - running_max) / running_max) * 100
        
        max_drawdown = abs(drawdown.min())
        
        # Calculate max drawdown duration
        in_drawdown = drawdown < 0
        drawdown_periods = []
        current_period = 0
        
        for is_dd in in_drawdown:
            if is_dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0
        if current_period > 0:
            drawdown_periods.append(current_period)
        
        max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
        
        # Time in negative (percentage of time portfolio was below initial value)
        time_in_negative = (self.equity_curve['total_value'] < self.equity_curve['total_value'].iloc[0]).sum()
        time_in_negative_pct = (time_in_negative / len(self.equity_curve)) * 100
        
        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'time_in_negative': time_in_negative_pct
        }
    
    def calculate_trade_metrics(self) -> Dict[str, float]:
        """Calculate trade-based metrics (win rate, profit factor, etc.)."""
        if len(self.trades) == 0:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }
        
        # Group trades by ticker to calculate P&L per trade
        # For simplicity, we'll use a basic approach
        buy_trades = self.trades[self.trades['action'] == 'BUY']
        sell_trades = self.trades[self.trades['action'] == 'SELL']
        
        # Calculate approximate P&L (simplified - would need position tracking)
        # For now, use a simple heuristic based on equity curve
        total_trades = len(buy_trades) + len(sell_trades)
        
        # Win rate based on equity curve improvement
        if len(self.equity_curve) > 1:
            positive_days = (self.equity_curve['returns'] > 0).sum()
            win_rate = (positive_days / len(self.equity_curve)) * 100
        else:
            win_rate = 0.0
        
        # Profit factor (simplified)
        positive_returns = self.equity_curve['returns'][self.equity_curve['returns'] > 0].sum()
        negative_returns = abs(self.equity_curve['returns'][self.equity_curve['returns'] < 0].sum())
        profit_factor = (positive_returns / negative_returns) if negative_returns > 0 else 0.0
        
        avg_win = positive_returns / max(1, (self.equity_curve['returns'] > 0).sum())
        avg_loss = negative_returns / max(1, (self.equity_curve['returns'] < 0).sum())
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win * 100,
            'avg_loss': avg_loss * 100
        }
    
    def get_rolling_metrics(self, window_days: int = 30) -> pd.DataFrame:
        """Calculate rolling metrics over a window."""
        if len(self.equity_curve) < window_days:
            return pd.DataFrame()
        
        rolling_returns = self.equity_curve['returns'].rolling(window=window_days)
        rolling_vol = rolling_returns.std() * np.sqrt(252) * 100
        rolling_mean = rolling_returns.mean() * 252 * 100
        
        result = pd.DataFrame({
            'date': self.equity_curve.index,
            'rolling_return': rolling_mean,
            'rolling_volatility': rolling_vol
        })
        result.set_index('date', inplace=True)
        
        return result
    
    def get_underwater_plot(self) -> pd.DataFrame:
        """Get data for underwater plot (drawdown over time)."""
        if len(self.equity_curve) < 2:
            return pd.DataFrame()
        
        running_max = self.equity_curve['total_value'].expanding().max()
        drawdown = ((self.equity_curve['total_value'] - running_max) / running_max) * 100
        
        result = pd.DataFrame({
            'date': self.equity_curve.index,
            'drawdown': drawdown
        })
        result.set_index('date', inplace=True)
        
        return result


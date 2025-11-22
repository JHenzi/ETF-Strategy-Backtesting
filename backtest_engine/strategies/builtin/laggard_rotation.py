"""Laggard Rotation strategy implementation."""
from typing import Dict, List, Any
from datetime import datetime
from ..base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class LaggardRotationStrategy(BaseStrategy):
    """Buy the worst performing assets (mean reversion strategy)."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        params = config.get('parameters', {})
        self.lookback_days = params.get('lookback_days', 20)
        self.laggard_count = params.get('laggard_count', 1)
        self.cooldown_days = params.get('cooldown_days', 0)
        self.rebalance_frequency = config.get('rebalance_frequency', 'weekly')
        self.current_positions = set()
    
    def generate_signals(self, current_date: datetime, should_rebalance: bool = False) -> List[Dict[str, Any]]:
        """Generate signals based on laggard rotation logic."""
        signals = []
        
        if not should_rebalance:
            return signals
        
        logger.info(f"Laggard Rotation: Rebalancing on {current_date}")
        
        # Calculate returns for all assets
        asset_returns = {}
        for ticker in self.universe:
            if self.is_in_cooldown(ticker, current_date, self.cooldown_days):
                logger.debug(f"Skipping {ticker} - in cooldown")
                continue
            
            returns = self.get_returns(ticker, current_date, self.lookback_days)
            if returns is not None:
                asset_returns[ticker] = returns
                logger.debug(f"{ticker}: {returns:.2f}% return over {self.lookback_days} days")
            else:
                logger.warning(f"Could not calculate returns for {ticker}")
        
        if not asset_returns:
            logger.warning("No asset returns calculated - cannot generate signals")
            return signals
        
        # Rank by returns (worst first)
        sorted_assets = sorted(asset_returns.items(), key=lambda x: x[1])
        logger.info(f"Asset returns (worst to best): {[(t, f'{r:.2f}%') for t, r in sorted_assets]}")
        
        # Select bottom N laggards
        laggards = [ticker for ticker, _ in sorted_assets[:self.laggard_count]]
        logger.info(f"Selected laggards: {laggards}")
        
        # Accumulation strategy: Only buy laggards, never sell
        # Buy laggards (whether we already hold them or not - accumulate positions)
        for ticker in laggards:
            # Check cooldown before buying
            if self.is_in_cooldown(ticker, current_date, self.cooldown_days):
                logger.debug(f"Skipping {ticker} - in cooldown")
                continue
            
            signals.append({
                'ticker': ticker,
                'action': 'BUY',
                'amount': None,  # Will be split equally across all buys
                'reason': f'Laggard rotation (return: {asset_returns[ticker]:.2f}%)'
            })
            self.current_positions.add(ticker)
            self.record_trade(ticker, current_date)
            logger.info(f"Signal to BUY {ticker} - laggard with {asset_returns[ticker]:.2f}% return")
        
        logger.info(f"Generated {len(signals)} BUY signals for accumulation")
        return signals


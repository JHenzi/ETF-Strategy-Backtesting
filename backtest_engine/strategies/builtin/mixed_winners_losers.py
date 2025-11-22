"""Mixed Winners and Losers strategy implementation."""
from typing import Dict, List, Any
from datetime import datetime
from ..base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class MixedWinnersLosersStrategy(BaseStrategy):
    """Buy both top performers and bottom performers."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        params = config.get('parameters', {})
        self.lookback_days = params.get('lookback_days', 15)
        self.winner_count = params.get('winner_count', 1)
        self.laggard_count = params.get('laggard_count', 1)
        self.cooldown_days = params.get('cooldown_days', 0)
        self.rebalance_frequency = config.get('rebalance_frequency', 'weekly')
        self.current_positions = set()
    
    def generate_signals(self, current_date: datetime, should_rebalance: bool = False) -> List[Dict[str, Any]]:
        """Generate signals based on mixed strategy logic."""
        signals = []
        
        if not should_rebalance:
            return signals
        
        # Calculate returns for all assets
        asset_returns = {}
        for ticker in self.universe:
            if self.is_in_cooldown(ticker, current_date, self.cooldown_days):
                continue
            
            returns = self.get_returns(ticker, current_date, self.lookback_days)
            if returns is not None:
                asset_returns[ticker] = returns
        
        if not asset_returns:
            return signals
        
        # Rank by returns
        sorted_assets = sorted(asset_returns.items(), key=lambda x: x[1], reverse=True)
        
        # Select top winners and bottom laggards
        winners = [ticker for ticker, _ in sorted_assets[:self.winner_count]]
        laggards = [ticker for ticker, _ in sorted_assets[-self.laggard_count:]]
        
        target_positions = set(winners + laggards)
        
        # Accumulation strategy: Only buy target positions, never sell
        # Buy target positions (whether we already hold them or not - accumulate positions)
        for ticker in target_positions:
            # Check cooldown before buying
            if self.is_in_cooldown(ticker, current_date, self.cooldown_days):
                logger.debug(f"Skipping {ticker} - in cooldown")
                continue
            
            position_type = 'winner' if ticker in winners else 'laggard'
            signals.append({
                'ticker': ticker,
                'action': 'BUY',
                'amount': None,  # Use available cash
                'reason': f'Mixed strategy: {position_type} (return: {asset_returns[ticker]:.2f}%)'
            })
            self.current_positions.add(ticker)
            self.record_trade(ticker, current_date)
            logger.info(f"Signal to BUY {ticker} - {position_type} with {asset_returns[ticker]:.2f}% return")
        
        logger.info(f"Generated {len(signals)} BUY signals for accumulation")
        return signals


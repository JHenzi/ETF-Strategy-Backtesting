"""Dollar Cost Averaging strategy implementation."""
from typing import Dict, List, Any
from datetime import datetime
from ..base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class DCAStrategy(BaseStrategy):
    """Dollar Cost Averaging - invest fixed amount at regular intervals."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.contribution_amount = config.get('contribution_amount', 100)
        self.contribution_frequency = config.get('contribution_frequency', 'weekly')
        self.last_contribution_date = None
    
    def generate_signals(self, current_date: datetime, should_rebalance: bool = False) -> List[Dict[str, Any]]:
        """Generate signals for DCA contributions."""
        signals = []
        
        # Check if it's time for a contribution
        should_contribute = False
        
        if self.last_contribution_date is None:
            should_contribute = True
        else:
            days_since = (current_date - self.last_contribution_date).days
            
            if self.contribution_frequency == 'weekly' and days_since >= 7:
                should_contribute = True
            elif self.contribution_frequency == 'monthly' and days_since >= 30:
                should_contribute = True
            elif self.contribution_frequency == 'daily':
                should_contribute = True
        
        if should_contribute:
            # Split contribution equally across all assets
            amount_per_asset = self.contribution_amount / len(self.universe) if self.universe else 0
            
            for ticker in self.universe:
                signals.append({
                    'ticker': ticker,
                    'action': 'BUY',
                    'amount': amount_per_asset,
                    'reason': f'DCA contribution ({self.contribution_frequency})'
                })
            
            self.last_contribution_date = current_date
        
        return signals


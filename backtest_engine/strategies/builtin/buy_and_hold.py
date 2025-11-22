"""Buy and Hold strategy implementation."""
from typing import Dict, List, Any
from datetime import datetime
from ..base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class BuyAndHoldStrategy(BaseStrategy):
    """Simple buy and hold strategy - buys assets at start and holds."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.has_bought = False
    
    def generate_signals(self, current_date: datetime, should_rebalance: bool = False) -> List[Dict[str, Any]]:
        """Generate signals - only buy on first day."""
        signals = []
        
        if not self.has_bought and current_date >= self.start_date:
            # Buy all assets on first day
            for ticker in self.universe:
                signals.append({
                    'ticker': ticker,
                    'action': 'BUY',
                    'amount': None,  # Use all available cash
                    'reason': 'Buy and Hold initial purchase'
                })
            self.has_bought = True
        
        return signals


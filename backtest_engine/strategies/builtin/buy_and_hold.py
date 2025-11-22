"""Buy and Hold strategy implementation."""
from typing import Dict, List, Any
from datetime import datetime
import pandas as pd
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
        
        # Convert dates to comparable format
        current_date_pd = pd.to_datetime(current_date)
        start_date_pd = pd.to_datetime(self.start_date)
        
        if not self.has_bought and current_date_pd >= start_date_pd:
            # Buy all assets on first day
            logger.info(f"Buy and Hold: Generating buy signals for {len(self.universe)} assets on {current_date}")
            for ticker in self.universe:
                signals.append({
                    'ticker': ticker,
                    'action': 'BUY',
                    'amount': None,  # Will be split equally across all assets
                    'reason': 'Buy and Hold initial purchase'
                })
            self.has_bought = True
        
        return signals


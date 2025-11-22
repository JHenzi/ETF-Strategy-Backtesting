"""RSI Mean Reversion strategy implementation."""
from typing import Dict, List, Any
from datetime import datetime
from ..base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)


class RSIMeanReversionStrategy(BaseStrategy):
    """Buy oversold assets (RSI < threshold), sell overbought (RSI > threshold)."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        params = config.get('parameters', {})
        self.rsi_period = params.get('rsi_period', 14)
        self.oversold_threshold = params.get('oversold_threshold', 30)
        self.overbought_threshold = params.get('overbought_threshold', 70)
        self.rebalance_frequency = config.get('rebalance_frequency', 'daily')
        self.current_positions = set()
    
    def generate_signals(self, current_date: datetime, should_rebalance: bool = False) -> List[Dict[str, Any]]:
        """Generate signals based on RSI mean reversion logic."""
        signals = []
        
        if not should_rebalance:
            return signals
        
        logger.info(f"RSI Mean Reversion: Checking signals on {current_date}")
        
        # Calculate RSI for all assets
        asset_rsi = {}
        for ticker in self.universe:
            rsi = self.calculate_rsi(ticker, current_date, self.rsi_period)
            if rsi is not None:
                asset_rsi[ticker] = rsi
                logger.debug(f"{ticker}: RSI = {rsi:.2f}")
            else:
                logger.warning(f"Could not calculate RSI for {ticker}")
        
        if not asset_rsi:
            logger.warning("No RSI values calculated - cannot generate signals")
            return signals
        
        # Generate buy signals for oversold assets (RSI < oversold_threshold)
        oversold_assets = [
            ticker for ticker, rsi in asset_rsi.items()
            if rsi < self.oversold_threshold
        ]
        
        # Generate sell signals for overbought assets (RSI > overbought_threshold)
        overbought_assets = [
            ticker for ticker, rsi in asset_rsi.items()
            if rsi > self.overbought_threshold and ticker in self.current_positions
        ]
        
        logger.info(f"Oversold assets (RSI < {self.oversold_threshold}): {oversold_assets}")
        logger.info(f"Overbought assets (RSI > {self.overbought_threshold}): {overbought_assets}")
        
        # Buy oversold assets - split cash equally among all oversold assets
        for ticker in oversold_assets:
            signals.append({
                'ticker': ticker,
                'action': 'BUY',
                'amount': None,  # Will be split equally across all buys by engine
                'reason': f'RSI oversold ({asset_rsi[ticker]:.2f} < {self.oversold_threshold})'
            })
            self.current_positions.add(ticker)
            self.record_trade(ticker, current_date)
            logger.info(f"Signal to BUY {ticker} - RSI {asset_rsi[ticker]:.2f} < {self.oversold_threshold}")
        
        # Sell overbought assets (sell all shares)
        for ticker in overbought_assets:
            signals.append({
                'ticker': ticker,
                'action': 'SELL',
                'shares': None,  # Sell all shares
                'reason': f'RSI overbought ({asset_rsi[ticker]:.2f} > {self.overbought_threshold})'
            })
            self.current_positions.discard(ticker)
            self.record_trade(ticker, current_date)
            logger.info(f"Signal to SELL {ticker} - RSI {asset_rsi[ticker]:.2f} > {self.overbought_threshold}")
        
        logger.info(f"Generated {len(signals)} signals ({len(oversold_assets)} buys, {len(overbought_assets)} sells)")
        return signals


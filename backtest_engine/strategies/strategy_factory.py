"""Factory for creating strategy instances from YAML config."""
from typing import Dict, Any
from .yaml_schema import StrategyLoader
from .base_strategy import BaseStrategy
from .builtin.buy_and_hold import BuyAndHoldStrategy
from .builtin.dca import DCAStrategy
from .builtin.laggard_rotation import LaggardRotationStrategy
from .builtin.momentum_winner import MomentumWinnerStrategy
from .builtin.mixed_winners_losers import MixedWinnersLosersStrategy
from .builtin.rsi_mean_reversion import RSIMeanReversionStrategy
import logging

logger = logging.getLogger(__name__)


class StrategyFactory:
    """Factory for creating strategy instances."""
    
    STRATEGY_CLASSES = {
        'buy_and_hold': BuyAndHoldStrategy,
        'dca': DCAStrategy,
        'laggard_rotation': LaggardRotationStrategy,
        'momentum_winner': MomentumWinnerStrategy,
        'mixed_winners_losers': MixedWinnersLosersStrategy,
        'rsi_mean_reversion': RSIMeanReversionStrategy,
    }
    
    def __init__(self):
        """Initialize the strategy factory."""
        self.loader = StrategyLoader()
    
    def create_strategy(
        self, 
        file_path: str = None, 
        yaml_string: str = None,
        config_dict: Dict[str, Any] = None
    ) -> BaseStrategy:
        """
        Create a strategy instance from YAML or config dict.
        
        Args:
            file_path: Path to YAML file
            yaml_string: YAML string
            config_dict: Strategy config dictionary
            
        Returns:
            Strategy instance
        """
        if config_dict is None:
            if file_path:
                result = self.loader.load_and_validate(file_path=file_path)
                config_dict = result['strategy']
            elif yaml_string:
                result = self.loader.load_and_validate(yaml_string=yaml_string)
                config_dict = result['strategy']
            else:
                raise ValueError("Must provide file_path, yaml_string, or config_dict")
        else:
            # Validate config dict
            validation = self.loader.validate_strategy(config_dict)
            if not validation['valid']:
                error_msg = "Strategy validation failed:\n" + "\n".join(validation['errors'])
                raise ValueError(error_msg)
        
        strategy_name = config_dict.get('name')
        
        if strategy_name not in self.STRATEGY_CLASSES:
            raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(self.STRATEGY_CLASSES.keys())}")
        
        strategy_class = self.STRATEGY_CLASSES[strategy_name]
        strategy = strategy_class(config_dict)
        
        # Set rebalance_frequency if specified
        if 'rebalance_frequency' in config_dict:
            strategy.rebalance_frequency = config_dict['rebalance_frequency']
        
        return strategy


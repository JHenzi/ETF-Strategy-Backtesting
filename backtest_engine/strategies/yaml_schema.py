"""
YAML strategy schema validator and parser.
"""
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class StrategySchemaValidator:
    """Validates YAML strategy files against schema."""
    
    REQUIRED_FIELDS = ['name', 'universe']
    OPTIONAL_FIELDS = [
        'description', 'parameters', 'position_sizing', 'execution',
        'cash', 'rebalance_frequency', 'metrics'
    ]
    
    SUPPORTED_STRATEGIES = [
        'buy_and_hold', 'dca', 'laggard_rotation', 'momentum_winner',
        'mixed_winners_losers', 'rsi_mean_reversion', 'equal_weight_rebalance',
        'relative_strength', 'buy_the_dip', 'sma_crossover'
    ]
    
    SUPPORTED_INDICATORS = ['rsi', 'sma', 'momentum', 'returns']
    
    def validate(self, strategy_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a strategy dictionary.
        
        Returns:
            Dict with 'valid' (bool), 'errors' (list), 'warnings' (list)
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in strategy_dict:
                errors.append(f"Missing required field: {field}")
        
        # Validate name
        if 'name' in strategy_dict:
            name = strategy_dict['name']
            if name not in self.SUPPORTED_STRATEGIES:
                warnings.append(f"Strategy name '{name}' not in built-in strategies. Will attempt to load as custom.")
        
        # Validate universe
        if 'universe' in strategy_dict:
            universe = strategy_dict['universe']
            if not isinstance(universe, list) or len(universe) == 0:
                errors.append("'universe' must be a non-empty list of tickers")
            else:
                for ticker in universe:
                    if not isinstance(ticker, str) or len(ticker) == 0:
                        errors.append(f"Invalid ticker in universe: {ticker}")
        
        # Validate parameters based on strategy type
        if 'name' in strategy_dict and 'parameters' in strategy_dict:
            param_errors = self._validate_parameters(
                strategy_dict['name'],
                strategy_dict['parameters']
            )
            errors.extend(param_errors)
        
        # Validate position_sizing
        if 'position_sizing' in strategy_dict:
            ps = strategy_dict['position_sizing']
            valid_sizing = ['equal_weight', 'single_asset', 'all_in_on_signal']
            if isinstance(ps, str) and ps not in valid_sizing:
                warnings.append(f"Unknown position_sizing: {ps}. Using equal_weight.")
        
        # Validate execution
        if 'execution' in strategy_dict:
            exec_val = strategy_dict['execution']
            valid_exec = ['next_open', 'market_close', 'same_day', 'first_day_only']
            if isinstance(exec_val, str) and exec_val not in valid_exec:
                warnings.append(f"Unknown execution: {exec_val}. Using next_open.")
        
        # Validate rebalance_frequency
        if 'rebalance_frequency' in strategy_dict:
            freq = strategy_dict['rebalance_frequency']
            valid_freqs = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']
            if freq not in valid_freqs:
                warnings.append(f"Unknown rebalance_frequency: {freq}. Using weekly.")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_parameters(self, strategy_name: str, parameters: Dict[str, Any]) -> List[str]:
        """Validate parameters for a specific strategy type."""
        errors = []
        
        # Strategy-specific parameter validation
        if strategy_name == 'laggard_rotation':
            required = ['lookback_days', 'laggard_count']
            for param in required:
                if param not in parameters:
                    errors.append(f"Missing required parameter for {strategy_name}: {param}")
        
        elif strategy_name == 'momentum_winner':
            required = ['lookback_days', 'winner_count']
            for param in required:
                if param not in parameters:
                    errors.append(f"Missing required parameter for {strategy_name}: {param}")
        
        elif strategy_name == 'mixed_winners_losers':
            required = ['lookback_days', 'winner_count', 'laggard_count']
            for param in required:
                if param not in parameters:
                    errors.append(f"Missing required parameter for {strategy_name}: {param}")
        
        elif strategy_name == 'rsi_mean_reversion':
            required = ['rsi_period']
            for param in required:
                if param not in parameters:
                    errors.append(f"Missing required parameter for {strategy_name}: {param}")
        
        elif strategy_name == 'relative_strength':
            required = ['lookback_days', 'benchmark']
            for param in required:
                if param not in parameters:
                    errors.append(f"Missing required parameter for {strategy_name}: {param}")
        
        elif strategy_name == 'buy_the_dip':
            required = ['max_drawdown_lookback', 'buy_threshold']
            for param in required:
                if param not in parameters:
                    errors.append(f"Missing required parameter for {strategy_name}: {param}")
        
        elif strategy_name == 'sma_crossover':
            required = ['short_window', 'long_window']
            for param in required:
                if param not in parameters:
                    errors.append(f"Missing required parameter for {strategy_name}: {param}")
        
        # Check for unsupported indicators
        if 'indicator' in parameters:
            indicator = parameters['indicator']
            if indicator not in self.SUPPORTED_INDICATORS:
                errors.append(f"Unsupported indicator: {indicator}. Supported: {', '.join(self.SUPPORTED_INDICATORS)}")
        
        return errors


class StrategyLoader:
    """Loads and parses YAML strategy files."""
    
    def __init__(self):
        """Initialize the strategy loader."""
        self.validator = StrategySchemaValidator()
    
    def load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load a strategy from a YAML file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Strategy file not found: {file_path}")
        
        with open(path, 'r') as f:
            strategy_dict = yaml.safe_load(f)
        
        return strategy_dict
    
    def load_from_string(self, yaml_string: str) -> Dict[str, Any]:
        """Load a strategy from a YAML string."""
        strategy_dict = yaml.safe_load(yaml_string)
        return strategy_dict
    
    def validate_strategy(self, strategy_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a strategy dictionary."""
        return self.validator.validate(strategy_dict)
    
    def load_and_validate(self, file_path: Optional[str] = None, yaml_string: Optional[str] = None) -> Dict[str, Any]:
        """
        Load and validate a strategy.
        
        Returns:
            Dict with 'strategy' (dict), 'validation' (dict)
        """
        if file_path:
            strategy_dict = self.load_from_file(file_path)
        elif yaml_string:
            strategy_dict = self.load_from_string(yaml_string)
        else:
            raise ValueError("Must provide either file_path or yaml_string")
        
        validation = self.validate_strategy(strategy_dict)
        
        if not validation['valid']:
            error_msg = "Strategy validation failed:\n" + "\n".join(validation['errors'])
            raise ValueError(error_msg)
        
        if validation['warnings']:
            logger.warning("Strategy validation warnings:\n" + "\n".join(validation['warnings']))
        
        return {
            'strategy': strategy_dict,
            'validation': validation
        }


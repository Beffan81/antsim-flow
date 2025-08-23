"""Queen implementation with blackboard-based state management."""
import logging
from typing import Dict, Any, Optional, Tuple

from .blackboard import Blackboard

logger = logging.getLogger(__name__)


class Queen:
    """Queen agent with blackboard for state management and egg laying capabilities."""
    
    def __init__(self, queen_id: int, position: Tuple[int, int], config: Optional[Dict[str, Any]] = None):
        """Initialize queen with blackboard.
        
        Args:
            queen_id: Unique queen identifier (typically 0)
            position: Initial position (x, y)
            config: Optional queen configuration
        """
        self.id = queen_id
        self.blackboard = Blackboard(queen_id)
        
        # Store minimal bootstrap config (if needed by plugins)
        self._config = config or {}
        
        # Initialize blackboard with queen-specific state
        self._initialize_blackboard(position)
        
        logger.info(f"Queen {queen_id} initialized at position {position}")
    
    def _initialize_blackboard(self, position: Tuple[int, int]) -> None:
        """Initialize blackboard with queen-specific state."""
        # Essential queen state
        self.blackboard.set('position', list(position))  # Store as list for JSON
        self.blackboard.set('has_moved', False)
        
        # Queen-specific attributes
        self.blackboard.set('egg_laying_interval', self._config.get('egg_laying_interval', 10))
        self.blackboard.set('eggs_laid', 0)
        self.blackboard.set('last_egg_tick', 0)
        self.blackboard.set('max_eggs', self._config.get('max_eggs', 100))
        
        # Energy and food capacity (queens typically have higher capacity)
        self.blackboard.set('energy', self._config.get('energy', 200))
        self.blackboard.set('max_energy', self._config.get('max_energy', 200))
        self.blackboard.set('social_stomach', self._config.get('social_stomach', 150))
        self.blackboard.set('social_stomach_capacity', self._config.get('social_stomach_capacity', 150))
        
        # Commit initial state
        self.blackboard.commit()
    
    @property
    def position(self) -> Tuple[int, int]:
        """Get current position from blackboard."""
        pos = self.blackboard.get('position', [0, 0])
        return tuple(pos)
    
    @position.setter
    def position(self, value: Tuple[int, int]) -> None:
        """Set position in blackboard."""
        self.blackboard.set('position', list(value))
    
    def update_from_sensors(self, sensor_data: Dict[str, Any]) -> None:
        """Update blackboard from sensor data.
        
        Args:
            sensor_data: Dictionary of sensor readings
        """
        # Simply merge all sensor data into blackboard
        for key, value in sensor_data.items():
            self.blackboard.set(key, value)
        
        logger.debug(f"Queen {self.id} updated with {len(sensor_data)} sensor values")
    
    def reset_cycle(self) -> None:
        """Reset per-cycle flags."""
        self.blackboard.set('has_moved', False)
        # Other cycle resets can be added by sensors/plugins
    
    def can_lay_egg(self, current_tick: int) -> bool:
        """Check if queen can lay an egg this tick."""
        last_egg = self.blackboard.get('last_egg_tick', 0)
        interval = self.blackboard.get('egg_laying_interval', 10)
        eggs_laid = self.blackboard.get('eggs_laid', 0)
        max_eggs = self.blackboard.get('max_eggs', 100)
        
        return (current_tick - last_egg >= interval and 
                eggs_laid < max_eggs)
    
    def lay_egg(self, current_tick: int) -> bool:
        """Lay an egg if possible."""
        if self.can_lay_egg(current_tick):
            self.blackboard.set('last_egg_tick', current_tick)
            eggs_laid = self.blackboard.get('eggs_laid', 0)
            self.blackboard.set('eggs_laid', eggs_laid + 1)
            logger.info(f"Queen {self.id} laid egg #{eggs_laid + 1} at tick {current_tick}")
            return True
        return False
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state for logging."""
        # Get all state from blackboard
        state = self.blackboard.to_dict()
        
        # Add computed summary info
        return {
            'id': self.id,
            'type': 'queen',
            'position': self.position,
            'eggs_laid': self.blackboard.get('eggs_laid', 0),
            'energy': self.blackboard.get('energy', 0),
            'social_stomach': self.blackboard.get('social_stomach', 0),
            'blackboard_keys': len(self.blackboard.keys()),
            'pending_changes': len(self.blackboard.diff())
        }
    
    def __repr__(self) -> str:
        """String representation."""
        pos = self.position
        eggs = self.blackboard.get('eggs_laid', 0)
        return f"Queen(id={self.id}, pos={pos}, eggs={eggs})"
    
    def __getattr__(self, name: str) -> Any:
        """Fallback to blackboard for attribute access.
        
        This allows legacy compatibility while encouraging BB usage.
        """
        if name.startswith('_'):
            raise AttributeError(f"Queen has no attribute '{name}'")
        
        # Try to get from blackboard
        value = self.blackboard.get(name, None)
        if value is not None:
            return value
        
        # Check config for defaults
        if name in self._config:
            return self._config[name]
            
        raise AttributeError(f"Queen has no attribute '{name}' in blackboard or config")
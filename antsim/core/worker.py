"""New Worker implementation with blackboard-based state management."""
import logging
from typing import Dict, Any, Optional, Tuple

from .blackboard import Blackboard

logger = logging.getLogger(__name__)


class Worker:
    """Worker agent with blackboard for state management."""
    
    def __init__(self, worker_id: int, position: Tuple[int, int], config: Optional[Dict[str, Any]] = None):
        """Initialize worker with blackboard.
        
        Args:
            worker_id: Unique worker identifier
            position: Initial position (x, y)
            config: Optional worker configuration
        """
        self.id = worker_id
        self.blackboard = Blackboard(worker_id)
        
        # Store minimal bootstrap config (if needed by plugins)
        self._config = config or {}
        
        # Initialize blackboard with minimal state
        self._initialize_blackboard(position)
        
        logger.info(f"Worker {worker_id} initialized at position {position}")
    
    def _initialize_blackboard(self, position: Tuple[int, int]) -> None:
        """Initialize blackboard with minimal worker state."""
        # Only essential bootstrap state - domain specifics come from sensors
        self.blackboard.set('position', list(position))  # Store as list for JSON
        self.blackboard.set('has_moved', False)
        
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
        
        logger.debug(f"Worker {self.id} updated with {len(sensor_data)} sensor values")
    
    def reset_cycle(self) -> None:
        """Reset per-cycle flags."""
        self.blackboard.set('has_moved', False)
        # Other cycle resets can be added by sensors/plugins
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state for logging."""
        # Get all state from blackboard
        state = self.blackboard.to_dict()
        
        # Add computed summary info
        return {
            'id': self.id,
            'position': self.position,
            'blackboard_keys': len(self.blackboard.keys()),
            'pending_changes': len(self.blackboard.diff())
        }
    
    def __repr__(self) -> str:
        """String representation."""
        pos = self.position
        keys = len(self.blackboard.keys())
        return f"Worker(id={self.id}, pos={pos}, bb_keys={keys})"
    
    def __getattr__(self, name: str) -> Any:
        """Fallback to blackboard for attribute access.
        
        This allows legacy compatibility while encouraging BB usage.
        """
        if name.startswith('_'):
            raise AttributeError(f"Worker has no attribute '{name}'")
        
        # Try to get from blackboard
        value = self.blackboard.get(name, None)
        if value is not None:
            return value
        
        # Check config for defaults
        if name in self._config:
            return self._config[name]
            
        raise AttributeError(f"Worker has no attribute '{name}' in blackboard or config")

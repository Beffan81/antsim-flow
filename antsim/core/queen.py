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
    
    def process_energy_cycle(self, current_tick: int) -> Dict[str, Any]:
        """Process energy conversion, loss, and hunger signaling.
        
        Returns:
            Dict with processing results and intents
        """
        results = {
            'energy_converted': 0,
            'energy_lost': 0,
            'stomach_depleted': 0,
            'is_alive': True,
            'is_signaling_hunger': False,
            'intents': []
        }
        
        # Get current state
        energy = self.blackboard.get('energy', 0)
        max_energy = self.blackboard.get('max_energy', 200)
        stomach = self.blackboard.get('social_stomach', 0)
        
        conversion_rate = self._config.get('energy_conversion_rate', 8)
        loss_rate = self._config.get('energy_loss_rate', 3)
        depletion_rate = self._config.get('stomach_depletion_rate', 5)
        
        # Energy conversion from stomach
        if stomach > 0:
            conversion_amount = min(stomach, conversion_rate)
            energy_gain = min(conversion_amount, max_energy - energy)
            
            self.blackboard.set('energy', energy + energy_gain)
            self.blackboard.set('social_stomach', stomach - conversion_amount)
            
            results['energy_converted'] = energy_gain
            results['stomach_depleted'] = conversion_amount
            
        # Energy loss when stomach empty
        else:
            energy_loss = min(energy, loss_rate)
            new_energy = energy - energy_loss
            self.blackboard.set('energy', new_energy)
            
            results['energy_lost'] = energy_loss
            
            # Death check
            if new_energy <= 0:
                results['is_alive'] = False
                logger.info(f"Queen {self.id} died from starvation at tick {current_tick}")
                return results
        
        # Hunger signaling via pheromones
        current_energy = self.blackboard.get('energy', 0)
        if current_energy < max_energy:
            # Import here to avoid circular imports
            try:
                from .executor import DepositPheromoneIntent
                
                strength = self._config.get('hunger_pheromone_strength', 3)
                hunger_intent = DepositPheromoneIntent(ptype="hunger", strength=strength)
                results['intents'].append(hunger_intent)
                results['is_signaling_hunger'] = True
                
                self.blackboard.set('is_signaling_hunger', True)
                
            except ImportError:
                # Fallback to dict format
                results['intents'].append({
                    "type": "PHEROMONE", 
                    "payload": {"ptype": "hunger", "strength": 3}
                })
                results['is_signaling_hunger'] = True
        else:
            self.blackboard.set('is_signaling_hunger', False)
        
        return results

    def can_lay_egg(self, current_tick: int) -> bool:
        """Check if queen can lay an egg this tick (requires 100% energy)."""
        last_egg = self.blackboard.get('last_egg_tick', 0)
        interval = self.blackboard.get('egg_laying_interval', 10)
        eggs_laid = self.blackboard.get('eggs_laid', 0)
        max_eggs = self.blackboard.get('max_eggs', 100)
        
        # NEW: Require 100% energy for egg laying
        energy = self.blackboard.get('energy', 0)
        max_energy = self.blackboard.get('max_energy', 200)
        has_full_energy = energy >= max_energy
        
        return (current_tick - last_egg >= interval and 
                eggs_laid < max_eggs and
                has_full_energy)
    
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
"""Brood/Egg implementation with energy-based growth mechanics."""
import logging
from typing import Dict, Any, Optional, Tuple

from .blackboard import Blackboard

logger = logging.getLogger(__name__)


class Brood:
    """Brood (egg/larva) with energy-based growth and maturation."""
    
    def __init__(self, brood_id: int, position: Tuple[int, int], config: Optional[Dict[str, Any]] = None):
        """Initialize brood with blackboard.
        
        Args:
            brood_id: Unique brood identifier
            position: Initial position (x, y)
            config: Optional brood configuration
        """
        self.id = brood_id
        self.blackboard = Blackboard(brood_id)
        self._config = config or {}
        
        # Initialize blackboard with brood-specific state
        self._initialize_blackboard(position)
        
        logger.info(f"Brood {brood_id} created at position {position}")
    
    def _initialize_blackboard(self, position: Tuple[int, int]) -> None:
        """Initialize blackboard with brood-specific state."""
        # Essential brood state
        self.blackboard.set('position', list(position))
        self.blackboard.set('type', 'brood')
        
        # Energy and food
        self.blackboard.set('energy', self._config.get('initial_energy', 50))
        self.blackboard.set('max_energy', self._config.get('max_energy', 100))
        self.blackboard.set('social_stomach', self._config.get('initial_stomach', 0))
        self.blackboard.set('social_stomach_capacity', self._config.get('stomach_capacity', 80))
        
        # Growth mechanics
        self.blackboard.set('growth_progress', 0)
        self.blackboard.set('maturation_time', self._config.get('maturation_time', 50))
        self.blackboard.set('created_tick', 0)
        
        # Energy processing rates
        self.blackboard.set('energy_conversion_rate', self._config.get('energy_conversion_rate', 5))
        self.blackboard.set('energy_loss_rate', self._config.get('energy_loss_rate', 2))
        self.blackboard.set('stomach_depletion_rate', self._config.get('stomach_depletion_rate', 3))
        
        # Hunger signaling
        self.blackboard.set('hunger_pheromone_strength', self._config.get('hunger_pheromone_strength', 2))
        self.blackboard.set('is_signaling_hunger', False)
        
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
        max_energy = self.blackboard.get('max_energy', 100)
        stomach = self.blackboard.get('social_stomach', 0)
        
        conversion_rate = self.blackboard.get('energy_conversion_rate', 5)
        loss_rate = self.blackboard.get('energy_loss_rate', 2)
        depletion_rate = self.blackboard.get('stomach_depletion_rate', 3)
        
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
                logger.info(f"Brood {self.id} died from starvation at tick {current_tick}")
                return results
        
        # Hunger signaling via pheromones
        current_energy = self.blackboard.get('energy', 0)
        if current_energy < max_energy:
            # Import here to avoid circular imports
            try:
                from .executor import DepositPheromoneIntent
                
                strength = self.blackboard.get('hunger_pheromone_strength', 2)
                hunger_intent = DepositPheromoneIntent(ptype="hunger", strength=strength)
                results['intents'].append(hunger_intent)
                results['is_signaling_hunger'] = True
                
                self.blackboard.set('is_signaling_hunger', True)
                
            except ImportError:
                # Fallback to dict format
                results['intents'].append({
                    "type": "PHEROMONE",
                    "payload": {"ptype": "hunger", "strength": 2}
                })
                results['is_signaling_hunger'] = True
        else:
            self.blackboard.set('is_signaling_hunger', False)
        
        return results
    
    def can_grow(self) -> bool:
        """Check if brood can grow (needs 100% energy)."""
        energy = self.blackboard.get('energy', 0)
        max_energy = self.blackboard.get('max_energy', 100)
        return energy >= max_energy
    
    def grow(self, current_tick: int) -> bool:
        """Grow the brood if possible."""
        if not self.can_grow():
            return False
        
        growth = self.blackboard.get('growth_progress', 0)
        self.blackboard.set('growth_progress', growth + 1)
        
        logger.debug(f"Brood {self.id} grew to {growth + 1} at tick {current_tick}")
        return True
    
    def can_mature(self, current_tick: int) -> bool:
        """Check if brood is ready to mature into worker."""
        growth = self.blackboard.get('growth_progress', 0)
        maturation_time = self.blackboard.get('maturation_time', 50)
        return growth >= maturation_time
    
    def update_from_sensors(self, sensor_data: Dict[str, Any]) -> None:
        """Update blackboard from sensor data."""
        for key, value in sensor_data.items():
            self.blackboard.set(key, value)
        
        logger.debug(f"Brood {self.id} updated with {len(sensor_data)} sensor values")
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state for logging."""
        return {
            'id': self.id,
            'type': 'brood',
            'position': self.position,
            'energy': self.blackboard.get('energy', 0),
            'max_energy': self.blackboard.get('max_energy', 100),
            'social_stomach': self.blackboard.get('social_stomach', 0),
            'growth_progress': self.blackboard.get('growth_progress', 0),
            'maturation_time': self.blackboard.get('maturation_time', 50),
            'is_signaling_hunger': self.blackboard.get('is_signaling_hunger', False),
            'blackboard_keys': len(self.blackboard.keys()),
            'pending_changes': len(self.blackboard.diff())
        }
    
    def __repr__(self) -> str:
        """String representation."""
        pos = self.position
        energy = self.blackboard.get('energy', 0)
        growth = self.blackboard.get('growth_progress', 0)
        return f"Brood(id={self.id}, pos={pos}, energy={energy}, growth={growth})"
    
    def __getattr__(self, name: str) -> Any:
        """Fallback to blackboard for attribute access."""
        if name.startswith('_'):
            raise AttributeError(f"Brood has no attribute '{name}'")
        
        # Try to get from blackboard
        value = self.blackboard.get(name, None)
        if value is not None:
            return value
        
        # Check config for defaults
        if name in self._config:
            return self._config[name]
            
        raise AttributeError(f"Brood has no attribute '{name}' in blackboard or config")
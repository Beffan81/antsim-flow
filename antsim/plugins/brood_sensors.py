"""Brood-specific sensors for energy monitoring and hunger detection."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
log = logging.getLogger(__name__)


@hookimpl
def register_sensors() -> Dict[str, Any]:
    """Register brood-specific sensors."""
    return {
        "brood_energy_level": brood_energy_level_sensor,
        "brood_hunger_status": brood_hunger_status_sensor,
        "brood_growth_progress": brood_growth_progress_sensor,
        "brood_maturation_ready": brood_maturation_ready_sensor,
    }


def _bb_get(obj: Any, key: str, default=None):
    """Safe blackboard/attribute getter."""
    if hasattr(obj, 'blackboard') and hasattr(obj.blackboard, 'get'):
        return obj.blackboard.get(key, default)
    return getattr(obj, key, default)


def brood_energy_level_sensor(brood: Any, environment: Any, **kwargs) -> float:
    """Get brood's current energy level as percentage.
    
    Returns:
        Energy level as percentage (0.0 - 1.0)
    """
    energy = _bb_get(brood, 'energy', 0)
    max_energy = _bb_get(brood, 'max_energy', 100)
    
    if max_energy <= 0:
        return 0.0
    
    return min(1.0, max(0.0, energy / max_energy))


def brood_hunger_status_sensor(brood: Any, environment: Any, **kwargs) -> bool:
    """Check if brood is hungry (not at full energy).
    
    Returns:
        True if brood needs feeding, False otherwise
    """
    energy = _bb_get(brood, 'energy', 0)
    max_energy = _bb_get(brood, 'max_energy', 100)
    
    return energy < max_energy


def brood_growth_progress_sensor(brood: Any, environment: Any, **kwargs) -> float:
    """Get brood's growth progress as percentage.
    
    Returns:
        Growth progress as percentage (0.0 - 1.0)
    """
    growth = _bb_get(brood, 'growth_progress', 0)
    maturation_time = _bb_get(brood, 'maturation_time', 50)
    
    if maturation_time <= 0:
        return 1.0
    
    return min(1.0, max(0.0, growth / maturation_time))


def brood_maturation_ready_sensor(brood: Any, environment: Any, **kwargs) -> bool:
    """Check if brood is ready to mature into worker.
    
    Returns:
        True if brood can become worker, False otherwise
    """
    growth = _bb_get(brood, 'growth_progress', 0)
    maturation_time = _bb_get(brood, 'maturation_time', 50)
    
    return growth >= maturation_time
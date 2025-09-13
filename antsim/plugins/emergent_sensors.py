# plugins/emergent_sensors.py
"""Emergent behavior sensors for direct communication and trail reinforcement."""
import logging
from typing import Any, Dict, Tuple, List, Optional
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
logger = logging.getLogger(__name__)


@hookimpl
def register_sensors() -> Dict[str, callable]:
    """Expose emergent behavior sensors."""
    return {
        "direct_feeding_opportunity": direct_feeding_opportunity_sensor,
        "track_foraging_success": track_foraging_success_sensor,
        "hunger_pheromone_response": hunger_pheromone_response_sensor,
    }


# Configuration cache for emergent behavior parameters
_emergent_config = None

def set_emergent_config(config):
    """Set emergent behavior configuration parameters."""
    global _emergent_config
    _emergent_config = config

def _get_config_value(key: str, default):
    """Get configuration value or return default."""
    if _emergent_config and hasattr(_emergent_config, key):
        return getattr(_emergent_config, key)
    return default


def _bb_get(obj: Any, key: str, default=None):
    """Safe getter for blackboard or worker attributes."""
    bb = getattr(obj, "blackboard", None)
    if bb and hasattr(bb, "get"):
        try:
            return bb.get(key, default)
        except Exception:
            pass
    return getattr(obj, key, default)


def _bb_pos(worker: Any) -> Tuple[int, int]:
    """Get worker position."""
    pos = _bb_get(worker, "position", [0, 0])
    if isinstance(pos, (list, tuple)) and len(pos) == 2:
        return int(pos[0]), int(pos[1])
    return 0, 0


def _neighbors8(x: int, y: int) -> List[Tuple[int, int]]:
    """Get 8-neighbor positions."""
    return [
        (x-1, y-1), (x, y-1), (x+1, y-1),
        (x-1, y), (x+1, y),
        (x-1, y+1), (x, y+1), (x+1, y+1)
    ]


def _get_neighbors_in_range(x: int, y: int, range_val: int) -> List[Tuple[int, int]]:
    """Get all neighbor positions within a given range."""
    neighbors = []
    for dx in range(-range_val, range_val + 1):
        for dy in range(-range_val, range_val + 1):
            if dx == 0 and dy == 0:
                continue  # Skip center
            neighbors.append((x + dx, y + dy))
    return neighbors


def _env_has_lookup(env: Any) -> bool:
    """Check if environment supports position lookups."""
    return hasattr(env, "get_ant_at_position") and hasattr(env, "width") and hasattr(env, "height")


def direct_feeding_opportunity_sensor(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Detects direct feeding opportunities through tactile contact.
    Returns True if worker has social food AND there's a hungry neighbor in direct contact.
    """
    if not _env_has_lookup(environment):
        logger.debug("sensor=direct_feeding_opportunity reason=env-missing skipped")
        return {"direct_feeding_opportunity": False, "direct_feed_target_id": None}
    
    # Check if worker has social food
    social_food = _bb_get(worker, "social_stomach", 0)
    if social_food <= 0:
        logger.debug("sensor=direct_feeding_opportunity worker_id=%s no_social_food", getattr(worker, "id", "?"))
        return {"direct_feeding_opportunity": False, "direct_feed_target_id": None}
    
    # Check neighbors for hunger
    x, y = _bb_pos(worker)
    hungriest_neighbor = None
    best_hunger_ratio = _get_config_value('hunger_detection_threshold', 1.1)  # Configurable threshold
    
    # Use configurable feeding range (default 1 = 8-neighborhood)
    feeding_range = _get_config_value('direct_feeding_range', 1)
    neighbors = _neighbors8(x, y) if feeding_range == 1 else _get_neighbors_in_range(x, y, feeding_range)
    
    for nx, ny in neighbors:
        neighbor = environment.get_ant_at_position(nx, ny)
        if neighbor is None:
            continue
            
        # Check if neighbor is hungry
        neighbor_stomach = _bb_get(neighbor, "individual_stomach", 0)
        neighbor_threshold = _bb_get(neighbor, "hunger_threshold", 50)
        
        if neighbor_stomach < neighbor_threshold:
            hunger_ratio = float(neighbor_stomach) / float(neighbor_threshold) if neighbor_threshold > 0 else 0.0
            if hunger_ratio < best_hunger_ratio:
                best_hunger_ratio = hunger_ratio
                hungriest_neighbor = neighbor
    
    has_opportunity = hungriest_neighbor is not None
    target_id = getattr(hungriest_neighbor, "id", None) if hungriest_neighbor else None
    
    logger.debug("sensor=direct_feeding_opportunity worker_id=%s opportunity=%s target_id=%s hunger_ratio=%.2f", 
                getattr(worker, "id", "?"), has_opportunity, target_id, best_hunger_ratio)
    
    return {
        "direct_feeding_opportunity": has_opportunity,
        "direct_feed_target_id": target_id
    }


def track_foraging_success_sensor(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Tracks foraging success for trail reinforcement.
    Returns trail_success_multiplier based on recent foraging outcomes.
    """
    # Check if worker just found food after following pheromones
    followed_pheromone = _bb_get(worker, "followed_pheromone_last_turn", False)
    found_food = _bb_get(worker, "food_detected", False)
    social_stomach = _bb_get(worker, "social_stomach", 0)
    
    # Determine success multiplier
    trail_success_multiplier = 1.0
    
    if followed_pheromone:
        if found_food and social_stomach > 0:
            # Success: followed pheromone and found food
            trail_success_multiplier = _get_config_value('trail_success_multiplier', 2.0)
            logger.debug("sensor=track_foraging_success worker_id=%s trail_success=HIGH", getattr(worker, "id", "?"))
        else:
            # Failure: followed pheromone but no food found
            trail_success_multiplier = _get_config_value('trail_failure_multiplier', 0.5)
            logger.debug("sensor=track_foraging_success worker_id=%s trail_success=LOW", getattr(worker, "id", "?"))
    else:
        # Normal case: no pheromone following
        logger.debug("sensor=track_foraging_success worker_id=%s trail_success=NORMAL", getattr(worker, "id", "?"))
    
    return {
        "trail_success_multiplier": trail_success_multiplier,
        "followed_pheromone_success": followed_pheromone and found_food
    }


def hunger_pheromone_response_sensor(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Detects hunger pheromones from Queen/Brood in nearby area.
    Returns position and strength of strongest hunger pheromone signal.
    """
    if not _env_has_lookup(environment):
        logger.debug("sensor=hunger_pheromone_response reason=env-missing skipped")
        return {
            "hunger_pheromone_detected": False,
            "hunger_pheromone_position": None,
            "hunger_pheromone_strength": 0
        }
    
    x, y = _bb_pos(worker)
    max_range = _get_config_value('hunger_pheromone_detection_range', 3)  # Configurable detection range
    
    best_position = None
    best_strength = 0
    
    # Scan in expanding rings for hunger pheromones
    for radius in range(1, max_range + 1):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if abs(dx) + abs(dy) != radius:  # Only check ring boundary
                    continue
                    
                nx, ny = x + dx, y + dy
                
                # Check bounds
                if not (0 <= nx < environment.width and 0 <= ny < environment.height):
                    continue
                
                try:
                    cell = environment.grid[ny][nx]
                    if hasattr(cell, "pheromones") and isinstance(cell.pheromones, dict):
                        hunger_level = cell.pheromones.get("hunger", 0)
                        if hunger_level > best_strength:
                            best_strength = hunger_level
                            best_position = [nx, ny]
                except Exception:
                    continue
        
        # Stop at first ring with pheromones (closest)
        if best_position:
            break
    
    detected = best_position is not None
    logger.debug("sensor=hunger_pheromone_response worker_id=%s detected=%s pos=%s strength=%s", 
                getattr(worker, "id", "?"), detected, best_position, best_strength)
    
    return {
        "hunger_pheromone_detected": detected,
        "hunger_pheromone_position": best_position,
        "hunger_pheromone_strength": best_strength
    }
# FILE: antsim/plugins/foraging_steps.py
"""Foraging step plugins for comprehensive ant foraging behavior."""
import logging
import random
from typing import Any, Dict, Optional, Tuple, List
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
logger = logging.getLogger(__name__)


@hookimpl
def register_steps() -> Dict[str, callable]:
    """Expose foraging steps."""
    return {
        "leave_nest_advanced": leave_nest_step,
        "spiral_search": spiral_search_step,
        "move_to_food_advanced": move_to_food_step,
        "collect_and_eat": collect_and_eat_step,
        "return_to_nest_advanced": return_to_nest_step,
        "deposit_trail_pheromone": deposit_trail_pheromone_step,
    }


def _safe_pos(worker: Any) -> Tuple[int, int]:
    """Get worker position safely."""
    if hasattr(worker, "position"):
        pos = getattr(worker, "position")
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            return int(pos[0]), int(pos[1])
    bb = getattr(worker, "blackboard", None)
    if bb:
        pos = bb.get("position", [0, 0])
        return int(pos[0]), int(pos[1])
    return 0, 0


def _bb_get(obj: Any, key: str, default=None):
    """Safe getter from blackboard or attributes."""
    bb = getattr(obj, "blackboard", None)
    if bb and hasattr(bb, "get"):
        try:
            return bb.get(key, default)
        except Exception:
            pass
    return getattr(obj, key, default)


def _create_move_intent(target_pos: List[int], reason: str = "foraging") -> Dict[str, Any]:
    """Create a movement intent."""
    return {
        "type": "MOVE",
        "target_position": target_pos,
        "reason": reason,
    }


def leave_nest_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Move worker from nest towards the nearest exit.
    """
    wid = getattr(worker, "id", "?")
    pos = _safe_pos(worker)
    
    # Check if already outside nest
    in_nest = _bb_get(worker, "in_nest", False)
    if not in_nest:
        logger.debug("step=leave_nest worker=%s status=already_outside pos=%s", wid, pos)
        return {"status": "SUCCESS"}
    
    # Get nearest entry position
    nearest_entry = _bb_get(worker, "nearest_entry_position", None)
    if not nearest_entry:
        logger.warning("step=leave_nest worker=%s status=no_entry pos=%s", wid, pos)
        return {"status": "FAILURE"}
    
    # Move towards entry
    dx = nearest_entry[0] - pos[0]
    dy = nearest_entry[1] - pos[1]
    
    # Normalize movement (one step at a time)
    if dx != 0:
        dx = 1 if dx > 0 else -1
    if dy != 0:
        dy = 1 if dy > 0 else -1
    
    target_pos = [pos[0] + dx, pos[1] + dy]
    
    intent = _create_move_intent(target_pos, "leaving_nest")
    
    logger.info("step=leave_nest worker=%s status=moving pos=%s target=%s entry=%s", 
               wid, pos, target_pos, nearest_entry)
    
    return {
        "status": "SUCCESS",
        "intents": [intent],
    }


def spiral_search_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Execute spiral search pattern around nest to find food.
    """
    wid = getattr(worker, "id", "?")
    pos = _safe_pos(worker)
    
    # Get spiral search target
    spiral_pos = _bb_get(worker, "spiral_next_position", None)
    if not spiral_pos:
        # Fallback to random search
        logger.debug("step=spiral_search worker=%s status=no_spiral_data pos=%s", wid, pos)
        return random_search_fallback(worker, environment)
    
    intent = _create_move_intent(spiral_pos, "spiral_search")
    
    logger.info("step=spiral_search worker=%s status=moving pos=%s target=%s", 
               wid, pos, spiral_pos)
    
    return {
        "status": "SUCCESS", 
        "intents": [intent],
    }


def move_to_food_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Move towards detected food source.
    """
    wid = getattr(worker, "id", "?")
    pos = _safe_pos(worker)
    
    # Try best food source first
    best_source = _bb_get(worker, "best_food_source", None)
    if best_source and "position" in best_source:
        target_pos = best_source["position"]
    else:
        # Fallback to basic food detection
        food_pos = _bb_get(worker, "food_position", None)
        if not food_pos:
            logger.debug("step=move_to_food worker=%s status=no_food pos=%s", wid, pos)
            return {"status": "FAILURE"}
        target_pos = food_pos
    
    # Move towards food (one step at a time)
    dx = target_pos[0] - pos[0]
    dy = target_pos[1] - pos[1]
    
    if dx != 0:
        dx = 1 if dx > 0 else -1
    if dy != 0:
        dy = 1 if dy > 0 else -1
    
    next_pos = [pos[0] + dx, pos[1] + dy]
    
    intent = _create_move_intent(next_pos, "approaching_food")
    
    logger.info("step=move_to_food worker=%s status=moving pos=%s target=%s food=%s", 
               wid, pos, next_pos, target_pos)
    
    return {
        "status": "SUCCESS",
        "intents": [intent],
    }


def collect_and_eat_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Collect food and fill social stomach.
    """
    wid = getattr(worker, "id", "?")
    pos = _safe_pos(worker)
    
    # Check if adjacent to food
    food_pos = _bb_get(worker, "food_position", None)
    if not food_pos:
        logger.debug("step=collect_and_eat worker=%s status=no_food pos=%s", wid, pos)
        return {"status": "FAILURE"}
    
    # Check adjacency (Manhattan distance <= 1)
    distance = abs(pos[0] - food_pos[0]) + abs(pos[1] - food_pos[1])
    if distance > 1:
        logger.debug("step=collect_and_eat worker=%s status=not_adjacent pos=%s food=%s dist=%d", 
                    wid, pos, food_pos, distance)
        return {"status": "FAILURE"}
    
    # Create collection intent
    collection_intent = {
        "type": "COLLECT_FOOD", 
        "target_position": food_pos,
        "reason": "foraging",
    }
    
    logger.info("step=collect_and_eat worker=%s status=collecting pos=%s food=%s", 
               wid, pos, food_pos)
    
    return {
        "status": "SUCCESS",
        "intents": [collection_intent],
    }


def return_to_nest_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Enhanced return to nest with robust fallback strategies.
    Prevents workers from getting lost through multi-layered navigation.
    """
    wid = getattr(worker, "id", "?")
    pos = _safe_pos(worker)
    
    # Check if already in nest
    in_nest = _bb_get(worker, "in_nest", False)
    if in_nest:
        logger.debug("step=return_to_nest worker=%s status=already_in_nest pos=%s", wid, pos)
        return {"status": "SUCCESS"}
    
    # Get enhanced navigation information
    return_direction = _bb_get(worker, "return_path_direction", None)
    return_strategy = _bb_get(worker, "return_strategy", "direct")
    path_blocked = _bb_get(worker, "path_blocked", False)
    
    # Multi-level fallback chain
    if not return_direction or (return_direction[0] == 0 and return_direction[1] == 0):
        # Try breadcrumb pheromone gradient
        breadcrumb_direction = _follow_breadcrumb_gradient(worker, environment)
        if breadcrumb_direction:
            return_direction = breadcrumb_direction
            return_strategy = "breadcrumb_gradient"
        else:
            # Final fallback: emergency navigation to center
            return_direction = _emergency_center_navigation(worker, environment)
            return_strategy = "emergency_center"
    
    if not return_direction or (return_direction[0] == 0 and return_direction[1] == 0):
        logger.warning("step=return_to_nest worker=%s status=all_fallbacks_failed pos=%s", wid, pos)
        return {"status": "FAILURE"}
    
    target_pos = [pos[0] + return_direction[0], pos[1] + return_direction[1]]
    
    # Ensure target is within bounds
    if hasattr(environment, "width") and hasattr(environment, "height"):
        target_pos[0] = max(0, min(target_pos[0], environment.width - 1))
        target_pos[1] = max(0, min(target_pos[1], environment.height - 1))
    
    intent = _create_move_intent(target_pos, f"returning_to_nest_{return_strategy}")
    
    logger.info("step=return_to_nest worker=%s status=moving pos=%s target=%s strategy=%s blocked=%s", 
               wid, pos, target_pos, return_strategy, path_blocked)
    
    return {
        "status": "SUCCESS",
        "intents": [intent],
    }


def _follow_breadcrumb_gradient(worker: Any, environment: Any) -> Optional[List[int]]:
    """
    Follow breadcrumb pheromone gradient back towards nest.
    Returns direction towards weaker breadcrumb (older = closer to nest).
    """
    x, y = _safe_pos(worker)
    
    if not hasattr(environment, "pheromone_field"):
        return None
    
    # Check neighboring cells for breadcrumb pheromones
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]
    weakest_strength = float('inf')
    best_direction = None
    
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if (0 <= nx < getattr(environment, "width", 40) and 
            0 <= ny < getattr(environment, "height", 30)):
            
            # Get breadcrumb pheromone strength at this position
            try:
                breadcrumb_strength = environment.pheromone_field.get_strength(nx, ny, "breadcrumb")
                if 0 < breadcrumb_strength < weakest_strength:
                    weakest_strength = breadcrumb_strength
                    best_direction = [dx, dy]
            except (AttributeError, TypeError):
                continue
    
    return best_direction


def _emergency_center_navigation(worker: Any, environment: Any) -> List[int]:
    """
    Emergency fallback: navigate towards environment center.
    Last resort when all other navigation methods fail.
    """
    x, y = _safe_pos(worker)
    
    # Navigate towards environment center
    center_x = getattr(environment, "width", 40) // 2
    center_y = getattr(environment, "height", 30) // 2
    
    dx = center_x - x
    dy = center_y - y
    
    # Normalize direction
    if dx != 0:
        dx = 1 if dx > 0 else -1
    if dy != 0:
        dy = 1 if dy > 0 else -1
    
    return [dx, dy]


def deposit_trail_pheromone_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Deposit pheromone trail while returning to nest.
    Enhanced with trail success reinforcement and breadcrumb system.
    """
    wid = getattr(worker, "id", "?")
    pos = _safe_pos(worker)
    bb = getattr(worker, "blackboard", None)
    
    # Check for trail success multiplier (for reinforcement)
    success_multiplier = _bb_get(worker, "trail_success_multiplier", 1.0)
    
    # Adjust strength based on success
    base_strength = 10.0
    strength = base_strength * success_multiplier
    strength = max(1.0, min(strength, 20.0))  # Clamp between 1-20
    
    # Get or initialize breadcrumb counter for this worker
    breadcrumb_counter = bb.get("breadcrumb_counter", 0) if bb else 0
    breadcrumb_counter += 1
    
    # Calculate breadcrumb strength (higher counter = later laid = stronger)
    # This creates a gradient that weakens towards the nest
    breadcrumb_strength = max(1.0, min(float(breadcrumb_counter) * 0.5, 10.0))
    
    # Create multiple pheromone deposition intents
    intents = []
    
    # Main food trail pheromone
    food_trail_intent = {
        "type": "PHEROMONE",
        "pheromone_type": "food_trail",
        "strength": strength,
        "position": pos,
        "reason": "food_trail_marking",
    }
    intents.append(food_trail_intent)
    
    # Breadcrumb pheromone for navigation fallback
    breadcrumb_intent = {
        "type": "PHEROMONE", 
        "pheromone_type": "breadcrumb",
        "strength": breadcrumb_strength,
        "position": pos,
        "reason": "navigation_breadcrumb",
    }
    intents.append(breadcrumb_intent)
    
    logger.info("step=deposit_trail_pheromone worker=%s status=depositing pos=%s trail_strength=%.1f breadcrumb_strength=%.1f counter=%d", 
               wid, pos, strength, breadcrumb_strength, breadcrumb_counter)
    
    return {
        "status": "SUCCESS",
        "intents": intents,
        "breadcrumb_counter": breadcrumb_counter,  # Store updated counter
    }


def random_search_fallback(worker: Any, environment: Any) -> Dict[str, Any]:
    """
    Fallback random search when spiral data is unavailable.
    """
    wid = getattr(worker, "id", "?")
    pos = _safe_pos(worker)
    
    # Random movement
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]
    dx, dy = random.choice(directions)
    target_pos = [pos[0] + dx, pos[1] + dy]
    
    # Ensure within bounds
    if hasattr(environment, "width") and hasattr(environment, "height"):
        target_pos[0] = max(0, min(target_pos[0], environment.width - 1))
        target_pos[1] = max(0, min(target_pos[1], environment.height - 1))
    
    intent = _create_move_intent(target_pos, "random_search")
    
    logger.debug("step=random_search_fallback worker=%s pos=%s target=%s", wid, pos, target_pos)
    
    return {
        "status": "SUCCESS",
        "intents": [intent],
    }
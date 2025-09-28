# FILE: antsim/plugins/foraging_sensors.py
"""Foraging sensor plugins for comprehensive ant foraging behavior."""
import logging
import math
from typing import Any, Dict, Optional, Tuple, List
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
logger = logging.getLogger(__name__)


@hookimpl
def register_sensors() -> Dict[str, callable]:
    """Expose foraging sensors."""
    return {
        "spiral_search_sensor": spiral_search_sensor,
        "food_source_sensor": food_source_sensor,
        "nest_distance_sensor": nest_distance_sensor,
        "foraging_state_sensor": foraging_state_sensor,
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


def _get_nest_entries(environment: Any) -> List[Tuple[int, int]]:
    """Get nest entry positions."""
    entries = []
    if hasattr(environment, "entry_positions") and isinstance(environment.entry_positions, (list, tuple)):
        entries = [tuple(p) for p in environment.entry_positions]
    elif hasattr(environment, "entry_position") and environment.entry_position:
        entries = [tuple(environment.entry_position)]
    return entries


def _manhattan_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Calculate Manhattan distance between two points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def spiral_search_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    """
    Provides spiral search coordinates around nest center.
    Returns next position in expanding spiral pattern.
    """
    bb = getattr(worker, "blackboard", None)
    if not bb:
        logger.debug("sensor=spiral_search_sensor reason=no-blackboard skipped")
        return {"spiral_next_position": None, "spiral_radius": 0}
    
    x, y = _safe_pos(worker)
    
    # Get or initialize spiral state
    spiral_center = bb.get("spiral_center", None)
    spiral_angle = bb.get("spiral_angle", 0.0)
    spiral_radius = bb.get("spiral_radius", 1)
    
    # Initialize spiral center to nest center if not set
    if spiral_center is None:
        entries = _get_nest_entries(environment)
        if entries:
            # Use first entry as reference point
            spiral_center = list(entries[0])
        else:
            # Fallback to current position
            spiral_center = [x, y]
    
    # Calculate next position in spiral
    angle_increment = 0.5  # Radians per step
    radius_increment = 0.1  # Radius growth per step
    
    # Update spiral parameters
    new_angle = spiral_angle + angle_increment
    new_radius = spiral_radius + radius_increment
    
    # Calculate spiral position
    spiral_x = spiral_center[0] + int(new_radius * math.cos(new_angle))
    spiral_y = spiral_center[1] + int(new_radius * math.sin(new_angle))
    
    # Ensure within bounds
    if hasattr(environment, "width") and hasattr(environment, "height"):
        spiral_x = max(0, min(spiral_x, environment.width - 1))
        spiral_y = max(0, min(spiral_y, environment.height - 1))
    
    logger.debug("sensor=spiral_search_sensor pos=(%s,%s) center=%s next=(%s,%s) radius=%.1f", 
                x, y, spiral_center, spiral_x, spiral_y, new_radius)
    
    return {
        "spiral_next_position": [spiral_x, spiral_y],
        "spiral_radius": new_radius,
        "spiral_angle": new_angle,
        "spiral_center": spiral_center,
    }


def food_source_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    """
    Enhanced food detection with range and quality assessment.
    Extends existing food detection with additional metadata.
    """
    if not hasattr(environment, "grid"):
        logger.debug("sensor=food_source_sensor reason=no-grid skipped")
        return {
            "food_sources_nearby": [],
            "best_food_source": None,
            "food_search_exhausted": False,
        }
    
    x, y = _safe_pos(worker)
    max_search_dist = 7  # Extended search range
    
    food_sources = []
    
    for dy in range(-max_search_dist, max_search_dist + 1):
        for dx in range(-max_search_dist, max_search_dist + 1):
            dist = abs(dx) + abs(dy)
            if dist > max_search_dist:
                continue
                
            nx, ny = x + dx, y + dy
            if (0 <= nx < environment.width and 
                0 <= ny < environment.height):
                
                cell = environment.grid[ny][nx]
                food = getattr(cell, "food", None)
                if food and getattr(food, "amount", 0) > 0:
                    food_sources.append({
                        "position": [nx, ny],
                        "distance": dist,
                        "amount": getattr(food, "amount", 0),
                        "quality": min(100, getattr(food, "amount", 0)),  # Simple quality metric
                    })
    
    # Sort by distance, then by amount
    food_sources.sort(key=lambda f: (f["distance"], -f["amount"]))
    
    best_source = food_sources[0] if food_sources else None
    
    # Check if search area is exhausted (heuristic)
    bb = getattr(worker, "blackboard", None)
    search_cycles = bb.get("food_search_cycles", 0) if bb else 0
    search_exhausted = search_cycles > 20 and len(food_sources) == 0
    
    logger.debug("sensor=food_source_sensor found=%d best=%s exhausted=%s", 
                len(food_sources), best_source["position"] if best_source else None, search_exhausted)
    
    return {
        "food_sources_nearby": food_sources,
        "best_food_source": best_source,
        "food_search_exhausted": search_exhausted,
    }


def nest_distance_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    """
    Enhanced nest distance sensor with obstacle detection and fallback strategies.
    Provides robust return navigation preventing workers from getting lost.
    """
    x, y = _safe_pos(worker)
    entries = _get_nest_entries(environment)
    bb = getattr(worker, "blackboard", None)
    
    if not entries:
        logger.debug("sensor=nest_distance_sensor reason=no-entries pos=(%s,%s)", x, y)
        return {
            "nearest_entry_distance": 999,
            "nearest_entry_position": None,
            "return_path_direction": None,
            "return_strategy": "no_entries",
            "path_blocked": False,
            "last_valid_direction": None,
        }
    
    # Find nearest entry
    nearest_entry = min(entries, key=lambda e: _manhattan_distance((x, y), e))
    nearest_distance = _manhattan_distance((x, y), nearest_entry)
    
    # Calculate primary return direction
    dx = nearest_entry[0] - x
    dy = nearest_entry[1] - y
    
    # Normalize direction
    if dx != 0:
        dx = 1 if dx > 0 else -1
    if dy != 0:
        dy = 1 if dy > 0 else -1
    
    primary_direction = [dx, dy] if (dx != 0 or dy != 0) else [0, 0]
    
    # Check if path is blocked (basic obstacle detection)
    next_x, next_y = x + dx, y + dy
    path_blocked = False
    
    if hasattr(environment, "grid") and hasattr(environment, "width") and hasattr(environment, "height"):
        if (0 <= next_x < environment.width and 0 <= next_y < environment.height):
            # Check if next cell is passable
            if hasattr(environment.grid[next_y][next_x], "terrain"):
                terrain = getattr(environment.grid[next_y][next_x], "terrain", None)
                if terrain == "wall":
                    path_blocked = True
            # Check if another ant is there
            if hasattr(environment, "get_ant_at_position"):
                occupant = environment.get_ant_at_position(next_x, next_y)
                if occupant is not None:
                    path_blocked = True
    
    # Determine navigation strategy
    last_valid_direction = bb.get("last_valid_direction", None) if bb else None
    strategy = "direct"
    
    if path_blocked:
        # Try alternative directions (detour around obstacles)
        alternative_directions = []
        if dx != 0 and dy != 0:  # Diagonal movement blocked
            alternative_directions = [[dx, 0], [0, dy]]  # Try horizontal or vertical
        elif dx != 0:  # Horizontal movement blocked
            alternative_directions = [[0, 1], [0, -1]]  # Try vertical
        elif dy != 0:  # Vertical movement blocked
            alternative_directions = [[1, 0], [-1, 0]]  # Try horizontal
        
        # Test alternative directions
        valid_alternative = None
        for alt_dx, alt_dy in alternative_directions:
            alt_x, alt_y = x + alt_dx, y + alt_dy
            if (0 <= alt_x < environment.width and 0 <= alt_y < environment.height):
                alt_blocked = False
                if hasattr(environment.grid[alt_y][alt_x], "terrain"):
                    terrain = getattr(environment.grid[alt_y][alt_x], "terrain", None)
                    if terrain == "wall":
                        alt_blocked = True
                if not alt_blocked and hasattr(environment, "get_ant_at_position"):
                    occupant = environment.get_ant_at_position(alt_x, alt_y)
                    if occupant is not None:
                        alt_blocked = True
                
                if not alt_blocked:
                    valid_alternative = [alt_dx, alt_dy]
                    break
        
        if valid_alternative:
            primary_direction = valid_alternative
            strategy = "detour"
        elif last_valid_direction:
            primary_direction = last_valid_direction
            strategy = "breadcrumb"
        else:
            # Emergency fallback: move towards environment center
            center_x = getattr(environment, "width", 40) // 2
            center_y = getattr(environment, "height", 30) // 2
            center_dx = center_x - x
            center_dy = center_y - y
            if center_dx != 0:
                center_dx = 1 if center_dx > 0 else -1
            if center_dy != 0:
                center_dy = 1 if center_dy > 0 else -1
            primary_direction = [center_dx, center_dy]
            strategy = "emergency"
    
    # Store last valid direction for future use
    if not path_blocked and primary_direction != [0, 0]:
        last_valid_direction = primary_direction.copy()
    
    logger.debug("sensor=nest_distance_sensor pos=(%s,%s) nearest=%s dist=%d dir=%s strategy=%s blocked=%s", 
                x, y, nearest_entry, nearest_distance, primary_direction, strategy, path_blocked)
    
    return {
        "nearest_entry_distance": nearest_distance,
        "nearest_entry_position": list(nearest_entry),
        "return_path_direction": primary_direction,
        "return_strategy": strategy,
        "path_blocked": path_blocked,
        "last_valid_direction": last_valid_direction,
    }


def foraging_state_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    """
    Track foraging-specific state and transitions.
    """
    bb = getattr(worker, "blackboard", None)
    if not bb:
        return {"foraging_phase": "idle"}
    
    # Determine current foraging phase
    social_hungry = bb.get("social_hungry", False)
    in_nest = bb.get("in_nest", False)
    food_detected = bb.get("food_detected", False)
    social_stomach = bb.get("social_stomach", 0)
    social_capacity = bb.get("social_stomach_capacity", 100)
    
    phase = "idle"
    if social_hungry and in_nest:
        phase = "leaving_nest"
    elif social_hungry and not in_nest:
        if food_detected:
            phase = "approaching_food"
        else:
            phase = "searching_food"
    elif social_stomach > 0 and not in_nest:
        phase = "returning_to_nest"
    elif social_stomach >= social_capacity * 0.8:  # Nearly full
        phase = "social_stomach_full"
    
    # Track search cycles for exhaustion detection
    search_cycles = bb.get("food_search_cycles", 0)
    if phase == "searching_food":
        search_cycles += 1
    elif phase in ["approaching_food", "returning_to_nest"]:
        search_cycles = 0  # Reset on success
    
    logger.debug("sensor=foraging_state_sensor phase=%s search_cycles=%d social=%d/%d", 
                phase, search_cycles, social_stomach, social_capacity)
    
    return {
        "foraging_phase": phase,
        "food_search_cycles": search_cycles,
        "foraging_active": phase != "idle",
    }
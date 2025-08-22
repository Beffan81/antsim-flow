# plugins/core_sensors.py
"""Core sensor plugins for antsim (pure, side-effect-free)."""
import logging
from typing import Any, Dict, Optional, Tuple, List
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
logger = logging.getLogger(__name__)


@hookimpl
def register_sensors() -> Dict[str, callable]:
    """Expose core sensors."""
    return {
        "bb_basic_state": bb_basic_state_sensor,
        "bb_env_flags": bb_env_flags_sensor,
        "bb_neighbors": bb_neighbors_sensor,
        "bb_food_detection": bb_food_detection_sensor,
        "bb_pheromone_detection": bb_pheromone_detection_sensor,
        "bb_internal_state": bb_internal_state_sensor,
        # NEW: Track sensor execution for idempotency
        "bb_sensor_metadata": bb_sensor_metadata,
    }


def _safe_pos(worker: Any) -> Tuple[int, int]:
    if hasattr(worker, "position"):
        pos = getattr(worker, "position")
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            return int(pos[0]), int(pos[1])
    bb = getattr(worker, "blackboard", None)
    if bb:
        pos = bb.get("position", [0, 0])
        return int(pos[0]), int(pos[1])
    return 0, 0


def _env_has_grid(env: Any) -> bool:
    return hasattr(env, "grid") and hasattr(env, "width") and hasattr(env, "height")


def _cell(env: Any, x: int, y: int):
    if not _env_has_grid(env):
        return None
    if 0 <= x < env.width and 0 <= y < env.height:
        return env.grid[y][x]
    return None


def bb_sensor_metadata(worker: Any, environment: Any) -> Dict[str, Any]:
    """Track sensor execution metadata for idempotency."""
    cycle = getattr(environment, "cycle_count", 0)
    return {
        "sensors_run_cycle": cycle,
        "sensors_run_tick": getattr(environment, "tick_id", 0),
    }


def bb_basic_state_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    x, y = _safe_pos(worker)
    cycle = getattr(environment, "cycle_count", 0)
    out = {"position": [x, y], "cycle": int(cycle)}
    logger.debug("sensor=bb_basic_state pos=(%s,%s) cycle=%s", x, y, cycle)
    return out


def bb_env_flags_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    x, y = _safe_pos(worker)
    in_nest = False
    at_entry = False
    if hasattr(environment, "entry_positions") and isinstance(environment.entry_positions, (list, tuple)):
        at_entry = (x, y) in [tuple(p) for p in environment.entry_positions]  # type: ignore
    elif hasattr(environment, "entry_position") and environment.entry_position:
        at_entry = (x, y) == tuple(environment.entry_position)
    cell = _cell(environment, x, y)
    if cell is not None and hasattr(cell, "cell_type"):
        in_nest = cell.cell_type in ("nest", "e")
    logger.debug("sensor=bb_env_flags at_entry=%s in_nest=%s pos=(%s,%s)", at_entry, in_nest, x, y)
    return {"at_entry": at_entry, "in_nest": in_nest}


def bb_neighbors_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    if not (_env_has_grid(environment) and hasattr(environment, "get_ant_at_position")):
        logger.debug("sensor=bb_neighbors reason=env-missing neighbors=skipped")
        return {
            "individual_hungry_neighbor_found": False,
            "hungry_neighbor_id": None,
            "hungry_neighbor_position": None,
            "neighbor_with_food_found": False,
            "signaling_neighbor_found": False,
            "signaling_neighbor_id": None,
            "signaling_neighbor_position": None,
        }
    x, y = _safe_pos(worker)
    hungry_neighbor_id = None
    hungry_neighbor_pos = None
    hungry_found = False
    signaling_neighbor_id = None
    signaling_neighbor_pos = None
    signaling_found = False
    neighbor_with_food = False
    dirs8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    dirs4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    best_hunger_ratio = 1.1
    best_signaling_ratio = 1.1
    for dx, dy in dirs8:
        nx, ny = x + dx, y + dy
        ant = environment.get_ant_at_position(nx, ny)
        if ant is None:
            continue
        indiv_stomach = None
        hunger_thr = None
        in_nest = False
        bb = getattr(ant, "blackboard", None)
        if bb:
            indiv_stomach = bb.get("individual_stomach")
            hunger_thr = bb.get("hunger_threshold")
            in_nest = bb.get("in_nest", False)
        if indiv_stomach is None:
            indiv_stomach = getattr(ant, "current_stomach", None)
        if hunger_thr is None:
            hunger_thr = getattr(ant, "hunger_threshold", None)
        if indiv_stomach is None or hunger_thr in (None, 0):
            continue
        ratio = float(indiv_stomach) / float(hunger_thr)
        
        # Check for individual hungry neighbor (existing logic)
        if indiv_stomach < hunger_thr and ratio < best_hunger_ratio:
            best_hunger_ratio = ratio
            hungry_neighbor_id = getattr(ant, "id", None)
            hungry_neighbor_pos = [nx, ny]
            hungry_found = True
            
        # Check for signaling neighbor (hungry AND in nest)
        if indiv_stomach < hunger_thr and in_nest and ratio < best_signaling_ratio:
            best_signaling_ratio = ratio
            signaling_neighbor_id = getattr(ant, "id", None)
            signaling_neighbor_pos = [nx, ny]
            signaling_found = True
    for dx, dy in dirs4:
        nx, ny = x + dx, y + dy
        ant = environment.get_ant_at_position(nx, ny)
        if ant is None:
            continue
        social = None
        bb = getattr(ant, "blackboard", None)
        if bb:
            social = bb.get("social_stomach")
        if social is None:
            social = getattr(ant, "current_social_stomach", None)
        if isinstance(social, (int, float)) and social > 0:
            neighbor_with_food = True
            break
    logger.debug(
        "sensor=bb_neighbors hungry_found=%s hungry_id=%s hungry_pos=%s neighbor_with_food=%s signaling_found=%s signaling_id=%s",
        hungry_found, hungry_neighbor_id, hungry_neighbor_pos, neighbor_with_food, signaling_found, signaling_neighbor_id,
    )
    return {
        "individual_hungry_neighbor_found": hungry_found,
        "hungry_neighbor_id": hungry_neighbor_id,
        "hungry_neighbor_position": hungry_neighbor_pos,
        "neighbor_with_food_found": neighbor_with_food,
        "signaling_neighbor_found": signaling_found,
        "signaling_neighbor_id": signaling_neighbor_id,
        "signaling_neighbor_position": signaling_neighbor_pos,
    }


def _find_collection_position(worker_pos: Tuple[int, int], food_pos: Tuple[int, int], 
                            environment: Any) -> Optional[List[int]]:
    """Find best adjacent position to collect food from (pure)."""
    wx, wy = worker_pos
    fx, fy = food_pos
    
    # If already adjacent, use current position
    if max(abs(wx - fx), abs(wy - fy)) <= 1:
        return [wx, wy]
    
    # Find all valid adjacent positions to food
    candidates = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            adj_x, adj_y = fx + dx, fy + dy
            if (0 <= adj_x < environment.width and 
                0 <= adj_y < environment.height and
                _cell_free_for_collection(environment, adj_x, adj_y)):
                dist = abs(wx - adj_x) + abs(wy - adj_y)
                candidates.append({"pos": [adj_x, adj_y], "dist": dist})
    
    if candidates:
        # Sort by distance to worker
        candidates.sort(key=lambda c: c["dist"])
        return candidates[0]["pos"]
    
    # If no free adjacent positions, return food position itself
    return [fx, fy]


def _cell_free_for_collection(env: Any, x: int, y: int) -> bool:
    """Check if cell is free for collection (no wall, allows current ant)."""
    cell = _cell(env, x, y)
    if cell is None:
        return False
    if hasattr(cell, "cell_type") and cell.cell_type in ("w", "wall"):
        return False
    # For collection position, we allow the cell even if occupied by current ant
    return True


def bb_food_detection_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    if not _env_has_grid(environment):
        logger.debug("sensor=bb_food_detection reason=no-grid skipped")
        return {
            "food_detected": False, 
            "food_position": None,
            "food_collection_position": None  # NEW
        }
    x, y = _safe_pos(worker)
    try:
        max_dist = int(getattr(environment, "config", {}).get("environment", {}).get("search", {}).get("max_distance", 5))  # type: ignore
    except Exception:
        max_dist = 5
    best_pos: Optional[Tuple[int, int]] = None
    best_d = 10**9
    for dy in range(-max_dist, max_dist + 1):
        for dx in range(-max_dist, max_dist + 1):
            if abs(dx) + abs(dy) > max_dist:
                continue
            nx, ny = x + dx, y + dy
            cell = _cell(environment, nx, ny)
            if cell is None:
                continue
            food = getattr(cell, "food", None)
            if food is not None and getattr(food, "amount", 0) > 0:
                d = abs(dx) + abs(dy)
                if d < best_d:
                    best_d = d
                    best_pos = (nx, ny)
    detected = best_pos is not None
    
    # NEW: Calculate collection position
    collection_pos = None
    if detected and best_pos:
        collection_pos = _find_collection_position((x, y), best_pos, environment)
    
    logger.debug("sensor=bb_food_detection detected=%s best=%s dist=%s collection=%s", 
                detected, best_pos, best_d if detected else None, collection_pos)
    return {
        "food_detected": detected, 
        "food_position": list(best_pos) if detected else None,
        "food_collection_position": collection_pos  # NEW
    }


def bb_pheromone_detection_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    if not _env_has_grid(environment):
        logger.debug("sensor=bb_pheromone_detection reason=no-grid skipped")
        return {"pheromone_detected": False, "pheromone_position": None, "pheromone_type": None}
    x, y = _safe_pos(worker)
    max_dist = 5
    best_pos: Optional[Tuple[int, int]] = None
    best_type: Optional[str] = None
    best_d = 10**9
    best_level = 0
    for radius in range(1, max_dist + 1):
        found_this_radius = False
        for dx in range(-radius, radius + 1):
            dy = radius - abs(dx)
            for sdy in (-dy, dy) if dy != 0 else (0,):
                nx, ny = x + dx, y + sdy
                cell = _cell(environment, nx, ny)
                if cell is None:
                    continue
                # Check for typed pheromones first
                if hasattr(cell, "pheromones") and isinstance(cell.pheromones, dict):
                    for ptype, level in cell.pheromones.items():
                        if level > 0 and level > best_level:
                            d = abs(nx - x) + abs(ny - y)
                            if d < best_d:
                                best_d = d
                                best_pos = (nx, ny)
                                best_type = ptype
                                best_level = level
                                found_this_radius = True
                # Fallback to legacy single pheromone
                level = getattr(cell, "pheromone_level", 0)
                ptype = getattr(cell, "pheromone_type", None)
                if level and level > 0 and level > best_level:
                    d = abs(nx - x) + abs(ny - y)
                    if d < best_d:
                        best_d = d
                        best_pos = (nx, ny)
                        best_type = ptype
                        best_level = level
                        found_this_radius = True
        if found_this_radius:
            break
    detected = best_pos is not None
    logger.debug("sensor=bb_pheromone_detection detected=%s best=%s dist=%s type=%s level=%s", 
                detected, best_pos, best_d if detected else None, best_type, best_level)
    return {
        "pheromone_detected": detected, 
        "pheromone_position": list(best_pos) if detected else None,
        "pheromone_type": best_type  # NEW: include type
    }


def bb_internal_state_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    """
    Derives internal state purely from worker/blackboard without side effects:
    - energy, max_energy
    - individual/social stomach and capacities
    - hunger_threshold
    - derived booleans: individual_hungry, social_hungry
    - NEW: search_unsuccessful flag based on recent movement
    """
    bb = getattr(worker, "blackboard", None)
    def g(k, default=None):
        return bb.get(k, default) if bb else getattr(worker, k, default)

    energy = g("energy", getattr(worker, "energy", 0))
    max_energy = g("max_energy", getattr(worker, "max_energy", 100))
    indiv = g("individual_stomach", getattr(worker, "current_stomach", 0))
    indiv_cap = g("individual_stomach_capacity", getattr(worker, "stomach_capacity", 0))
    social = g("social_stomach", getattr(worker, "current_social_stomach", 0))
    social_cap = g("social_stomach_capacity", getattr(worker, "social_stomach_capacity", 0))
    thr = g("hunger_threshold", getattr(worker, "hunger_threshold", indiv_cap // 2))

    individual_hungry = bool(indiv < thr)
    social_hungry = bool(social == 0)
    
    # NEW: Derive search_unsuccessful from movement pattern
    # This is a simplified heuristic - can be enhanced with actual movement tracking
    has_moved = g("has_moved", False)
    food_detected = g("food_detected", False)
    search_unsuccessful = not has_moved and not food_detected
    
    # NEW: Derive signaling_hunger from individual_hungry AND in_nest
    in_nest = g("in_nest", False)
    signaling_hunger = individual_hungry and in_nest

    out = {
        "energy": int(energy),
        "max_energy": int(max_energy),
        "individual_stomach": int(indiv),
        "individual_stomach_capacity": int(indiv_cap),
        "social_stomach": int(social),
        "social_stomach_capacity": int(social_cap),
        "hunger_threshold": int(thr),
        "individual_hungry": individual_hungry,
        "social_hungry": social_hungry,
        "search_unsuccessful": search_unsuccessful,  # NEW
        "signaling_hunger": signaling_hunger,  # NEW
    }
    logger.debug(
        "sensor=bb_internal_state indiv=%s/%s social=%s/%s threshold=%s hungry_i=%s hungry_s=%s search_fail=%s signaling=%s",
        indiv, indiv_cap, social, social_cap, thr, individual_hungry, social_hungry, search_unsuccessful, signaling_hunger
    )
    return out

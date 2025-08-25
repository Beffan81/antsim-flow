# plugins/emergent_steps.py
"""Emergent behavior steps for direct communication and hunger response."""
import logging
from typing import Any, Dict, List, Optional, Tuple
from pluggy import HookimplMarker

# Tolerant imports for intents
try:
    from ..core.executor import MoveIntent, FeedIntent
except Exception:
    MoveIntent = None  # type: ignore
    FeedIntent = None  # type: ignore

hookimpl = HookimplMarker("antsim")
logger = logging.getLogger(__name__)


@hookimpl
def register_steps() -> Dict[str, callable]:
    """Expose emergent behavior steps."""
    return {
        "auto_direct_feed": auto_direct_feed_step,
        "move_to_hunger_source": move_to_hunger_source_step,
    }


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


def _env_bounds(env: Any) -> Optional[Tuple[int, int]]:
    """Get environment bounds if available."""
    w = getattr(env, "width", None)
    h = getattr(env, "height", None)
    if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
        return w, h
    return None


def _in_bounds(pos: Tuple[int, int], bounds: Optional[Tuple[int, int]]) -> bool:
    """Check if position is within bounds."""
    if not bounds:
        return True
    x, y = pos
    w, h = bounds
    return 0 <= x < w and 0 <= y < h


def _is_cell_free(env: Any, pos: Tuple[int, int]) -> bool:
    """Check if cell is free (no wall, no ant)."""
    try:
        if hasattr(env, "grid"):
            x, y = pos
            cell = env.grid[y][x]
            if hasattr(cell, "cell_type") and getattr(cell, "cell_type") in ("w", "wall"):
                return False
            if hasattr(cell, "ant") and getattr(cell, "ant") is not None:
                return False
            return True
    except Exception:
        pass
    return True


def auto_direct_feed_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Automatically feeds hungry neighbors through direct tactile contact.
    This implements immediate local feeding without complex coordination.
    """
    wid = getattr(worker, "id", "?")
    
    # Check if we have a direct feeding opportunity
    has_opportunity = _bb_get(worker, "direct_feeding_opportunity", False)
    target_id = _bb_get(worker, "direct_feed_target_id", None)
    social_food = _bb_get(worker, "social_stomach", 0)
    
    if not has_opportunity or target_id is None:
        logger.debug("step=auto_direct_feed worker=%s status=no_opportunity", wid)
        return {"status": "FAILURE"}
        
    if social_food <= 0:
        logger.debug("step=auto_direct_feed worker=%s status=no_social_food", wid)
        return {"status": "FAILURE"}
    
    # Create feed intent - automatic feeding, no explicit amount
    if FeedIntent is None:
        intent = {"type": "FEED", "payload": {"target_id": int(target_id)}}
    else:
        intent = FeedIntent(target_id=int(target_id), amount=None)  # type: ignore
    
    logger.info("step=auto_direct_feed worker=%s target=%s auto_feeding=TRUE", wid, target_id)
    return {"status": "SUCCESS", "intents": [intent]}


def move_to_hunger_source_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Moves worker towards detected hunger pheromone sources (Queen/Brood).
    Simple gradient following - one step towards strongest hunger signal.
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    
    # Check for hunger pheromone detection
    hunger_detected = _bb_get(worker, "hunger_pheromone_detected", False)
    hunger_position = _bb_get(worker, "hunger_pheromone_position", None)
    
    if not hunger_detected or not hunger_position:
        logger.debug("step=move_to_hunger_source worker=%s status=no_hunger_pheromone pos=%s", wid, pos)
        return {"status": "FAILURE"}
    
    try:
        hx, hy = int(hunger_position[0]), int(hunger_position[1])
    except Exception:
        logger.debug("step=move_to_hunger_source worker=%s status=invalid_hunger_position pos=%s", wid, pos)
        return {"status": "FAILURE"}
    
    # Calculate direction towards hunger source
    x, y = pos
    dx = 1 if hx > x else (-1 if hx < x else 0)
    dy = 1 if hy > y else (-1 if hy < y else 0)
    
    # Try to move one step towards hunger source
    target_positions = [
        (x + dx, y + dy),  # Diagonal
        (x + dx, y),       # Horizontal
        (x, y + dy),       # Vertical
    ]
    
    bounds = _env_bounds(environment)
    target = None
    
    for candidate in target_positions:
        if _in_bounds(candidate, bounds) and _is_cell_free(environment, candidate):
            target = candidate
            break
    
    if not target:
        logger.debug("step=move_to_hunger_source worker=%s status=no_valid_move pos=%s hunger_pos=%s", 
                    wid, pos, (hx, hy))
        return {"status": "FAILURE"}
    
    # Create move intent
    if MoveIntent is None:
        intent = {"type": "MOVE", "payload": {"target": list(target)}}
    else:
        intent = MoveIntent(target=target)  # type: ignore
    
    logger.info("step=move_to_hunger_source worker=%s pos=%s target=%s hunger_source=%s", 
               wid, pos, target, (hx, hy))
    return {"status": "SUCCESS", "intents": [intent]}
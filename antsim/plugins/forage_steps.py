# FILE: antsim/plugins/forage_steps.py
"""Forage steps: domain-aligned, pure intent producers.

Provides:
- find_food_source: gate-like step that succeeds if sensors detected food in range.

Design:
- Pure: read-only on worker/BB/environment; no world mutation and no direct path planning here.
- Intents: none for this gate; subsequent steps (move_to_food, collect_food) handle actions.
- Logging: concise reasoning (detected flag, positions, distances).
"""
import logging
from typing import Any, Dict, Optional, Tuple
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
log = logging.getLogger(__name__)


@hookimpl
def register_steps() -> Dict[str, callable]:
    """Expose forage-related steps."""
    return {
        "find_food_source": find_food_source_step,
        "move_to_food": move_to_food_step,
        "collect_food": collect_food_step,
    }


# ---------- Helpers (pure) ----------

def _bb_get(obj: Any, key: str, default=None):
    """Safe getter from blackboard or attributes (pure)."""
    bb = getattr(obj, "blackboard", None)
    if bb and hasattr(bb, "get"):
        try:
            return bb.get(key, default)
        except Exception:
            pass
    return getattr(obj, key, default)


def _bb_pos(worker: Any) -> Tuple[int, int]:
    """Get worker position from blackboard (preferred) or attributes (pure)."""
    pos = _bb_get(worker, "position", [0, 0])
    try:
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            return int(pos[0]), int(pos[1])
    except Exception:
        pass
    return 0, 0


def _manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ---------- Step (pure) ----------

def find_food_source_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Gate-like step: succeeds if sensors have detected food in range.

    Reads BB keys populated by sensors:
      - 'food_detected' (bool)
      - 'food_position' ([x, y] or None)

    Returns:
      - {'status': 'SUCCESS'} if food_detected is True (allows subsequent move_to_food/collect_food)
      - {'status': 'FAILURE'} otherwise (lets BT fall back, e.g., to search_food_randomly)
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    detected = bool(_bb_get(worker, "food_detected", False))
    food_pos = _bb_get(worker, "food_position", None)

    if detected and isinstance(food_pos, (list, tuple)) and len(food_pos) == 2:
        try:
            fpos = (int(food_pos[0]), int(food_pos[1]))
        except Exception:
            fpos = None
        dist = _manhattan(pos, fpos) if fpos else None
        log.info(
            "step=find_food_source worker=%s status=detected pos=%s food_pos=%s dist=%s",
            wid, pos, fpos, dist
        )
        # No intents here; next steps do the action
        return {"status": "SUCCESS"}

    log.debug(
        "step=find_food_source worker=%s status=not_detected pos=%s food_pos=%s",
        wid, pos, food_pos
    )
    return {"status": "FAILURE"}


def move_to_food_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Move towards detected food source (one step closer).
    
    Reads BB keys:
      - 'food_position' ([x, y])
      - 'position' ([x, y])
    
    Returns:
      - {'status': 'SUCCESS', 'intents': [MOVE_intent]} if movement possible
      - {'status': 'FAILURE'} if no food position or already adjacent
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    food_pos = _bb_get(worker, "food_position", None)
    
    if not food_pos or not isinstance(food_pos, (list, tuple)) or len(food_pos) != 2:
        log.debug("step=move_to_food worker=%s status=no_food_pos pos=%s", wid, pos)
        return {"status": "FAILURE"}
    
    try:
        fpos = (int(food_pos[0]), int(food_pos[1]))
    except Exception:
        log.debug("step=move_to_food worker=%s status=invalid_food_pos pos=%s food=%s", wid, pos, food_pos)
        return {"status": "FAILURE"}
    
    # Check if already adjacent (Manhattan distance <= 1)
    if _manhattan(pos, fpos) <= 1:
        log.debug("step=move_to_food worker=%s status=already_adjacent pos=%s food=%s", wid, pos, fpos)
        return {"status": "SUCCESS"}  # Already there
    
    # Calculate next step towards food
    dx = fpos[0] - pos[0]
    dy = fpos[1] - pos[1]
    
    # Normalize to single step
    if dx != 0:
        dx = 1 if dx > 0 else -1
    if dy != 0:
        dy = 1 if dy > 0 else -1
    
    target_pos = [pos[0] + dx, pos[1] + dy]
    
    intent = {
        "type": "MOVE",
        "target_position": target_pos,
        "reason": "approaching_food",
    }
    
    log.info("step=move_to_food worker=%s status=moving pos=%s target=%s food=%s", 
             wid, pos, target_pos, fpos)
    
    return {
        "status": "SUCCESS",
        "intents": [intent],
    }


def collect_food_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Collect food from adjacent cell.
    
    Reads BB keys:
      - 'food_position' ([x, y])
      - 'position' ([x, y])
    
    Returns:
      - {'status': 'SUCCESS', 'intents': [COLLECT_FOOD_intent]} if collection possible
      - {'status': 'FAILURE'} if not adjacent to food
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    food_pos = _bb_get(worker, "food_position", None)
    
    if not food_pos or not isinstance(food_pos, (list, tuple)) or len(food_pos) != 2:
        log.debug("step=collect_food worker=%s status=no_food_pos pos=%s", wid, pos)
        return {"status": "FAILURE"}
    
    try:
        fpos = (int(food_pos[0]), int(food_pos[1]))
    except Exception:
        log.debug("step=collect_food worker=%s status=invalid_food_pos pos=%s food=%s", wid, pos, food_pos)
        return {"status": "FAILURE"}
    
    # Check adjacency (Manhattan distance <= 1)
    distance = _manhattan(pos, fpos)
    if distance > 1:
        log.debug("step=collect_food worker=%s status=not_adjacent pos=%s food=%s dist=%d", 
                  wid, pos, fpos, distance)
        return {"status": "FAILURE"}
    
    intent = {
        "type": "COLLECT_FOOD",
        "target_position": list(fpos),
        "reason": "food_collection",
    }
    
    log.info("step=collect_food worker=%s status=collecting pos=%s food=%s", wid, pos, fpos)
    
    return {
        "status": "SUCCESS",
        "intents": [intent],
    }

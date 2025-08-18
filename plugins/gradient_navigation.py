# FILE: antsim/plugins/gradient_navigation.py
"""Pheromone gradient navigation plugin (pure, intent-producing).

Provides:
- Sensor: bb_pheromone_gradient
    Computes a simple local gradient for a given pheromone type (default: 'food') by
    scanning the 8-neighborhood and picking the neighbor with the highest level.
    Writes to BB:
      - 'pheromone_gradient_target': [x, y] or None
      - 'pheromone_gradient_strength': float >= 0
      - 'pheromone_gradient_type': str (e.g., 'food')

- Trigger: pheromone_gradient_available
    Returns True if a gradient target is present and strength > min_strength (threshold).

- Step: follow_gradient
    Moves one cell towards the chosen gradient target (usually adjacent).
    Returns:
      - {'status': 'SUCCESS'} if already at the target cell
      - {'status': 'RUNNING', 'intents': [MoveIntent]} when proposing a move
      - {'status': 'FAILURE'} if no target is available

Design constraints (Step 6+):
- Sensors: pure, write BB only.
- Triggers: pure, BB read-only.
- Steps: pure, produce intents; no world mutation.
- Executor: single movement per tick is enforced centrally.

Logging:
- Logs concise reasoning: chosen target, strength, type; step decisions.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
log = logging.getLogger(__name__)

# Tolerant import for MoveIntent (fallback to dict)
try:
    from ..core.executor import MoveIntent  # type: ignore
except Exception:
    MoveIntent = None  # type: ignore


@hookimpl
def register_sensors() -> Dict[str, callable]:
    """Expose gradient sensor."""
    return {
        "bb_pheromone_gradient": bb_pheromone_gradient_sensor,
    }


@hookimpl
def register_triggers() -> Dict[str, callable]:
    """Expose gradient presence trigger."""
    return {
        # Now supports threshold parameter via trigger_params / evaluator kwargs
        "pheromone_gradient_available": pheromone_gradient_available_trigger,
    }


@hookimpl
def register_steps() -> Dict[str, callable]:
    """Expose follow-gradient step."""
    return {
        "follow_gradient": follow_gradient_step,
    }


# ---------- Helpers (pure) ----------

def _bb_get(obj: Any, key: str, default=None):
    """Best-effort getter for worker.blackboard or attributes."""
    bb = getattr(obj, "blackboard", None)
    if bb and hasattr(bb, "get"):
        try:
            return bb.get(key, default)
        except Exception:
            pass
    return getattr(obj, key, default)


def _bb_set(obj: Any, key: str, value: Any) -> None:
    """Best-effort setter to worker.blackboard."""
    bb = getattr(obj, "blackboard", None)
    if bb and hasattr(bb, "set"):
        try:
            bb.set(key, value)
        except Exception:
            pass


def _pos(worker: Any) -> Tuple[int, int]:
    p = _bb_get(worker, "position", [0, 0])
    if isinstance(p, (list, tuple)) and len(p) == 2:
        try:
            return int(p[0]), int(p[1])
        except Exception:
            return 0, 0
    return 0, 0


def _neighbors8(x: int, y: int) -> List[Tuple[int, int]]:
    return [
        (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
        (x - 1, y),                 (x + 1, y),
        (x - 1, y + 1), (x, y + 1), (x + 1, y + 1),
    ]


def _env_has_grid(env: Any) -> bool:
    return hasattr(env, "grid") and hasattr(env, "width") and hasattr(env, "height")


def _in_bounds(env: Any, x: int, y: int) -> bool:
    return 0 <= x < getattr(env, "width", 0) and 0 <= y < getattr(env, "height", 0)


def _cell(env: Any, x: int, y: int):
    try:
        return env.grid[y][x] if _in_bounds(env, x, y) else None
    except Exception:
        return None


def _pheromone_level(cell: Any, ptype: str) -> float:
    """Best-effort: prefer typed dict 'pheromones', fallback to 'pheromone_level'."""
    if cell is None:
        return 0.0
    try:
        phs = getattr(cell, "pheromones", None)
        if isinstance(phs, dict) and ptype in phs:
            val = phs.get(ptype, 0.0)
            return float(val) if isinstance(val, (int, float)) else 0.0
    except Exception:
        pass
    try:
        lvl = getattr(cell, "pheromone_level", 0.0)
        return float(lvl) if isinstance(lvl, (int, float)) else 0.0
    except Exception:
        return 0.0


def _is_free(env: Any, x: int, y: int) -> bool:
    """Conservative 'free' check (no wall, no ant) without mutating env."""
    c = _cell(env, x, y)
    if c is None:
        return False
    try:
        if getattr(c, "cell_type", None) in ("w", "wall"):
            return False
        if getattr(c, "ant", None) is not None:
            return False
    except Exception:
        # tolerate minimal cells
        pass
    return True


def _next_step_towards(cur: Tuple[int, int], dst: Tuple[int, int], env: Any) -> Optional[Tuple[int, int]]:
    """Choose one-step neighbor moving towards dst (8-neighborhood)."""
    if cur == dst:
        return None
    sx, sy = cur
    dx = 0 if dst[0] == sx else (1 if dst[0] > sx else -1)
    dy = 0 if dst[1] == sy else (1 if dst[1] > sy else -1)
    candidates: List[Tuple[int, int]] = []
    # prioritize cardinal moves, then diagonal, then mild detours
    if dx != 0:
        candidates.append((sx + dx, sy))
    if dy != 0:
        candidates.append((sx, sy + dy))
    if dx != 0 and dy != 0:
        candidates.append((sx + dx, sy + dy))
    candidates.extend([(sx + 1, sy), (sx - 1, sy), (sx, sy + 1), (sx, sy - 1)])

    for nx, ny in candidates:
        if _in_bounds(env, nx, ny) and _is_free(env, nx, ny):
            # reduce or keep distance to dst
            if abs(nx - dst[0]) + abs(ny - dst[1]) <= abs(sx - dst[0]) + abs(sy - dst[1]):
                return (nx, ny)
    for nx, ny in candidates:
        if _in_bounds(env, nx, ny) and _is_free(env, nx, ny):
            return (nx, ny)
    return None


# ---------- Sensor (pure) ----------

def bb_pheromone_gradient_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    """
    Compute a local pheromone gradient target in the 8-neighborhood.
    Default pheromone type: 'food' (sensible for foraging demo).

    Returns dict for BB merge:
      - pheromone_gradient_target: [x, y] or None
      - pheromone_gradient_strength: float (neighbor_level - current_level; min 0)
      - pheromone_gradient_type: 'food'
    """
    if not _env_has_grid(environment):
        log.debug("sensor=bb_pheromone_gradient reason=no-grid")
        return {"pheromone_gradient_target": None, "pheromone_gradient_strength": 0.0, "pheromone_gradient_type": "food"}

    ptype = "food"  # simple default; can be extended later via params/config
    x, y = _pos(worker)
    cur_cell = _cell(environment, x, y)
    cur_level = _pheromone_level(cur_cell, ptype)

    best_pos: Optional[Tuple[int, int]] = None
    best_level = cur_level

    for nx, ny in _neighbors8(x, y):
        c = _cell(environment, nx, ny)
        if c is None:
            continue
        lvl = _pheromone_level(c, ptype)
        # Prefer strictly higher level; tie-break by first-come
        if lvl > best_level:
            best_level = lvl
            best_pos = (nx, ny)

    strength = max(0.0, float(best_level - cur_level))
    target = list(best_pos) if best_pos else None

    log.debug(
        "sensor=bb_pheromone_gradient type=%s pos=%s target=%s strength=%.3f cur=%.3f best=%.3f",
        ptype, (x, y), target, strength, cur_level, best_level
    )
    return {
        "pheromone_gradient_target": target,
        "pheromone_gradient_strength": strength,
        "pheromone_gradient_type": ptype,
    }


# ---------- Trigger (pure, BB read-only) ----------

def pheromone_gradient_available_trigger(blackboard: Any, min_strength: float = 0.0) -> bool:
    """
    True if a gradient target exists and its strength exceeds a threshold.

    Args:
      blackboard: Blackboard-like with keys 'pheromone_gradient_target' and 'pheromone_gradient_strength'
      min_strength: threshold (inclusive lower bound is False; requires strength > min_strength)
    """
    try:
        tgt = blackboard.get("pheromone_gradient_target", None)
        strength = float(blackboard.get("pheromone_gradient_strength", 0.0))
        thresh = float(min_strength) if min_strength is not None else 0.0
    except Exception:
        return False
    res = bool(tgt is not None and strength > thresh)
    log.debug("trigger=pheromone_gradient_available result=%s target=%s strength=%.3f min_strength=%.3f",
              res, tgt, strength, thresh)
    return res


# ---------- Step (pure, intents only) ----------

def follow_gradient_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Move one step towards the pheromone gradient target computed by the sensor.

    Returns:
      - SUCCESS if already at target (or no movement needed)
      - RUNNING with one MoveIntent if progressing
      - FAILURE if no valid target
    """
    wid = getattr(worker, "id", "?")
    pos = _pos(worker)
    tgt = _bb_get(worker, "pheromone_gradient_target", None)
    strength = _bb_get(worker, "pheromone_gradient_strength", 0.0)
    ptype = _bb_get(worker, "pheromone_gradient_type", "food")

    if not (isinstance(tgt, (list, tuple)) and len(tgt) == 2):
        log.info("step=follow_gradient worker=%s status=no_target pos=%s type=%s", wid, pos, ptype)
        return {"status": "FAILURE"}

    tx, ty = int(tgt[0]), int(tgt[1])
    target = (tx, ty)

    if pos == target:
        log.info("step=follow_gradient worker=%s status=on_target pos=%s type=%s strength=%.3f", wid, pos, ptype, float(strength) or 0.0)
        return {"status": "SUCCESS"}

    next_pos = _next_step_towards(pos, target, environment)
    if next_pos is None:
        log.info("step=follow_gradient worker=%s status=blocked pos=%s target=%s type=%s", wid, pos, target, ptype)
        return {"status": "FAILURE"}

    if MoveIntent is None:
        intent = {"type": "MOVE", "payload": {"target": [next_pos[0], next_pos[1]]}}
    else:
        intent = MoveIntent(target=next_pos)  # type: ignore

    log.info(
        "step=follow_gradient worker=%s decision pos=%s target=%s next=%s type=%s strength=%.3f",
        wid, pos, target, next_pos, ptype, float(strength) or 0.0
    )
    return {"status": "RUNNING", "intents": [intent]}

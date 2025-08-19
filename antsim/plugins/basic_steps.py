# FILE: antsim/plugins/basic_steps.py
"""Basic domain steps as pure intent producers.

Provides:
- do_nothing: succeed without any intents
- random_move: propose a single random valid move (8-neighborhood)
- explore_nest: prefer random moves within nest; fallback to any valid move
- find_entry: legacy alias that moves one step towards the nearest entry (wraps navigation logic)

Design:
- Pure functions: read-only on worker/environment/BB, produce intents only
- No world mutation; mutations happen via antsim.core.executor.IntentExecutor
- Logging explains decisions (targets chosen, reasons) and is concise
"""
import logging
import random
from typing import Any, Dict, List, Optional, Tuple
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
log = logging.getLogger(__name__)

# Tolerant imports for intents (fallback to plain dict payloads if core.executor is not available)
try:
    from ..core.executor import MoveIntent  # type: ignore
except Exception:
    MoveIntent = None  # type: ignore


@hookimpl
def register_steps() -> Dict[str, callable]:
    """Register basic steps (no collisions with existing names)."""
    return {
        "do_nothing": do_nothing_step,
        "random_move": random_move_step,
        "explore_nest": explore_nest_step,
        "find_entry": find_entry_step,  # legacy alias
    }


# ---------- Helpers (pure) ----------

def _bb_get(obj: Any, key: str, default=None):
    bb = getattr(obj, "blackboard", None)
    if bb and hasattr(bb, "get"):
        try:
            return bb.get(key, default)
        except Exception:
            pass
    return getattr(obj, key, default)


def _bb_pos(worker: Any) -> Tuple[int, int]:
    pos = _bb_get(worker, "position", [0, 0])
    try:
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            return int(pos[0]), int(pos[1])
    except Exception:
        pass
    return 0, 0


def _env_bounds(env: Any) -> Optional[Tuple[int, int]]:
    w = getattr(env, "width", None)
    h = getattr(env, "height", None)
    if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
        return w, h
    return None


def _in_bounds(p: Tuple[int, int], bounds: Optional[Tuple[int, int]]) -> bool:
    if not bounds:
        return True
    x, y = p
    w, h = bounds
    return 0 <= x < w and 0 <= y < h


def _cell_free(env: Any, p: Tuple[int, int]) -> bool:
    """Best-effort free check (no wall, no ant)."""
    try:
        if not hasattr(env, "grid"):
            return True
        x, y = p
        cell = env.grid[y][x]
        if hasattr(cell, "cell_type") and getattr(cell, "cell_type") in ("w", "wall"):
            return False
        if hasattr(cell, "ant") and getattr(cell, "ant") is not None:
            return False
        return True
    except Exception:
        return True


def _neighbors8(x: int, y: int) -> List[Tuple[int, int]]:
    return [
        (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
        (x - 1, y),                 (x + 1, y),
        (x - 1, y + 1), (x, y + 1), (x + 1, y + 1)
    ]


def _neighbors4(x: int, y: int) -> List[Tuple[int, int]]:
    return [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]


def _get_cell_type(env: Any, p: Tuple[int, int]) -> Optional[str]:
    try:
        if hasattr(env, "grid"):
            x, y = p
            cell = env.grid[y][x]
            return getattr(cell, "cell_type", None)
    except Exception:
        pass
    return None


def _entries(env: Any) -> List[Tuple[int, int]]:
    if hasattr(env, "entry_positions") and isinstance(env.entry_positions, (list, tuple)):
        return [tuple(e) for e in env.entry_positions]  # type: ignore
    if hasattr(env, "entry_position") and env.entry_position:
        try:
            return [tuple(env.entry_position)]
        except Exception:
            pass
    return []


def _manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _nearest_entry(pos: Tuple[int, int], entries: List[Tuple[int, int]], env: Any) -> Optional[Tuple[int, int]]:
    if not entries:
        return None
    ranked = sorted(entries, key=lambda e: (_cell_free(env, e) is False, _manhattan(pos, e)))
    return ranked[0]


def _next_step_towards(src: Tuple[int, int], dst: Tuple[int, int], env: Any) -> Optional[Tuple[int, int]]:
    if src == dst:
        return None
    sx, sy = src
    dx = 0 if dst[0] == sx else (1 if dst[0] > sx else -1)
    dy = 0 if dst[1] == sy else (1 if dst[1] > sy else -1)
    candidates: List[Tuple[int, int]] = []
    if dx != 0:
        candidates.append((sx + dx, sy))
    if dy != 0:
        candidates.append((sx, sy + dy))
    if dx != 0 and dy != 0:
        candidates.append((sx + dx, sy + dy))
    # mild detours
    candidates.extend([(sx + 1, sy), (sx - 1, sy), (sx, sy + 1), (sx, sy - 1)])
    bounds = _env_bounds(env)
    for np in candidates:
        if _in_bounds(np, bounds) and _cell_free(env, np) and _manhattan(np, dst) <= _manhattan(src, dst):
            return np
    for np in candidates:
        if _in_bounds(np, bounds) and _cell_free(env, np):
            return np
    return None


# ---------- Steps (pure) ----------

def do_nothing_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """Succeed without intents (idle)."""
    wid = getattr(worker, "id", "?")
    log.info("step=do_nothing worker=%s", wid)
    return {"status": "SUCCESS"}


def random_move_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """Propose a random valid move to an adjacent free cell (8-neighborhood)."""
    wid = getattr(worker, "id", "?")
    x, y = _bb_pos(worker)
    bounds = _env_bounds(environment)
    options = [(nx, ny) for (nx, ny) in _neighbors8(x, y) if _in_bounds((nx, ny), bounds) and _cell_free(environment, (nx, ny))]
    if not options:
        log.info("step=random_move worker=%s status=no_valid_moves pos=%s", wid, (x, y))
        return {"status": "FAILURE"}
    target = random.choice(options)
    intent = {"type": "MOVE", "payload": {"target": [target[0], target[1]]}} if MoveIntent is None else MoveIntent(target=target)  # type: ignore
    log.info("step=random_move worker=%s decision pos=%s target=%s options=%d", wid, (x, y), target, len(options))
    return {"status": "SUCCESS", "intents": [intent]}


def explore_nest_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Prefer moving within nest cells; fallback to any valid neighbor.
    If already no valid move, fail to allow BT fallbacks.
    """
    wid = getattr(worker, "id", "?")
    x, y = _bb_pos(worker)
    bounds = _env_bounds(environment)

    # Try nest-only neighbors first
    nest_neighbors = []
    for nx, ny in _neighbors8(x, y):
        np = (nx, ny)
        if not _in_bounds(np, bounds) or not _cell_free(environment, np):
            continue
        if _get_cell_type(environment, np) in ("nest", "e"):
            nest_neighbors.append(np)

    target: Optional[Tuple[int, int]] = None
    if nest_neighbors:
        target = random.choice(nest_neighbors)
        reason = "nest_neighbor"
    else:
        # Fallback: any free neighbor
        all_free = [(nx, ny) for (nx, ny) in _neighbors8(x, y) if _in_bounds((nx, ny), bounds) and _cell_free(environment, (nx, ny))]
        if not all_free:
            log.info("step=explore_nest worker=%s status=no_valid_moves pos=%s", wid, (x, y))
            return {"status": "FAILURE"}
        target = random.choice(all_free)
        reason = "fallback_any"

    intent = {"type": "MOVE", "payload": {"target": [target[0], target[1]]}} if MoveIntent is None else MoveIntent(target=target)  # type: ignore
    log.info("step=explore_nest worker=%s decision pos=%s target=%s reason=%s", wid, (x, y), target, reason)
    return {"status": "SUCCESS", "intents": [intent]}


def find_entry_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Legacy alias: move one step towards nearest entry cell.
    Returns:
      - SUCCESS if already at an entry
      - RUNNING with one MoveIntent when progressing towards entry
      - FAILURE if no entries known or blocked
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    entries = _entries(environment)
    if not entries:
        log.warning("step=find_entry worker=%s reason=no_entries_known pos=%s", wid, pos)
        return {"status": "FAILURE"}

    if pos in entries:
        log.info("step=find_entry worker=%s status=already_at_entry pos=%s", wid, pos)
        return {"status": "SUCCESS"}

    target = _nearest_entry(pos, entries, environment)
    if target is None:
        log.warning("step=find_entry worker=%s reason=cannot_resolve_target pos=%s", wid, pos)
        return {"status": "FAILURE"}

    next_pos = _next_step_towards(pos, target, environment)
    if next_pos is None:
        log.info("step=find_entry worker=%s status=blocked pos=%s target=%s", wid, pos, target)
        return {"status": "FAILURE"}

    intent = {"type": "MOVE", "payload": {"target": [next_pos[0], next_pos[1]]}} if MoveIntent is None else MoveIntent(target=next_pos)  # type: ignore
    log.info("step=find_entry worker=%s decision pos=%s target_entry=%s next=%s", wid, pos, target, next_pos)
    return {"status": "RUNNING", "intents": [intent]}

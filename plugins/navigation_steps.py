# FILE: antsim/plugins/navigation_steps.py
"""Navigation-related domain steps (pure intent producers).

Provides:
- move_to_entry: move one step towards nearest entry cell.
Design:
- Pure: reads worker/environment/BB, produces intents only.
- No world mutation; execution via antsim.core.executor.IntentExecutor.
- Logs decision context (chosen target, next hop, reasons).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from pluggy import HookimplMarker

# Tolerant imports for intents (fallback to dict if not available)
try:
    from ..core.executor import MoveIntent  # type: ignore
except Exception:
    MoveIntent = None  # type: ignore

hookimpl = HookimplMarker("antsim")
log = logging.getLogger(__name__)


@hookimpl
def register_steps() -> Dict[str, callable]:
    """Expose navigation steps."""
    return {
        "move_to_entry": move_to_entry_step,
    }


# --------- Helpers (pure) ---------

def _bb_pos(worker: Any) -> Tuple[int, int]:
    bb = getattr(worker, "blackboard", None)
    if bb and hasattr(bb, "get"):
        pos = bb.get("position", [0, 0])
        try:
            return int(pos[0]), int(pos[1])
        except Exception:
            pass
    pos = getattr(worker, "position", None)
    if isinstance(pos, (list, tuple)) and len(pos) == 2:
        return int(pos[0]), int(pos[1])
    return 0, 0


def _env_bounds(env: Any) -> Optional[Tuple[int, int]]:
    w = getattr(env, "width", None)
    h = getattr(env, "height", None)
    if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
        return w, h
    return None


def _env_entries(env: Any) -> List[Tuple[int, int]]:
    if hasattr(env, "entry_positions") and isinstance(env.entry_positions, (list, tuple)):
        return [tuple(e) for e in env.entry_positions]  # type: ignore
    if hasattr(env, "entry_position") and env.entry_position:
        try:
            return [tuple(env.entry_position)]
        except Exception:
            pass
    return []


def _in_bounds(p: Tuple[int, int], bounds: Optional[Tuple[int, int]]) -> bool:
    if not bounds:
        return True
    x, y = p
    w, h = bounds
    return 0 <= x < w and 0 <= y < h


def _cell_free(env: Any, p: Tuple[int, int]) -> bool:
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


def _manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _nearest_entry(pos: Tuple[int, int], entries: List[Tuple[int, int]], env: Any) -> Optional[Tuple[int, int]]:
    """Choose nearest entry; prefer free cells if grid known."""
    if not entries:
        return None
    # sort by (blocked, distance)
    ranked = sorted(entries, key=lambda e: (_cell_free(env, e) is False, _manhattan(pos, e)))
    return ranked[0]


def _next_step_towards(src: Tuple[int, int], dst: Tuple[int, int], env: Any) -> Optional[Tuple[int, int]]:
    """Choose a single-step neighbor that reduces distance; prefer 4-neighborhood, then diagonals."""
    if src == dst:
        return None
    sx, sy = src
    dx = 0 if dst[0] == sx else (1 if dst[0] > sx else -1)
    dy = 0 if dst[1] == sy else (1 if dst[1] > sy else -1)
    candidate_order: List[Tuple[int, int]] = []
    # 4-neighborhood first
    if dx != 0:
        candidate_order.append((sx + dx, sy))
    if dy != 0:
        candidate_order.append((sx, sy + dy))
    # allow diagonal as fallback (executor permits 8-neighborhood)
    if dx != 0 and dy != 0:
        candidate_order.append((sx + dx, sy + dy))
    # if both axes aligned but primary blocked, try perpendiculars for mild detour
    candidate_order.extend([(sx + 1, sy), (sx - 1, sy), (sx, sy + 1), (sx, sy - 1)])

    bounds = _env_bounds(env)
    for nx, ny in candidate_order:
        np = (nx, ny)
        if not _in_bounds(np, bounds):
            continue
        if not _cell_free(env, np):
            continue
        # prefer real progress
        if _manhattan(np, dst) <= _manhattan(src, dst):
            return np
    # no improving move found; allow first free neighbor as last resort
    for nx, ny in candidate_order:
        np = (nx, ny)
        if _in_bounds(np, bounds) and _cell_free(env, np):
            return np
    return None


# --------- Step (pure) ---------

def move_to_entry_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Move one cell towards the nearest entry position.
    Returns:
      - {'status': 'SUCCESS'} if already at entry.
      - {'status': 'RUNNING', 'intents': [MoveIntent]} if a move is proposed.
      - {'status': 'FAILURE'} if no entry is known or no valid move found.
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    entries = _env_entries(environment)
    if not entries:
        log.warning("step=move_to_entry worker=%s reason=no_entries_known pos=%s", wid, pos)
        return {"status": "FAILURE"}

    # Already at any entry?
    if pos in entries:
        log.info("step=move_to_entry worker=%s status=already_at_entry pos=%s", wid, pos)
        return {"status": "SUCCESS"}

    target = _nearest_entry(pos, entries, environment)
    if target is None:
        log.warning("step=move_to_entry worker=%s reason=cannot_resolve_target pos=%s", wid, pos)
        return {"status": "FAILURE"}

    next_pos = _next_step_towards(pos, target, environment)
    if next_pos is None:
        log.info("step=move_to_entry worker=%s status=blocked pos=%s target=%s", wid, pos, target)
        return {"status": "FAILURE"}

    # Build intent (tolerate missing dataclass)
    if MoveIntent is None:
        intent = {"type": "MOVE", "payload": {"target": [next_pos[0], next_pos[1]]}}
    else:
        intent = MoveIntent(target=next_pos)  # type: ignore

    log.info(
        "step=move_to_entry worker=%s decision pos=%s target_entry=%s next=%s",
        wid, pos, target, next_pos
    )
    return {"status": "RUNNING", "intents": [intent]}

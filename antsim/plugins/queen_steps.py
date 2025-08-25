# FILE: antsim/plugins/queen_steps.py
"""Queen-related domain steps as pure intent producers.

Provides:
- move_to_queen: move one step towards a suitable adjacent cell near the queen
- feed_queen: produce a FeedIntent for the queen if adjacent and social stomach > 0

Design:
- Pure functions: read worker/environment/BB, produce intents only
- No world mutation here; IntentExecutor applies effects and enforces the one-move rule
- Clear decision logging (reasons, targets) for traceability
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
log = logging.getLogger(__name__)

# Tolerant imports for intents (fallback to plain dicts if not present)
try:
    from ..core.executor import MoveIntent, FeedIntent  # type: ignore
except Exception:
    MoveIntent = None  # type: ignore
    FeedIntent = None  # type: ignore


@hookimpl
def register_steps() -> Dict[str, callable]:
    """Expose queen-related steps (both for workers interacting with queen and queen-specific behaviors)."""
    return {
        "move_to_queen": move_to_queen_step,
        "feed_queen": feed_queen_step,
        "signal_hunger": signal_hunger_step,
        "idle": idle_step,
    }


# ---------- Helpers (pure) ----------

def _bb_get(obj: Any, key: str, default=None):
    """Best-effort getter from blackboard or attributes (pure)."""
    bb = getattr(obj, "blackboard", None)
    if bb and hasattr(bb, "get"):
        try:
            return bb.get(key, default)
        except Exception:
            pass
    return getattr(obj, key, default)


def _bb_pos(worker: Any) -> Tuple[int, int]:
    """Get worker position from blackboard or attributes (pure)."""
    pos = _bb_get(worker, "position", [0, 0])
    if isinstance(pos, (list, tuple)) and len(pos) == 2:
        try:
            return int(pos[0]), int(pos[1])
        except Exception:
            return 0, 0
    return 0, 0


def _env_bounds(env: Any) -> Optional[Tuple[int, int]]:
    w = getattr(env, "width", None)
    h = getattr(env, "height", None)
    if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
        return w, h
    return None


def _in_bounds(pos: Tuple[int, int], bounds: Optional[Tuple[int, int]]) -> bool:
    if not bounds:
        return True
    x, y = pos
    w, h = bounds
    return 0 <= x < w and 0 <= y < h


def _cell_free(env: Any, pos: Tuple[int, int]) -> bool:
    """True if cell is walkable and not occupied (pure check)."""
    try:
        if not hasattr(env, "grid"):
            return True
        x, y = pos
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


def _next_step_towards(src: Tuple[int, int], dst: Tuple[int, int], env: Any) -> Optional[Tuple[int, int]]:
    """Pick a single next cell reducing distance to dst; prefer 4-neighborhood, then diagonals."""
    if src == dst:
        return None
    sx, sy = src
    dx = 0 if dst[0] == sx else (1 if dst[0] > sx else -1)
    dy = 0 if dst[1] == sy else (1 if dst[1] > sy else -1)
    candidates: List[Tuple[int, int]] = []
    # primary (4-neighborhood)
    if dx != 0:
        candidates.append((sx + dx, sy))
    if dy != 0:
        candidates.append((sx, sy + dy))
    # diagonal fallback
    if dx != 0 and dy != 0:
        candidates.append((sx + dx, sy + dy))
    # mild detours as last resort
    candidates.extend([(sx + 1, sy), (sx - 1, sy), (sx, sy + 1), (sx, sy - 1)])

    bounds = _env_bounds(env)
    for nx, ny in candidates:
        np = (nx, ny)
        if not _in_bounds(np, bounds):
            continue
        if not _cell_free(env, np):
            continue
        if _manhattan(np, dst) <= _manhattan(src, dst):
            return np
    # fallback: any free candidate
    for nx, ny in candidates:
        np = (nx, ny)
        if _in_bounds(np, bounds) and _cell_free(env, np):
            return np
    return None


def _find_queen(env: Any) -> Tuple[Optional[Any], Optional[Tuple[int, int]]]:
    """Best-effort queen lookup: env.queen, then ant_registry, then id=0 via get_ant_by_id."""
    q = getattr(env, "queen", None)
    if q is not None:
        pos = getattr(q, "position", None)
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            return q, (int(pos[0]), int(pos[1]))
    # try ant_registry
    reg = getattr(env, "ant_registry", None)
    if isinstance(reg, dict):
        for ant in reg.values():
            if ant is None:
                continue
            # Heuristics: class name Queen, or has egg-laying attribute
            if getattr(ant, "__class__", type(ant)).__name__ == "Queen" or hasattr(ant, "egg_laying_interval"):
                pos = getattr(ant, "position", None)
                if isinstance(pos, (list, tuple)) and len(pos) == 2:
                    return ant, (int(pos[0]), int(pos[1]))
    # fallback id=0
    get_by_id = getattr(env, "get_ant_by_id", None)
    if callable(get_by_id):
        try:
            ant0 = get_by_id(0)
            if ant0 is not None:
                pos = getattr(ant0, "position", None)
                if isinstance(pos, (list, tuple)) and len(pos) == 2:
                    return ant0, (int(pos[0]), int(pos[1]))
        except Exception:
            pass
    return None, None


# ---------- Steps (pure) ----------

def move_to_queen_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Move one step towards a free adjacent position near the queen.
    - SUCCESS if already adjacent
    - RUNNING with one MoveIntent if moving towards adjacency
    - FAILURE if queen not found or no valid move
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    queen, qpos = _find_queen(environment)
    if queen is None or qpos is None:
        log.warning("step=move_to_queen worker=%s reason=no_queen pos=%s", wid, pos)
        return {"status": "FAILURE"}

    # Already adjacent?
    if max(abs(pos[0] - qpos[0]), abs(pos[1] - qpos[1])) <= 1:
        log.info("step=move_to_queen worker=%s status=adjacent pos=%s queen=%s", wid, pos, qpos)
        return {"status": "SUCCESS"}

    # Collect candidate adjacency cells around queen (prefer free, nearest)
    adj: List[Tuple[int, int]] = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            npos = (qpos[0] + dx, qpos[1] + dy)
            if _in_bounds(npos, _env_bounds(environment)) and _cell_free(environment, npos):
                adj.append(npos)

    target = None
    if adj:
        adj.sort(key=lambda p: _manhattan(pos, p))
        target = adj[0]
    else:
        # Fall back to queen cell itself (executor still enforces occupancy)
        target = qpos

    next_pos = _next_step_towards(pos, target, environment)
    if next_pos is None:
        log.info(
            "step=move_to_queen worker=%s status=blocked pos=%s queen=%s target=%s",
            wid, pos, qpos, target
        )
        return {"status": "FAILURE"}

    # Build move intent
    if MoveIntent is None:
        intent = {"type": "MOVE", "payload": {"target": [next_pos[0], next_pos[1]]}}
    else:
        intent = MoveIntent(target=next_pos)  # type: ignore

    log.info(
        "step=move_to_queen worker=%s decision pos=%s queen=%s target_adj=%s next=%s",
        wid, pos, qpos, target, next_pos
    )
    return {"status": "RUNNING", "intents": [intent]}


def feed_queen_step(worker: Any, environment: Any, amount: Optional[int] = None, **kwargs) -> Dict[str, Any]:
    """
    Feed the queen if adjacent and social stomach has food.
    - SUCCESS with FeedIntent if prerequisites met
    - FAILURE otherwise
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    queen, qpos = _find_queen(environment)
    if queen is None or qpos is None:
        log.warning("step=feed_queen worker=%s reason=no_queen pos=%s", wid, pos)
        return {"status": "FAILURE"}

    # Must be adjacent
    if max(abs(pos[0] - qpos[0]), abs(pos[1] - qpos[1])) > 1:
        log.info("step=feed_queen worker=%s status=not_adjacent pos=%s queen=%s", wid, pos, qpos)
        return {"status": "FAILURE"}

    # Check social stomach
    social = _bb_get(worker, "social_stomach", 0)
    try:
        social_val = int(social)
    except Exception:
        social_val = 0
    if social_val <= 0:
        log.info("step=feed_queen worker=%s status=no_social_food pos=%s queen=%s", wid, pos, qpos)
        return {"status": "FAILURE"}

    # Build feed intent
    qid = getattr(queen, "id", 0)
    if FeedIntent is None:
        payload = {"target_id": int(qid)}
        if amount is not None:
            payload["amount"] = int(amount)
        intent = {"type": "FEED", "payload": payload}
    else:
        intent = FeedIntent(target_id=int(qid), amount=None if amount is None else int(amount))  # type: ignore

    log.info("step=feed_queen worker=%s decision target=%s pos=%s queen=%s amount=%s",
             wid, qid, pos, qpos, amount)
    # Return SUCCESS to allow sequence to complete; executor applies the intent this tick
    return {"status": "SUCCESS", "intents": [intent]}


# ---------- Queen-specific steps ----------

def signal_hunger_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """Queen signals hunger without moving.
    
    This step allows the queen to signal her hunger state to nearby workers
    without any movement. Workers can detect this via their sensors.
    
    Returns:
        SUCCESS: Always succeeds, signaling is passive
    """
    qid = getattr(worker, 'id', '?')
    log.debug("step=signal_hunger queen=%s (passive signaling)", qid)
    
    # Set hunger signaling flag on blackboard for workers to detect
    bb = getattr(worker, 'blackboard', None)  
    if bb:
        bb.set('signaling_hunger', True)
        log.debug("step=signal_hunger queen=%s set signaling_hunger flag", qid)
    
    return {"status": "SUCCESS"}


def idle_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """Queen remains idle, waiting passively.
    
    This is the default queen behavior when not hungry.
    The queen stays in place and waits.
    
    Returns:
        SUCCESS: Always succeeds
    """
    qid = getattr(worker, 'id', '?')
    log.debug("step=idle queen=%s (no action)", qid)
    
    # Ensure signaling_hunger is cleared when idle
    bb = getattr(worker, 'blackboard', None)
    if bb:
        bb.set('signaling_hunger', False)
    
    return {"status": "SUCCESS"}

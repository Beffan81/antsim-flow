# FILE: antsim/plugins/example_plugin.py
# plugins/example_plugin.py
"""Example plugin demonstrating the plugin interface with intent-producing steps."""
import logging
from typing import Dict, Any, Optional, Tuple
from pluggy import HookimplMarker

# Import intent types (pure creation; no world mutation here)
try:
    from ..core.executor import MoveIntent, DepositPheromoneIntent, FeedIntent  # antsim.core.executor
except Exception:  # tolerate import issues during isolated plugin tests
    MoveIntent = None  # type: ignore
    DepositPheromoneIntent = None  # type: ignore
    FeedIntent = None  # type: ignore

logger = logging.getLogger(__name__)
hookimpl = HookimplMarker("antsim")


@hookimpl
def register_steps() -> Dict[str, callable]:
    """Register example step functions."""
    return {
        "example_move": example_move_step,
        "example_wait": example_wait_step,
        # New intent-only demo steps
        "example_deposit_pheromone": example_deposit_pheromone_step,
        "example_feed_neighbor": example_feed_neighbor_step,
    }


@hookimpl
def register_triggers() -> Dict[str, callable]:
    """Register example trigger functions."""
    return {
        "always_true": always_true_trigger,
        "random_chance": random_chance_trigger,
    }


@hookimpl
def register_sensors() -> Dict[str, callable]:
    """Register example sensor functions."""
    return {
        "position_sensor": position_sensor,
        "time_sensor": time_sensor,
    }


# ---------- Helpers (pure) ----------

def _bb_get_pos(worker: Any) -> Tuple[int, int]:
    """Best-effort position getter (supports Worker with blackboard or simple attrs)."""
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
    x = getattr(worker, "x", 0)
    y = getattr(worker, "y", 0)
    return int(x), int(y)


def _env_bounds(env: Any) -> Optional[Tuple[int, int]]:
    w = getattr(env, "width", None)
    h = getattr(env, "height", None)
    if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
        return w, h
    return None


def _choose_next_move(worker: Any, env: Any) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
    """
    Choose a simple next cell: prefer right, then down, left, up (4-neighborhood).
    Returns (target, delta). Either can be None if undecided.
    """
    x, y = _bb_get_pos(worker)
    bounds = _env_bounds(env)
    candidates = [(x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)]
    for nx, ny in candidates:
        if not bounds:
            return (nx, ny), (nx - x, ny - y)
        w, h = bounds
        if 0 <= nx < w and 0 <= ny < h:
            return (nx, ny), (nx - x, ny - y)
    return None, None


def _bb_get(worker: Any, key: str, default=None):
    """Safe getter for Blackboard-like or dict-like worker/worker.bb."""
    bb = getattr(worker, "blackboard", None)
    if bb and hasattr(bb, "get"):
        try:
            return bb.get(key, default)
        except Exception:
            pass
    return getattr(worker, key, default)


# ---------- Step implementations (pure; produce intents only) ----------

def example_move_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Produce a single MoveIntent towards a simple neighboring cell.
    - Pure: no direct world/BB mutation.
    - Executor will enforce single-move-per-tick and collisions.
    Returns: {'status': 'SUCCESS', 'intents': [MoveIntent(...)]}
    """
    target, delta = _choose_next_move(worker, environment)
    if MoveIntent is None:
        intent = {"type": "MOVE", "payload": {"target": list(target) if target else None, "delta": list(delta) if delta else None}}
    else:
        intent = MoveIntent(target=target, delta=delta)  # type: ignore

    wid = getattr(worker, "id", "?")
    logger.info("example_move_step worker=%s target=%s delta=%s", wid, target, delta)
    return {"status": "SUCCESS", "intents": [intent]}


def example_wait_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """Do nothing; succeed without intents (pure)."""
    wid = getattr(worker, "id", "?")
    logger.debug("example_wait_step worker=%s", wid)
    return {"status": "SUCCESS"}


def example_deposit_pheromone_step(worker: Any, environment: Any, ptype: str = "food", strength: int = 1, **kwargs) -> Dict[str, Any]:
    """
    Produce a DepositPheromoneIntent at current cell (pure).
    Params:
      - ptype: pheromone type label (e.g., 'food', 'hunger')
      - strength: deposit strength (int)
    """
    if DepositPheromoneIntent is None:
        intent = {"type": "PHEROMONE", "payload": {"ptype": str(ptype), "strength": int(strength)}}
    else:
        intent = DepositPheromoneIntent(ptype=str(ptype), strength=int(strength))  # type: ignore
    wid = getattr(worker, "id", "?")
    logger.info("example_deposit_pheromone_step worker=%s ptype=%s strength=%s", wid, ptype, strength)
    return {"status": "SUCCESS", "intents": [intent]}


def example_feed_neighbor_step(worker: Any, environment: Any, amount: Optional[int] = None, **kwargs) -> Dict[str, Any]:
    """
    Produce a FeedIntent if a hungry neighbor id is present and social stomach has content.
    Pure step: reads BB, emits intent; no mutation here.
    Returns FAILURE when prerequisites are not met to allow BT fallbacks.
    """
    target_id = _bb_get(worker, "hungry_neighbor_id", None)
    social = _bb_get(worker, "social_stomach", 0)

    wid = getattr(worker, "id", "?")
    if target_id is None:
        logger.debug("example_feed_neighbor_step worker=%s reason=no_target", wid)
        return {"status": "FAILURE"}
    if not isinstance(social, (int, float)) or social <= 0:
        logger.debug("example_feed_neighbor_step worker=%s reason=no_social_food target=%s", wid, target_id)
        return {"status": "FAILURE"}

    if FeedIntent is None:
        payload = {"target_id": int(target_id)}
        if amount is not None:
            payload["amount"] = int(amount)
        intent = {"type": "FEED", "payload": payload}
    else:
        intent = FeedIntent(target_id=int(target_id), amount=None if amount is None else int(amount))  # type: ignore

    logger.info("example_feed_neighbor_step worker=%s target=%s amount=%s", wid, target_id, amount)
    return {"status": "SUCCESS", "intents": [intent]}


# ---------- Trigger implementations ----------

def always_true_trigger(blackboard: Dict[str, Any]) -> bool:
    """Trigger that always returns True."""
    return True


def random_chance_trigger(blackboard: Dict[str, Any], p: float = 0.5) -> bool:
    """
    Deterministic 'random chance' trigger based on blackboard fields.
    Reads 'cycle' and 'agent_id' to derive a stable pseudo-random fraction in [0,1).
    Returns True if fraction > p. Pure and BB-read-only.
    """
    try:
        cycle = int(blackboard.get("cycle", 0))
    except Exception:
        cycle = 0
    try:
        aid = int(blackboard.get("agent_id", 0))
    except Exception:
        aid = 0
    # Simple LCG-like mix for determinism without global RNG
    val = (cycle * 1103515245 + aid * 12345) & 0x7FFFFFFF
    frac = (val % 1000000) / 1000000.0  # [0,1)
    try:
        threshold = float(p)
    except Exception:
        threshold = 0.5
    return frac > threshold


# ---------- Sensor implementations (pure) ----------

def position_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    """Sensor that reads worker position (best-effort)."""
    x, y = _bb_get_pos(worker)
    return {"position_x": x, "position_y": y}


def time_sensor(worker: Any, environment: Any) -> Dict[str, Any]:
    """Sensor that reads current simulation time."""
    return {"cycle_count": getattr(environment, "cycle_count", 0)}

# FILE: antsim/plugins/brood_steps.py
"""Brood-related step as pure intent producer.

Provides:
- feed_brood: If an adjacent Brood is hungry and worker has social food, emit a FeedIntent.

Constraints:
- Pure function: reads worker/environment/BB; produces intents only.
- No direct world mutation here; IntentExecutor applies effects and enforces rules.
- Clear decision logging for traceability.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
log = logging.getLogger(__name__)

# Tolerant imports for intents (allow running even if executor isn't importable in isolation)
try:
    from ..core.executor import FeedIntent  # type: ignore
except Exception:
    FeedIntent = None  # type: ignore


@hookimpl
def register_steps() -> Dict[str, callable]:
    """Expose brood-related steps."""
    return {
        "feed_brood": feed_brood_step,
    }


# ---------- Helpers (pure) ----------

def _bb_get(obj: Any, key: str, default=None):
    """Safe getter from blackboard or attributes."""
    bb = getattr(obj, "blackboard", None)
    if bb and hasattr(bb, "get"):
        try:
            return bb.get(key, default)
        except Exception:
            pass
    return getattr(obj, key, default)


def _bb_pos(worker: Any) -> Tuple[int, int]:
    pos = _bb_get(worker, "position", [0, 0])
    if isinstance(pos, (list, tuple)) and len(pos) == 2:
        try:
            return int(pos[0]), int(pos[1])
        except Exception:
            return 0, 0
    return 0, 0


def _neighbors8(x: int, y: int) -> List[Tuple[int, int]]:
    return [
        (x - 1, y - 1), (x, y - 1), (x + 1, y - 1),
        (x - 1, y),                 (x + 1, y),
        (x - 1, y + 1), (x, y + 1), (x + 1, y + 1),
    ]


def _env_has_lookup(env: Any) -> bool:
    return hasattr(env, "get_ant_at_position")


def _is_brood(ant: Any) -> bool:
    """Heuristic brood identification: by class name."""
    if ant is None:
        return False
    name = getattr(getattr(ant, "__class__", type(ant)), "__name__", "")
    return name == "Brood"


def _hunger_ratio(ant: Any) -> Optional[float]:
    """Compute individual hunger ratio (smaller => hungrier)."""
    try:
        cur = getattr(ant, "current_stomach", None)
        cap = getattr(ant, "stomach_capacity", None)
        thr = getattr(ant, "hunger_threshold", None)
        # Prefer threshold if present, else capacity
        denom = thr if isinstance(thr, (int, float)) and thr > 0 else cap
        if isinstance(cur, (int, float)) and isinstance(denom, (int, float)) and denom > 0:
            return float(cur) / float(denom)
    except Exception:
        pass
    return None


# ---------- Step (pure) ----------

def feed_brood_step(worker: Any, environment: Any, amount: Optional[int] = None, **kwargs) -> Dict[str, Any]:
    """
    Feed adjacent Brood using worker's social stomach.

    Preconditions:
    - Adjacent Brood present and hungry (based on stomach vs threshold)
    - Worker social_stomach > 0

    Returns:
    - {'status': 'SUCCESS', 'intents': [FeedIntent]} if an intent is produced
    - {'status': 'FAILURE'} otherwise (allows BT fallbacks)
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)

    # Ensure env supports neighbor lookup
    if not _env_has_lookup(environment):
        log.debug("step=feed_brood worker=%s reason=env_no_lookup pos=%s", wid, pos)
        return {"status": "FAILURE"}

    # Check worker social stomach
    social = _bb_get(worker, "social_stomach", 0)
    try:
        social_val = int(social)
    except Exception:
        social_val = 0
    if social_val <= 0:
        log.info("step=feed_brood worker=%s status=no_social_food pos=%s", wid, pos)
        return {"status": "FAILURE"}

    # Scan 8-neighborhood for Brood candidates; choose hungriest
    x, y = pos
    best_brood = None
    best_ratio = 2.0  # larger than any realistic hunger ratio
    for nx, ny in _neighbors8(x, y):
        ant = environment.get_ant_at_position(nx, ny)
        if not _is_brood(ant):
            continue
        ratio = _hunger_ratio(ant)
        if ratio is None:
            continue
        # consider only "hungry" brood (ratio < 1.0 approx threshold/capacity)
        if ratio < best_ratio and ratio < 1.0:
            best_ratio = ratio
            best_brood = ant

    if best_brood is None:
        log.debug("step=feed_brood worker=%s status=no_hungry_brood pos=%s", wid, pos)
        return {"status": "FAILURE"}

    target_id = getattr(best_brood, "id", None)
    if target_id is None:
        log.debug("step=feed_brood worker=%s status=target_no_id pos=%s", wid, pos)
        return {"status": "FAILURE"}

    # Build feed intent (amount optional)
    if FeedIntent is None:
        payload = {"target_id": int(target_id)}
        if amount is not None:
            try:
                payload["amount"] = int(amount)
            except Exception:
                pass
        intent = {"type": "FEED", "payload": payload}
    else:
        intent = FeedIntent(target_id=int(target_id), amount=None if amount is None else int(amount))  # type: ignore

    log.info(
        "step=feed_brood worker=%s decision target=%s pos=%s target_ratio=%.3f amount=%s",
        wid, target_id, pos, best_ratio, amount
    )
    return {"status": "SUCCESS", "intents": [intent]}

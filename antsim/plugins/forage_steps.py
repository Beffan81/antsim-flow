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

# FILE: antsim/core/executor.py
# antsim/core/executor.py
"""Centralized intent execution for the new core.

Provides:
- Intent dataclasses (Move, Feed, DepositPheromone, Custom)
- Executor enforcing single-move-per-tick and structured decision logging
- Stateless helpers to validate/apply world mutations

Notes:
- Steps shall only create intents; mutations happen here.
- Executor aims to be environment-agnostic and tolerant to minimalist envs.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

log = logging.getLogger(__name__)

# Structured events
try:
    from ..io.event_logger import get_event_logger, EventType
except Exception:  # safe import for isolated unit tests
    get_event_logger = None  # type: ignore
    EventType = None  # type: ignore


# ---------- Intent types ----------

@dataclass(frozen=True)
class Intent:
    """Base intent with type label and payload."""
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "payload": dict(self.payload)}


@dataclass(frozen=True)
class MoveIntent(Intent):
    """Move by absolute target or delta."""
    def __init__(self, target: Optional[Tuple[int, int]] = None, delta: Optional[Tuple[int, int]] = None):
        payload = {}
        if target is not None:
            payload["target"] = [int(target[0]), int(target[1])]
        if delta is not None:
            payload["delta"] = [int(delta[0]), int(delta[1])]
        super().__init__("MOVE", payload)


@dataclass(frozen=True)
class FeedIntent(Intent):
    """Feed target agent from social stomach."""
    def __init__(self, target_id: int, amount: Optional[int] = None):
        super().__init__("FEED", {"target_id": int(target_id), "amount": None if amount is None else int(amount)})


@dataclass(frozen=True)
class DepositPheromoneIntent(Intent):
    """Deposit pheromone at current/target cell."""
    def __init__(self, ptype: str, strength: int = 1, position: Optional[Tuple[int, int]] = None):
        payload = {"ptype": str(ptype), "strength": int(strength)}
        if position is not None:
            payload["position"] = [int(position[0]), int(position[1])]
        super().__init__("PHEROMONE", payload)


@dataclass(frozen=True)
class CustomIntent(Intent):
    """Arbitrary effect routed to environment-specific handlers."""
    def __init__(self, name: str, payload: Dict[str, Any]):
        super().__init__(str(name).upper(), dict(payload))


# ---------- Movement state helpers ----------

def _bb_get(bb: Any, key: str, default=None):
    try:
        return bb.get(key, default)
    except Exception:
        return default

def _bb_set(bb: Any, key: str, value: Any):
    try:
        bb.set(key, value)
    except Exception:
        pass


# ---------- Environment helpers (tolerant) ----------

def _env_bounds(env: Any) -> Optional[Tuple[int, int]]:
    w = getattr(env, "width", None)
    h = getattr(env, "height", None)
    if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
        return w, h
    return None


def _within_bounds(pos: Tuple[int, int], bounds: Optional[Tuple[int, int]]) -> bool:
    if not bounds:
        return True
    x, y = pos
    w, h = bounds
    return 0 <= x < w and 0 <= y < h


def _cell_free(env: Any, pos: Tuple[int, int]) -> bool:
    # Minimal collision check if env supports a grid with 'ant' occupancy
    try:
        if not hasattr(env, "grid"):
            return True
        x, y = pos
        cell = env.grid[y][x]
        # Consider walls if present
        if hasattr(cell, "cell_type") and getattr(cell, "cell_type") in ("w", "wall"):
            return False
        if hasattr(cell, "ant") and getattr(cell, "ant") is not None:
            return False
        return True
    except Exception:
        return True


def _move_occupy(env: Any, old_pos: Tuple[int, int], new_pos: Tuple[int, int], worker: Any) -> None:
    # Best-effort occupancy update if env has a grid with 'ant' field
    try:
        if hasattr(env, "grid"):
            env.grid[old_pos[1]][old_pos[0]].ant = None
            env.grid[new_pos[1]][new_pos[0]].ant = worker
    except Exception:
        pass


# ---------- Executor ----------

class IntentExecutor:
    """Executes intents and enforces single-move-per-tick per worker."""

    def __init__(self, allow_multiple_interactions: bool = True, enable_event_logging: bool = True):
        self.allow_multiple_interactions = allow_multiple_interactions
        self.enable_event_logging = enable_event_logging
        self._events = None
        if enable_event_logging and get_event_logger is not None:
            try:
                self._events = get_event_logger()
            except Exception:
                self._events = None

    def _derive_ids(self, worker: Any) -> Tuple[int, Union[int, str]]:
        """Best-effort extraction of tick and worker_id for structured logs."""
        bb = getattr(worker, "blackboard", None)
        tick = 0
        wid: Union[int, str] = getattr(worker, "id", "unknown")
        try:
            tick = int(_bb_get(bb, "cycle", 0))
        except Exception:
            tick = 0
        return tick, wid

    def _log_intent_event(self, tick: int, wid: Union[int, str], intent_type: str, status: str, details: Dict[str, Any]) -> None:
        if not (self.enable_event_logging and self._events and EventType):
            return
        try:
            self._events.log_intent_execution(tick, wid, intent_type, status, details)
        except Exception:
            # Never fail because of event logging
            pass

    def reset_worker_cycle(self, worker: Any) -> None:
        """Reset per-tick markers; called before sensors in a tick."""
        bb = getattr(worker, "blackboard", None)
        if bb:
            _bb_set(bb, "has_moved", False)
            _bb_set(bb, "intents_executed", [])
        # Legacy convenience flags if present
        if hasattr(worker, "has_moved_this_cycle"):
            worker.has_moved_this_cycle = False

    def apply_intents(self, worker: Any, env: Any, intents: List[Union[Intent, Dict[str, Any]]]) -> Dict[str, Any]:
        """Apply intents; returns execution summary for logging."""
        if not intents:
            return {"executed": [], "rejected": [], "reason": "no_intents"}

        bb = getattr(worker, "blackboard", None)
        pos_list = _bb_get(bb, "position", [0, 0])
        cur_pos = (int(pos_list[0]), int(pos_list[1])) if isinstance(pos_list, (list, tuple)) else (0, 0)
        bounds = _env_bounds(env)

        executed: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []

        # Structured IDs for events
        tick, wid = self._derive_ids(worker)

        # Normalize intents to Intent objects
        norm: List[Intent] = []
        for it in intents:
            if isinstance(it, Intent):
                norm.append(it)
            elif isinstance(it, dict):
                t = it.get("type")
                p = it.get("payload", {})
                norm.append(Intent(str(t).upper(), dict(p)))
            else:
                rej = {"intent": repr(it), "reason": "invalid_type"}
                rejected.append(rej)
                self._log_intent_event(tick, wid, "UNKNOWN", "rejected", rej)

        # Enforce single move
        moved = bool(_bb_get(bb, "has_moved", False))
        for it in norm:
            if it.type == "MOVE":
                if moved:
                    info = {"intent": it.to_dict(), "reason": "move_already_done"}
                    rejected.append(info)
                    self._log_intent_event(tick, wid, it.type, "rejected", info)
                    continue
                ok, new_pos, reason = self._apply_move(worker, env, cur_pos, it, bounds)
                if ok and new_pos:
                    _bb_set(bb, "position", [new_pos[0], new_pos[1]])
                    _bb_set(bb, "has_moved", True)
                    moved = True
                    self._flag_legacy_move(worker, True)
                    info = {"intent": it.to_dict(), "result": "applied", "new_pos": list(new_pos)}
                    executed.append(info)
                    self._log_intent_event(tick, wid, it.type, "executed", info)
                    cur_pos = new_pos
                else:
                    info = {"intent": it.to_dict(), "reason": reason or "move_invalid"}
                    rejected.append(info)
                    self._log_intent_event(tick, wid, it.type, "rejected", info)
                continue

            if it.type == "FEED":
                ok, details = self._apply_feed(worker, env, it)
                if ok:
                    info = {"intent": it.to_dict(), "result": "applied", **details}
                    executed.append(info)
                    self._log_intent_event(tick, wid, it.type, "executed", info)
                else:
                    info = {"intent": it.to_dict(), "reason": details.get("reason", "feed_failed")}
                    rejected.append(info)
                    self._log_intent_event(tick, wid, it.type, "rejected", info)
                continue

            if it.type == "PHEROMONE":
                ok, details = self._apply_pheromone(worker, env, it, cur_pos)
                if ok:
                    info = {"intent": it.to_dict(), "result": "applied", **details}
                    executed.append(info)
                    self._log_intent_event(tick, wid, it.type, "executed", info)
                else:
                    info = {"intent": it.to_dict(), "reason": details.get("reason", "pheromone_failed")}
                    rejected.append(info)
                    self._log_intent_event(tick, wid, it.type, "rejected", info)
                continue

            if it.type == "COLLECT_FOOD":
                ok, details = self._apply_collect_food(worker, env, it)
                if ok:
                    info = {"intent": it.to_dict(), "result": "applied", **details}
                    executed.append(info)
                    self._log_intent_event(tick, wid, it.type, "executed", info)
                else:
                    info = {"intent": it.to_dict(), "reason": details.get("reason", "collect_failed")}
                    rejected.append(info)
                    self._log_intent_event(tick, wid, it.type, "rejected", info)
                continue

            # Custom/unknown: treat as no-op (still log as executed-noop)
            info = {"intent": it.to_dict(), "result": "noop"}
            executed.append(info)
            self._log_intent_event(tick, wid, it.type, "executed", info)

        # Persist execution log on BB
        if bb:
            prev = _bb_get(bb, "intents_executed", [])
            _bb_set(bb, "intents_executed", list(prev) + executed)

        # Structured decision summary (textual)
        log.info(
            "executor_result worker=%s executed=%d rejected=%d details_executed=%s details_rejected=%s",
            getattr(worker, "id", "?"), len(executed), len(rejected), executed, rejected
        )
        return {"executed": executed, "rejected": rejected}

    # ---------- Apply handlers ----------

    def _apply_move(
        self,
        worker: Any,
        env: Any,
        cur_pos: Tuple[int, int],
        intent: Intent,
        bounds: Optional[Tuple[int, int]],
    ) -> Tuple[bool, Optional[Tuple[int, int]], Optional[str]]:
        target = intent.payload.get("target")
        delta = intent.payload.get("delta")
        if target is None and delta is None:
            return False, None, "no_target_or_delta"
        if target is not None and delta is not None:
            return False, None, "ambiguous_move"

        if target is not None:
            try:
                nx, ny = int(target[0]), int(target[1])
            except Exception:
                return False, None, "invalid_target"
        else:
            try:
                dx, dy = int(delta[0]), int(delta[1])
            except Exception:
                return False, None, "invalid_delta"
            nx, ny = cur_pos[0] + dx, cur_pos[1] + dy

        new_pos = (nx, ny)
        if not _within_bounds(new_pos, bounds):
            return False, None, "out_of_bounds"

        # Enforce one-cell step (8-neighborhood) for now
        if max(abs(new_pos[0] - cur_pos[0]), abs(new_pos[1] - cur_pos[1])) > 1:
            return False, None, "too_far"

        if not _cell_free(env, new_pos):
            return False, None, "blocked"

        _move_occupy(env, cur_pos, new_pos, worker)
        log.info(
            "intent_applied type=MOVE worker=%s from=%s to=%s reason=validated",
            getattr(worker, "id", "?"), cur_pos, new_pos
        )
        return True, new_pos, None

    def _apply_feed(self, worker: Any, env: Any, intent: Intent) -> Tuple[bool, Dict[str, Any]]:
        tgt = intent.payload.get("target_id")
        amount = intent.payload.get("amount")
        if tgt is None:
            return False, {"reason": "missing_target"}

        # Environment API tolerant lookup
        target = None
        if hasattr(env, "get_ant_by_id"):
            try:
                target = env.get_ant_by_id(int(tgt))
            except Exception:
                target = None

        if target is None:
            return False, {"reason": "target_not_found"}

        # Pull values from BB if present
        bb = getattr(worker, "blackboard", None)
        social = _bb_get(bb, "social_stomach")
        social_cap = _bb_get(bb, "social_stomach_capacity")
        if social is None:
            social = getattr(worker, "current_social_stomach", 0)
            social_cap = getattr(worker, "social_stomach_capacity", 0)

        if social <= 0:
            return False, {"reason": "no_social_food"}

        # Compute transferable amount
        t_stom = getattr(target, "stomach_capacity", 0)
        t_cur = getattr(target, "current_stomach", 0)
        free = max(0, t_stom - t_cur)
        if free <= 0:
            return False, {"reason": "target_full"}

        transfer = min(int(social), int(free))
        if amount is not None:
            transfer = min(transfer, max(0, int(amount)))

        # Apply as best-effort (no BB on target in legacy env)
        try:
            setattr(target, "current_stomach", t_cur + transfer)
        except Exception:
            pass
        if bb is not None:
            _bb_set(bb, "social_stomach", int(social) - transfer)
        else:
            try:
                worker.current_social_stomach = int(social) - transfer
            except Exception:
                pass

        log.info(
            "intent_applied type=FEED worker=%s target=%s amount=%s",
            getattr(worker, "id", "?"), getattr(target, "id", tgt), transfer
        )
        return True, {"transferred": transfer, "target_id": getattr(target, "id", tgt)}

    def _apply_pheromone(self, worker: Any, env: Any, intent: Intent, cur_pos: Tuple[int, int]) -> Tuple[bool, Dict[str, Any]]:
        p = intent.payload
        ptype = p.get("ptype")
        strength = int(p.get("strength", 1))
        pos = p.get("position")
        if pos is None:
            tx, ty = cur_pos
        else:
            try:
                tx, ty = int(pos[0]), int(pos[1])
            except Exception:
                return False, {"reason": "invalid_position"}

        # Best-effort application (supports env.grid[y][x].pheromones or cell add_pheromone)
        try:
            cell = env.grid[ty][tx]
            if hasattr(cell, "add_pheromone"):
                cell.add_pheromone(ptype, strength)
            else:
                if not hasattr(cell, "pheromones"):
                    cell.pheromones = {}
                cell.pheromones[ptype] = cell.pheromones.get(ptype, 0) + strength
            log.info(
                "intent_applied type=PHEROMONE worker=%s pos=(%s,%s) ptype=%s strength=%s",
                getattr(worker, "id", "?"), tx, ty, ptype, strength
            )
            return True, {"ptype": ptype, "position": [tx, ty], "strength": strength}
        except Exception:
            return False, {"reason": "env_cell_unavailable"}

    def _apply_collect_food(self, worker: Any, env: Any, intent: Intent) -> Tuple[bool, Dict[str, Any]]:
        """
        Apply collection of food from environment cell into worker's social stomach.
        Tolerant to minimal environments:
          - Requires env.grid[y][x].food with 'amount' attribute for actual collection.
          - If missing, rejects with reason.
        Updates BB key 'social_stomach' respecting 'social_stomach_capacity'.
        """
        payload = intent.payload or {}
        # Determine source position: explicit food_position or worker's current position
        bb = getattr(worker, "blackboard", None)
        pos_from_bb = _bb_get(bb, "position", [0, 0])
        try:
            cur_x, cur_y = (int(pos_from_bb[0]), int(pos_from_bb[1])) if isinstance(pos_from_bb, (list, tuple)) else (0, 0)
        except Exception:
            cur_x, cur_y = 0, 0
        src = payload.get("food_position") or payload.get("position") or [cur_x, cur_y]
        try:
            sx, sy = int(src[0]), int(src[1])
        except Exception:
            return False, {"reason": "invalid_source_position"}

        # Amount requested (default 10 as in domain step)
        try:
            requested = int(payload.get("amount", 10))
        except Exception:
            requested = 10
        if requested <= 0:
            return False, {"reason": "non_positive_amount"}

        # Read stomach values from BB or fallback attrs
        social = _bb_get(bb, "social_stomach")
        cap = _bb_get(bb, "social_stomach_capacity")
        if social is None:
            social = getattr(worker, "current_social_stomach", 0)
        if cap is None:
            cap = getattr(worker, "social_stomach_capacity", 0)

        free_capacity = max(0, int(cap) - int(social))
        if free_capacity <= 0:
            return False, {"reason": "no_capacity", "current_social": int(social), "capacity": int(cap)}

        # Access environment cell and food object
        try:
            cell = env.grid[sy][sx]
        except Exception:
            return False, {"reason": "env_cell_unavailable"}

        food_obj = getattr(cell, "food", None)
        available = getattr(food_obj, "amount", 0) if food_obj is not None else 0
        if not isinstance(available, (int, float)) or available <= 0:
            return False, {"reason": "no_food", "position": [sx, sy]}

        # Compute collection amount
        collect_amt = int(min(requested, free_capacity, int(available)))
        if collect_amt <= 0:
            return False, {"reason": "nothing_to_collect", "requested": requested, "free_capacity": free_capacity, "available": int(available)}

        # Apply mutations: reduce source, increase social stomach
        try:
            # Reduce source
            food_obj.amount = int(available) - collect_amt
            if getattr(food_obj, "amount", 0) <= 0:
                # Optional: set empty source to None for simple envs
                try:
                    cell.food = None
                except Exception:
                    pass
        except Exception:
            return False, {"reason": "source_update_failed"}

        # Update BB/worker social stomach
        new_social = int(social) + collect_amt
        if bb is not None:
            _bb_set(bb, "social_stomach", new_social)
        else:
            try:
                worker.current_social_stomach = new_social
            except Exception:
                pass

        log.info(
            "intent_applied type=COLLECT_FOOD worker=%s src=%s amount=%s social_stomach=%s/%s",
            getattr(worker, "id", "?"), [sx, sy], collect_amt, new_social, int(cap)
        )
        return True, {"collected": collect_amt, "source": [sx, sy], "social_stomach": new_social, "capacity": int(cap)}

    # ---------- Legacy compatibility flags ----------

    def _flag_legacy_move(self, worker: Any, moved: bool) -> None:
        """Mirror move status for legacy attrs if present."""
        try:
            if hasattr(worker, "has_moved_this_cycle"):
                worker.has_moved_this_cycle = bool(moved)
        except Exception:
            pass

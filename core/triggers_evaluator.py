# FILE: antsim/core/triggers_evaluator.py
# antsim/core/triggers_evaluator.py
"""Evaluator for trigger plugins with AND/OR logic and structured logging."""
import logging
from typing import Any, Dict, List, Optional, Tuple, Callable

from ..registry.manager import PluginManager
from ..io.event_logger import get_event_logger, EventType

logger = logging.getLogger(__name__)


class TriggersEvaluator:
    """Resolves and evaluates triggers via PluginManager with unified structured logging."""
    def __init__(self, plugin_manager: PluginManager):
        self.pm = plugin_manager
        self._triggers: Dict[str, Callable] = {}
        self._events = get_event_logger()
        self._load()

    def _load(self) -> None:
        self._triggers.clear()
        for name in self.pm.list_triggers():
            func = self.pm.get_trigger(name)
            if func:
                self._triggers[name] = func
        logger.info("TriggersEvaluator loaded %d triggers", len(self._triggers))

    def list_triggers(self) -> List[str]:
        return sorted(self._triggers.keys())

    @staticmethod
    def _derive_ids(blackboard: Any) -> Tuple[int, Any]:
        """Best-effort extraction of tick and worker_id from a Blackboard-like object."""
        tick = 0
        wid: Any = "unknown"
        try:
            # antsim.core.blackboard.Blackboard API
            tick = int(blackboard.get("cycle", 0))
            wid = blackboard.get("agent_id", "unknown")
        except Exception:
            pass
        return tick, wid

    def evaluate(self, name: str, blackboard: Any, **kwargs) -> bool:
        """Evaluate a single trigger; emits structured event."""
        func = self._triggers.get(name)
        tick, wid = self._derive_ids(blackboard)
        if not func:
            logger.error("trigger=%s status=missing", name)
            # structured event for missing trigger
            self._events.log_event(
                EventType.TRIGGER_EVAL,
                tick,
                wid,
                {"trigger": name, "result": False, "reason": "missing", "kwargs": kwargs or {}},
                tags=[f"trigger:{name}", "missing"],
            )
            return False
        try:
            # Prefer signature (bb, **kwargs); be tolerant for (bb) only
            result = func(blackboard, **kwargs) if kwargs else func(blackboard)
            result = bool(result)
            logger.debug("trigger=%s result=%s kwargs=%s", name, result, kwargs or {})
            # structured event
            self._events.log_event(
                EventType.TRIGGER_EVAL,
                tick,
                wid,
                {"trigger": name, "result": result, "kwargs": kwargs or {}},
                tags=[f"trigger:{name}", f"result:{result}"],
            )
            return result
        except TypeError:
            # Fallback: call without kwargs
            result = bool(func(blackboard))
            logger.debug("trigger=%s result=%s kwargs=%s", name, result, {})
            self._events.log_event(
                EventType.TRIGGER_EVAL,
                tick,
                wid,
                {"trigger": name, "result": result, "kwargs": {}},
                tags=[f"trigger:{name}", f"result:{result}"],
            )
            return result
        except Exception as e:
            logger.error("trigger=%s error=%s", name, e, exc_info=True)
            self._events.log_event(
                EventType.TRIGGER_EVAL,
                tick,
                wid,
                {"trigger": name, "result": False, "error": str(e)},
                tags=[f"trigger:{name}", "error"],
            )
            return False

    def evaluate_many(self, names: List[str], blackboard: Any, logic: str = "AND") -> Tuple[bool, Dict[str, bool]]:
        """Evaluate multiple triggers with AND/OR logic; returns (final, details) and logs a summary event."""
        details: Dict[str, bool] = {}
        tick, wid = self._derive_ids(blackboard)
        if not names:
            logger.debug("triggers=empty default=true logic=%s", logic)
            # summary event for empty set
            self._events.log_event(
                EventType.TRIGGER_EVAL,
                tick,
                wid,
                {"triggers": [], "logic": logic.upper(), "final": True, "details": {}},
                tags=["gate", "empty"],
            )
            return True, details

        for n in names:
            res = self.evaluate(n, blackboard)
            details[n] = res

        if logic.upper() == "OR":
            final = any(details.values())
        else:
            final = all(details.values())

        active = [k for k, v in details.items() if v]
        inactive = [k for k, v in details.items() if not v]
        logger.info(
            "triggers_evaluated count=%d logic=%s final=%s active=%s inactive=%s",
            len(details),
            logic.upper(),
            final,
            active,
            inactive,
        )
        # structured summary event
        self._events.log_event(
            EventType.TRIGGER_EVAL,
            tick,
            wid,
            {
                "triggers": list(names),
                "logic": logic.upper(),
                "final": final,
                "details": details,
                "active": active,
                "inactive": inactive,
            },
            tags=["gate", f"logic:{logic.upper()}", f"final:{final}"],
        )
        return final, details

    def evaluate_task_gate(self, task_name: str, trigger_names: List[str], blackboard: Any, logic: str = "AND") -> bool:
        """Evaluate a 'gate' for a task; logs decision context (structured and textual)."""
        final, details = self.evaluate_many(trigger_names, blackboard, logic)
        logger.info(
            "task_gate task=%s decision=%s logic=%s reasons=%s",
            task_name, final, logic.upper(), details
        )
        # also emit structured event tagged with task
        tick, wid = self._derive_ids(blackboard)
        self._events.log_event(
            EventType.TRIGGER_EVAL,
            tick,
            wid,
            {"task": task_name, "triggers": trigger_names, "logic": logic.upper(), "final": final, "details": details},
            tags=[f"task:{task_name}", "gate", f"final:{final}"],
        )
        return final

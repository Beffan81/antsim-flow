# FILE: antsim/behavior/bt.py
# FILE: antsim/behavior/bt.py
"""Minimal Behavior Tree (BT) with builder and engine.

Provides:
- Status enum and Node base
- Sequence, Selector, Condition, StepLeaf
- TreeBuilder from simple dict config
- BehaviorEngine: pre-sensors -> bt.tick (Intents) -> apply_intents -> post-sensors

Logging focuses on decisions: trigger evaluations, selected branches, step results,
and intents/executor outcomes. This version also logs structured blackboard diffs
(pre- and post-sensors) and BT transitions via the central EventLogger, including
a simple tick performance breakdown.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable

from ..registry.manager import PluginManager
from ..core.sensors_runner import SensorsRunner
from ..core.triggers_evaluator import TriggersEvaluator
from ..core.executor import IntentExecutor
from ..io.event_logger import get_event_logger

log = logging.getLogger(__name__)


# ---------- Status and context ----------

class Status:
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


@dataclass
class TickContext:
    """Execution context for BT ticking."""
    worker: Any
    environment: Any
    pm: PluginManager
    sensors: SensorsRunner
    triggers: TriggersEvaluator
    node_path: List[str]
    tick_id: int = 0
    intents: List[Any] = field(default_factory=list)  # collected intents from leaves
    events: Any = None  # EventLogger instance (optional)


# ---------- BT Nodes ----------

class Node:
    """Abstract BT node."""
    def __init__(self, name: str):
        self.name = name

    def tick(self, ctx: TickContext) -> str:
        raise NotImplementedError


class Sequence(Node):
    """Runs children in order; fails on first failure; running on first running."""
    def __init__(self, name: str, children: List[Node]):
        super().__init__(name)
        self.children = children

    def tick(self, ctx: TickContext) -> str:
        wid = getattr(ctx.worker, "id", "?")
        # Structured enter
        if ctx.events:
            ctx.events.log_bt_transition(ctx.tick_id, wid, self.name, "sequence", "enter")
        t0 = time.perf_counter()

        log.debug("bt_node sequence enter name=%s", self.name)
        for i, child in enumerate(self.children):
            ctx.node_path.append(f"{self.name}[{i}]")
            res = child.tick(ctx)
            ctx.node_path.pop()
            log.debug("bt_node sequence child_result name=%s idx=%d result=%s", self.name, i, res)
            if res != Status.SUCCESS:
                # Structured exit with child result
                if ctx.events:
                    ctx.events.log_bt_transition(
                        ctx.tick_id, wid, self.name, "sequence", "exit",
                        status=res, duration_ms=(time.perf_counter() - t0) * 1000.0
                    )
                return res
        # All children succeeded
        if ctx.events:
            ctx.events.log_bt_transition(
                ctx.tick_id, wid, self.name, "sequence", "exit",
                status=Status.SUCCESS, duration_ms=(time.perf_counter() - t0) * 1000.0
            )
        return Status.SUCCESS


class Selector(Node):
    """Runs children in order; succeeds on first success; running on first running."""
    def __init__(self, name: str, children: List[Node]):
        super().__init__(name)
        self.children = children

    def tick(self, ctx: TickContext) -> str:
        wid = getattr(ctx.worker, "id", "?")
        # Structured enter
        if ctx.events:
            ctx.events.log_bt_transition(ctx.tick_id, wid, self.name, "selector", "enter")
        t0 = time.perf_counter()

        log.debug("bt_node selector enter name=%s", self.name)
        for i, child in enumerate(self.children):
            ctx.node_path.append(f"{self.name}[{i}]")
            res = child.tick(ctx)
            ctx.node_path.pop()
            log.debug("bt_node selector child_result name=%s idx=%d result=%s", self.name, i, res)
            if res != Status.FAILURE:
                # Structured exit with first non-failure result
                if ctx.events:
                    ctx.events.log_bt_transition(
                        ctx.tick_id, wid, self.name, "selector", "exit",
                        status=res, duration_ms=(time.perf_counter() - t0) * 1000.0
                    )
                return res
        # All failed
        if ctx.events:
            ctx.events.log_bt_transition(
                ctx.tick_id, wid, self.name, "selector", "exit",
                status=Status.FAILURE, duration_ms=(time.perf_counter() - t0) * 1000.0
            )
        return Status.FAILURE


class Condition(Node):
    """Evaluates triggers via TriggersEvaluator; returns SUCCESS if gate passes.

    Extended: supports optional per-trigger params (trigger_params: Dict[str, Dict[str, Any]])
    passed from configuration. This enables declarative parameterization (Step 7).
    """
    def __init__(self, name: str, trigger_names: List[str], logic: str = "AND",
                 trigger_params: Optional[Dict[str, Dict[str, Any]]] = None):
        super().__init__(name)
        self.trigger_names = trigger_names
        self.logic = (logic or "AND").upper()
        self.trigger_params = trigger_params or {}

    def tick(self, ctx: TickContext) -> str:
        bb = getattr(ctx.worker, "blackboard", None)
        wid = getattr(ctx.worker, "id", "?")
        # Structured enter
        if ctx.events:
            ctx.events.log_bt_transition(ctx.tick_id, wid, self.name, "condition", "enter")
        t0 = time.perf_counter()

        # Evaluate each trigger individually to pass parameters (minimal invasive)
        results: Dict[str, bool] = {}
        active: List[str] = []
        inactive: List[str] = []
        for n in self.trigger_names:
            params = self.trigger_params.get(n, {}) if isinstance(self.trigger_params, dict) else {}
            try:
                res = ctx.triggers.evaluate(n, bb, **params) if params else ctx.triggers.evaluate(n, bb)
            except Exception:
                res = False
            results[n] = bool(res)
            if results[n]:
                active.append(n)
            else:
                inactive.append(n)

        if self.logic == "OR":
            final = any(results.values()) if results else True
        else:
            final = all(results.values()) if results else True

        dt_ms = (time.perf_counter() - t0) * 1000.0
        log.info(
            "bt_condition name=%s logic=%s result=%s reasons=%s",
            self.name, self.logic, final, results
        )
        # Structured exit
        if ctx.events:
            ctx.events.log_bt_transition(ctx.tick_id, wid, self.name, "condition", "exit",
                                         status=str(final), duration_ms=dt_ms)
        return Status.SUCCESS if final else Status.FAILURE


class StepLeaf(Node):
    """Calls a step plugin by name; maps return values to Status and collects intents."""
    def __init__(self, name: str, step_name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name)
        self.step_name = step_name
        self.params = params or {}
        self._func: Optional[Callable] = None

    def _resolve(self, ctx: TickContext) -> Optional[Callable]:
        if self._func is None:
            self._func = ctx.pm.get_step(self.step_name)
            if not self._func:
                log.error("bt_step missing step=%s node=%s", self.step_name, self.name)
        return self._func

    @staticmethod
    def _map_status_and_intents(result: Any) -> Tuple[str, List[Any]]:
        """
        Map various step results to (Status, intents-list).

        Accepted forms:
        - {"status": "...", "intents": [...]}  -> honors status; collects intents
        - {"status": "..."}                     -> honors status; no intents
        - list/tuple of intents                 -> default status RUNNING
        - single intent (dict/Intent-like)     -> default status RUNNING
        - True/False/None                      -> SUCCESS/FAILURE/FAILURE
        - string "IN_PROGRESS"/"RUN"           -> RUNNING
        """
        intents_out: List[Any] = []

        # Dict form with optional intents
        if isinstance(result, dict) and "status" in result:
            status_val = result.get("status")
            intents = result.get("intents", None)
            if intents is not None:
                if isinstance(intents, (list, tuple)):
                    intents_out = list(intents)
                else:
                    intents_out = [intents]
            # Map declared status string/bool
            if isinstance(status_val, str):
                s = status_val.upper()
                if s in (Status.SUCCESS, Status.FAILURE, Status.RUNNING):
                    return s, intents_out
                if s in ("IN_PROGRESS", "RUN"):
                    return Status.RUNNING, intents_out
            if status_val is True:
                return Status.SUCCESS, intents_out
            if status_val is False or status_val is None:
                return Status.FAILURE, intents_out
            # Fallback
            return Status.FAILURE, intents_out

        # Pure intents: list/tuple
        if isinstance(result, (list, tuple)):
            return Status.RUNNING, list(result)

        # Single intent-like: dataclass or dict with 'type'
        if hasattr(result, "__dict__") and hasattr(getattr(result, "__class__", object), "__name__"):
            # likely a dataclass intent; accept as single intent
            return Status.RUNNING, [result]
        if isinstance(result, dict) and "type" in result:
            return Status.RUNNING, [result]

        # Status-only strings
        if isinstance(result, str):
            s = result.upper()
            if s in (Status.SUCCESS, Status.FAILURE, Status.RUNNING):
                return s, intents_out
            if s in ("IN_PROGRESS", "RUN"):
                return Status.RUNNING, intents_out

        # Booleans / None
        if result is True:
            return Status.SUCCESS, intents_out
        if result is False or result is None:
            return Status.FAILURE, intents_out

        # Unknown shape -> conservative failure
        return Status.FAILURE, intents_out

    def tick(self, ctx: TickContext) -> str:
        func = self._resolve(ctx)
        if not func:
            return Status.FAILURE

        wid = getattr(ctx.worker, "id", "?")
        # Structured enter
        if ctx.events:
            ctx.events.log_bt_transition(ctx.tick_id, wid, self.name, "step", "enter")
        t0 = time.perf_counter()

        try:
            res = func(ctx.worker, ctx.environment, **self.params)
            status, intents = self._map_status_and_intents(res)

            if intents:
                ctx.intents.extend(intents)
                log.debug("bt_step_intents name=%s collected_count=%d", self.name, len(intents))

            log.info(
                "bt_step name=%s step=%s status=%s intents_present=%s params=%s",
                self.name, self.step_name, status, bool(intents), self.params
            )
            # Structured exit
            if ctx.events:
                ctx.events.log_bt_transition(
                    ctx.tick_id, wid, self.name, "step", "exit",
                    status=status, duration_ms=(time.perf_counter() - t0) * 1000.0
                )
            return status
        except Exception as e:
            log.error("bt_step error name=%s step=%s err=%s", self.name, self.step_name, e, exc_info=True)
            if ctx.events:
                ctx.events.log_bt_transition(
                    ctx.tick_id, wid, self.name, "step", "exit",
                    status="FAILURE", duration_ms=(time.perf_counter() - t0) * 1000.0
                )
            return Status.FAILURE


# ---------- Tree Builder ----------

class TreeBuilder:
    """Builds a BT from a dict definition using the PluginManager and TriggersEvaluator."""
    def __init__(self, plugin_manager: PluginManager, triggers: Optional[TriggersEvaluator] = None):
        self.pm = plugin_manager
        self.triggers = triggers  # not required here; evaluation happens via ctx

    def build(self, spec: Dict[str, Any]) -> Node:
        """Builds Node recursively from spec."""
        ntype = spec.get("type", "").lower()
        name = spec.get("name", ntype)
        if ntype in ("sequence", "seq"):
            children = [self.build(c) for c in spec.get("children", [])]
            return Sequence(name, children)
        if ntype in ("selector", "sel"):
            children = [self.build(c) for c in spec.get("children", [])]
            return Selector(name, children)
        if ntype in ("condition", "cond"):
            triggers = spec.get("triggers", [])
            logic = spec.get("logic", "AND")
            # NEW: optional per-trigger params map passed through to node
            trigger_params = spec.get("trigger_params", {}) or {}
            return Condition(name, triggers, logic, trigger_params=trigger_params)
        if ntype in ("step", "leaf"):
            step_name = spec.get("step") or spec.get("name") or spec.get("step_name")
            params = spec.get("params", {})
            if not step_name:
                raise ValueError(f"Step node '{name}' missing 'step' field")
            return StepLeaf(name, step_name, params)
        raise ValueError(f"Unknown node type: {ntype}")


# ---------- Behavior Engine ----------

class BehaviorEngine:
    """Runs a BT per agent with sensors pre/post phases and centralized intent execution.
    
    Supports different behavior trees for different agent types (Queen vs Worker).
    """
    def __init__(self, plugin_manager: PluginManager, worker_tree_root: Node, queen_tree_root: Node = None):
        self.pm = plugin_manager
        self.sensors = SensorsRunner(plugin_manager)
        self.triggers = TriggersEvaluator(plugin_manager)
        self.executor = IntentExecutor()
        self.worker_root = worker_tree_root
        self.queen_root = queen_tree_root or worker_tree_root  # Fallback to worker tree if no queen tree
        self._ticks = 0
        self._events = get_event_logger()

    @staticmethod
    def _format_bb_changes(changes: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Render BB diff into a compact, serializable list for logs."""
        out: List[Dict[str, Any]] = []
        for k, v in (changes or {}).items():
            if isinstance(v, dict):
                out.append({"key": k, "old": v.get("old"), "new": v.get("new")})
            else:
                out.append({"key": k, "value": v})
        return out

    def _is_queen(self, agent: Any) -> bool:
        """Check if agent is a queen based on class name or attributes."""
        return (getattr(agent, "__class__", type(agent)).__name__ == "Queen" or 
                hasattr(agent, "egg_laying_interval"))
    
    def _get_agent_tree(self, agent: Any) -> Node:
        """Get appropriate behavior tree for agent type."""
        return self.queen_root if self._is_queen(agent) else self.worker_root

    def tick_agent(self, agent: Any, environment: Any) -> str:
        """Tick any agent (queen or worker) with appropriate behavior tree.
        
        This is the new universal method that replaces tick_worker.
        """
        tree_root = self._get_agent_tree(agent)
        agent_type = "Queen" if self._is_queen(agent) else "Worker"
        
        return self._tick_with_tree(agent, environment, tree_root, agent_type)
    
    def tick_worker(self, worker: Any, environment: Any) -> str:
        """Legacy method for backward compatibility - delegates to tick_agent."""
        return self.tick_agent(worker, environment)

    def _tick_with_tree(self, agent: Any, environment: Any, tree_root: Node, agent_type: str = "Agent") -> str:
        """reset movement -> pre-sensors -> bt.tick (collect intents) -> apply_intents -> post-sensors"""
        self._ticks += 1
        tick_id = self._ticks
        agent_id = getattr(agent, "id", "?")
        log.info("bt_tick start %s=%s tick=%d", agent_type.lower(), agent_id, tick_id)

        t_total = time.perf_counter()

        # Reset per-tick movement and intent log on BB
        self.executor.reset_worker_cycle(agent)
        log.debug("bt_tick agent_reset %s=%s tick=%d", agent_type.lower(), agent_id, tick_id)

        # Pre sensors: populate BB facts (idempotent per tick)
        t_pre = time.perf_counter()
        pre_changes = self.sensors.update_worker(agent, environment)
        pre_ms = (time.perf_counter() - t_pre)
        if pre_changes:
            log.info("bt_tick pre_sensors_changes %s=%s tick=%d keys=%s", agent_type.lower(), agent_id, tick_id, list(pre_changes.keys()))
            if log.isEnabledFor(logging.DEBUG):
                log.debug(
                    "bt_tick pre_sensors_diff %s=%s tick=%d diff=%s",
                    agent_type.lower(), agent_id, tick_id, self._format_bb_changes(pre_changes)
                )
            # Structured event
            self._events.log_bb_diff(tick_id, agent_id, pre_changes, phase="pre_sensors")
        else:
            log.debug("bt_tick pre_sensors_no_changes %s=%s tick=%d", agent_type.lower(), agent_id, tick_id)

        # Build tick context (pass EventLogger)
        ctx = TickContext(
            worker=agent,
            environment=environment,
            pm=self.pm,
            sensors=self.sensors,
            triggers=self.triggers,
            node_path=[],
            tick_id=tick_id,
            events=self._events,
        )

        # Run BT
        t_bt = time.perf_counter()
        result = tree_root.tick(ctx)
        bt_ms = (time.perf_counter() - t_bt)

        # Apply intents via executor before post-sensors
        executed_cnt = rejected_cnt = 0
        t_exec = time.perf_counter()
        if ctx.intents:
            log.info("bt_tick intents_collected %s=%s tick=%d count=%d", agent_type.lower(), agent_id, tick_id, len(ctx.intents))
            exec_summary = self.executor.apply_intents(agent, environment, ctx.intents)
            executed = exec_summary.get("executed", [])
            rejected = exec_summary.get("rejected", [])
            executed_cnt = len(executed)
            rejected_cnt = len(rejected)
            log.info("bt_tick intents_applied %s=%s tick=%d executed=%d rejected=%d",
                     agent_type.lower(), agent_id, tick_id, executed_cnt, rejected_cnt)
            # Structured logging per intent
            for e in executed:
                intent = e.get("intent", {})
                self._events.log_intent_execution(tick_id, agent_id, intent.get("type", "UNKNOWN"), "executed", e)
            for r in rejected:
                intent = r.get("intent", {})
                self._events.log_intent_execution(tick_id, agent_id, intent.get("type", "UNKNOWN"), "rejected", r)
            if rejected_cnt and log.isEnabledFor(logging.DEBUG):
                log.debug("bt_tick intents_rejected_details %s=%s tick=%d details=%s",
                          agent_type.lower(), agent_id, tick_id, rejected)
        else:
            log.debug("bt_tick no_intents %s=%s tick=%d", agent_type.lower(), agent_id, tick_id)
        exec_ms = (time.perf_counter() - t_exec)

        # Post sensors: allow reading results after executor mutations
        t_post = time.perf_counter()
        post_changes = self.sensors.update_worker(agent, environment)
        post_ms = (time.perf_counter() - t_post)
        if post_changes:
            log.info("bt_tick post_sensors_changes %s=%s tick=%d keys=%s", agent_type.lower(), agent_id, tick_id, list(post_changes.keys()))
            if log.isEnabledFor(logging.DEBUG):
                log.debug(
                    "bt_tick post_sensors_diff %s=%s tick=%d diff=%s",
                    agent_type.lower(), agent_id, tick_id, self._format_bb_changes(post_changes)
                )
            self._events.log_bb_diff(tick_id, agent_id, post_changes, phase="post_sensors")
        else:
            log.debug("bt_tick post_sensors_no_changes %s=%s tick=%d", agent_type.lower(), agent_id, tick_id)

        # Optional concise snapshot of key facts
        if log.isEnabledFor(logging.DEBUG):
            bb = agent.blackboard
            snapshot_keys = [
                "position", "in_nest", "at_entry",
                "individual_stomach", "individual_hungry",
                "social_stomach", "social_hungry",
                "food_detected", "food_position", "has_moved"
            ]
            # Add queen-specific keys if it's a queen
            if agent_type == "Queen":
                snapshot_keys.extend(["signaling_hunger", "eggs_laid", "last_egg_tick"])                
            
            snapshot = {k: bb.get(k) for k in snapshot_keys}
            log.debug("bt_tick bb_snapshot %s=%s tick=%d snapshot=%s", agent_type.lower(), agent_id, tick_id, snapshot)

        total_ms = (time.perf_counter() - t_total)
        # Structured performance summary
        self._events.log_performance_tick(
            tick_id,
            {
                "pre_sensors": pre_ms,
                "bt": bt_ms,
                "executor": exec_ms,
                "post_sensors": post_ms,
            },
            total_ms
        )

        # NEW: ensure timely delivery of structured events per tick
        try:
            # EventLogger is designed to be cheap on flush; guard errors to avoid side-effects
            self._events.flush()
        except Exception:
            pass

        log.info("bt_tick end %s=%s tick=%d result=%s path=%s",
                 agent_type.lower(), agent_id, tick_id, result, " > ".join(ctx.node_path))
        return result


# ---------- Example minimal tree spec helper ----------

def example_tree_spec() -> Dict[str, Any]:
    """Simple BT example: if social_hungry AND not_in_nest -> example_move, else example_wait."""
    return {
        "type": "selector",
        "name": "Root",
        "children": [
            {
                "type": "sequence",
                "name": "CollectOutside",
                "children": [
                    {"type": "condition", "name": "GateCollect", "triggers": ["social_hungry", "not_in_nest"], "logic": "AND"},
                    {"type": "step", "name": "example_move", "step": "example_move", "params": {}},
                ],
            },
            {"type": "step", "name": "Idle", "step": "example_wait", "params": {}},
        ],
    }

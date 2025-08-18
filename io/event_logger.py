# FILE: antsim/io/event_logger.py
"""
Structured event logging for antsim with aggregation and performance tracking.

Goals:
- Unified event collection for BT transitions, BB diffs, intent execution
- Structured output (JSON-lines compatible) with event types and metadata
- Performance metrics tracking (tick times, phase durations)
- Configurable verbosity levels per event category
- Thread-safe for future multi-agent scenarios

Event Types:
- bt_transition: Node enter/exit with path, status, duration
- bb_diff: Blackboard changes with before/after values
- intent_execution: Intent apply/reject with reasons
- sensor_update: Sensor runs with changed keys
- trigger_eval: Trigger evaluation results
- performance: Tick timing and phase breakdowns
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Union


log = logging.getLogger(__name__)


class EventType(str, Enum):
    """Categorized event types for filtering and analysis."""
    BT_TRANSITION = "bt_transition"
    BB_DIFF = "bb_diff"
    INTENT_EXECUTION = "intent_execution"
    SENSOR_UPDATE = "sensor_update"
    TRIGGER_EVAL = "trigger_eval"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


@dataclass
class Event:
    """Structured event with metadata."""
    type: EventType
    timestamp: float
    tick: int
    worker_id: Union[int, str]
    data: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "tick": self.tick,
            "worker_id": self.worker_id,
            "data": self.data,
            "tags": self.tags
        }


class PerformanceTracker:
    """Track timing for different phases of execution."""
    
    def __init__(self):
        self.timers: Dict[str, float] = {}
        self.durations: Dict[str, List[float]] = defaultdict(list)
        
    def start(self, name: str) -> None:
        """Start timing a phase."""
        self.timers[name] = time.perf_counter()
        
    def end(self, name: str) -> float:
        """End timing and record duration."""
        if name not in self.timers:
            return 0.0
        duration = time.perf_counter() - self.timers.pop(name)
        self.durations[name].append(duration)
        return duration
        
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get timing statistics per phase."""
        stats = {}
        for name, durations in self.durations.items():
            if durations:
                stats[name] = {
                    "count": len(durations),
                    "total": sum(durations),
                    "mean": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "last": durations[-1]
                }
        return stats
        
    def reset(self) -> None:
        """Reset all timers and statistics."""
        self.timers.clear()
        self.durations.clear()


class EventLogger:
    """Central event logger with filtering and output control."""
    
    def __init__(self, 
                 buffer_size: int = 10000,
                 auto_flush_interval: int = 100,
                 enabled_types: Optional[List[EventType]] = None):
        """
        Initialize event logger.
        
        Args:
            buffer_size: Maximum events to buffer before auto-flush
            auto_flush_interval: Flush every N events
            enabled_types: Event types to log (None = all)
        """
        self.buffer: List[Event] = []
        self.buffer_size = buffer_size
        self.auto_flush_interval = auto_flush_interval
        self.enabled_types = set(enabled_types) if enabled_types else set(EventType)
        
        self.event_counts: Dict[EventType, int] = defaultdict(int)
        self.performance = PerformanceTracker()
        self._lock = Lock()
        self._event_counter = 0
        
        # Output handlers
        self._handlers: List[callable] = []
        self._add_default_handler()
        
    def _add_default_handler(self) -> None:
        """Add default JSON-lines logger handler."""
        def json_handler(events: List[Event]) -> None:
            for event in events:
                if log.isEnabledFor(logging.INFO):
                    log.info("event: %s", json.dumps(event.to_dict(), ensure_ascii=False))
        self._handlers.append(json_handler)
        
    def add_handler(self, handler: callable) -> None:
        """Add custom event handler."""
        self._handlers.append(handler)
        
    def is_enabled(self, event_type: EventType) -> bool:
        """Check if event type is enabled for logging."""
        return event_type in self.enabled_types
        
    def log_event(self, event_type: EventType, tick: int, worker_id: Union[int, str],
                  data: Dict[str, Any], tags: Optional[List[str]] = None) -> None:
        """Log a structured event."""
        if not self.is_enabled(event_type):
            return
            
        with self._lock:
            event = Event(
                type=event_type,
                timestamp=time.time(),
                tick=tick,
                worker_id=worker_id,
                data=data,
                tags=tags or []
            )
            
            self.buffer.append(event)
            self.event_counts[event_type] += 1
            self._event_counter += 1
            
            # Auto-flush logic
            if (self._event_counter % self.auto_flush_interval == 0 or 
                len(self.buffer) >= self.buffer_size):
                self._flush_locked()
                
    def log_bt_transition(self, tick: int, worker_id: Union[int, str], 
                         node_name: str, node_type: str, action: str,
                         status: Optional[str] = None, duration_ms: Optional[float] = None) -> None:
        """Log behavior tree node transition."""
        self.log_event(
            EventType.BT_TRANSITION,
            tick,
            worker_id,
            {
                "node_name": node_name,
                "node_type": node_type,
                "action": action,  # "enter", "exit"
                "status": status,
                "duration_ms": duration_ms
            },
            tags=[f"node:{node_name}", f"action:{action}"]
        )
        
    def log_bb_diff(self, tick: int, worker_id: Union[int, str],
                   changes: Dict[str, Dict[str, Any]], phase: str = "unknown") -> None:
        """Log blackboard changes."""
        if not changes:
            return
            
        self.log_event(
            EventType.BB_DIFF,
            tick,
            worker_id,
            {
                "phase": phase,  # "pre_sensors", "post_sensors"
                "change_count": len(changes),
                "changes": [
                    {
                        "key": k,
                        "old": v.get("old"),
                        "new": v.get("new")
                    }
                    for k, v in changes.items()
                ]
            },
            tags=[f"phase:{phase}", f"changes:{len(changes)}"]
        )
        
    def log_intent_execution(self, tick: int, worker_id: Union[int, str],
                           intent_type: str, status: str, 
                           details: Optional[Dict[str, Any]] = None) -> None:
        """Log intent execution result."""
        self.log_event(
            EventType.INTENT_EXECUTION,
            tick,
            worker_id,
            {
                "intent_type": intent_type,
                "status": status,  # "executed", "rejected"
                "details": details or {}
            },
            tags=[f"intent:{intent_type}", f"status:{status}"]
        )
        
    def log_performance_tick(self, tick: int, phase_durations: Dict[str, float],
                           total_duration: float) -> None:
        """Log performance metrics for a tick."""
        self.log_event(
            EventType.PERFORMANCE,
            tick,
            "system",
            {
                "total_ms": total_duration * 1000,
                "phases_ms": {k: v * 1000 for k, v in phase_durations.items()},
                "phase_stats": self.performance.get_stats()
            },
            tags=["performance", f"tick:{tick}"]
        )
        
    def flush(self) -> int:
        """Flush buffered events to handlers."""
        with self._lock:
            return self._flush_locked()
            
    def _flush_locked(self) -> int:
        """Internal flush without lock (call with lock held)."""
        if not self.buffer:
            return 0
            
        events_to_flush = self.buffer[:]
        self.buffer.clear()
        
        # Call handlers
        for handler in self._handlers:
            try:
                handler(events_to_flush)
            except Exception as e:
                log.error("Event handler error: %s", e, exc_info=True)
                
        return len(events_to_flush)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics."""
        with self._lock:
            return {
                "total_events": self._event_counter,
                "buffered": len(self.buffer),
                "by_type": dict(self.event_counts),
                "performance": self.performance.get_stats()
            }
            
    def reset(self) -> None:
        """Reset logger state."""
        with self._lock:
            self.buffer.clear()
            self.event_counts.clear()
            self.performance.reset()
            self._event_counter = 0
            

# Global instance for convenient access
_global_logger: Optional[EventLogger] = None


def get_event_logger() -> EventLogger:
    """Get or create global event logger."""
    global _global_logger
    if _global_logger is None:
        _global_logger = EventLogger()
    return _global_logger


def configure_event_logger(**kwargs) -> EventLogger:
    """Configure and return global event logger."""
    global _global_logger
    _global_logger = EventLogger(**kwargs)
    return _global_logger


# Convenience functions
def log_bt_transition(tick: int, worker_id: Union[int, str], 
                     node_name: str, node_type: str, action: str, **kwargs) -> None:
    """Log BT transition via global logger."""
    get_event_logger().log_bt_transition(tick, worker_id, node_name, node_type, action, **kwargs)


def log_bb_diff(tick: int, worker_id: Union[int, str], 
               changes: Dict[str, Dict[str, Any]], phase: str = "unknown") -> None:
    """Log BB diff via global logger."""
    get_event_logger().log_bb_diff(tick, worker_id, changes, phase)


def log_intent_execution(tick: int, worker_id: Union[int, str],
                        intent_type: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Log intent execution via global logger."""
    get_event_logger().log_intent_execution(tick, worker_id, intent_type, status, details)

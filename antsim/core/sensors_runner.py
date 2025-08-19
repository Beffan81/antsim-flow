# FILE: antsim/core/sensors_runner.py
"""Sensors runner that executes sensor plugins and updates blackboards.

Enhancements for Step 14 (Performance):
- Central per-tick spatial index (KD-Tree if available, else lightweight mapping), shared via environment.
- Sensor policies with on_interval to throttle expensive sensors deterministically.
- Idempotent behavior per tick; sensors remain pure (write-only BB); index building is a runner concern.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple

from ..registry.manager import PluginManager
from ..io.event_logger import get_event_logger, EventType

logger = logging.getLogger(__name__)


class SensorsRunner:
    """Executes sensor plugins and manages blackboard updates."""
    def __init__(self, plugin_manager: PluginManager):
        """Initialize sensors runner.
        
        Args:
            plugin_manager: Plugin manager instance
        """
        self.plugin_manager = plugin_manager
        self._sensor_cache: Dict[str, callable] = {}
        self._events = get_event_logger()
        # Performance/Policy & Spatial cache (per environment)
        self._sensor_policies: Dict[str, Dict[str, Any]] = {}
        self._spatial_cache: Dict[int, Dict[str, Any]] = {}
        self._last_ran_sensors: List[str] = []
        self._load_sensors()
        
    def _load_sensors(self) -> None:
        """Cache all available sensors and prepare default policies."""
        sensor_names = self.plugin_manager.list_sensors()
        for name in sensor_names:
            sensor = self.plugin_manager.get_sensor(name)
            if sensor:
                self._sensor_cache[name] = sensor
        
        logger.info("Loaded %d sensors: %s", len(self._sensor_cache), list(self._sensor_cache.keys()))
        # Default policy (heuristic): throttle expensive sensors
        # - Pheromone-related checks are often broader scans -> run every 2 ticks
        # - Food detection scans radius -> run every 2 ticks
        # - Gradient sensors can also be throttled
        for sname in self._sensor_cache.keys():
            if any(k in sname for k in ("pheromone", "food_detection", "gradient")):
                self.set_sensor_policy(sname, on_interval=2)

    # ---------- Sensor policy control ----------

    def set_sensor_policy(self, sensor_name: str, on_interval: Optional[int] = None) -> None:
        """Set policy for a sensor. on_interval: run only when (tick % interval == 0)."""
        pol = self._sensor_policies.get(sensor_name, {})
        if on_interval is not None:
            pol["on_interval"] = max(1, int(on_interval))
        else:
            pol.pop("on_interval", None)
        self._sensor_policies[sensor_name] = pol

    def _should_run_sensor(self, name: str, environment: Any) -> bool:
        """Evaluate whether to run a sensor this tick based on policy."""
        pol = self._sensor_policies.get(name)
        if not pol:
            return True
        interval = int(pol.get("on_interval", 1))
        if interval <= 1:
            return True
        tick = int(getattr(environment, "cycle_count", 0))
        return (tick % interval) == 0

    # ---------- Spatial index (per-tick, shared) ----------

    def _ensure_spatial_index(self, environment: Any) -> Dict[str, Any]:
        """
        Build/reuse a per-tick spatial index and expose it on the environment for shared use.
        Tries SciPy cKDTree if available; falls back to simple mapping. Idempotent per tick.
        """
        env_id = id(environment)
        tick = int(getattr(environment, "cycle_count", 0))
        cache = self._spatial_cache.get(env_id)
        if cache and cache.get("tick") == tick:
            # Ensure env has attributes for shared use (idempotent)
            self._expose_spatial_on_env(environment, cache)
            return cache

        # Build index from environment state (prefer ant_registry)
        positions: List[Tuple[int, int]] = []
        objects: List[Any] = []
        pos_to_obj: Dict[Tuple[int, int], Any] = {}

        # Preferred path: ant_registry
        reg = getattr(environment, "ant_registry", None)
        if isinstance(reg, dict):
            for ant in reg.values():
                if ant is None:
                    continue
                pos = getattr(ant, "position", None)
                if isinstance(pos, (list, tuple)) and len(pos) == 2:
                    try:
                        p = (int(pos[0]), int(pos[1]))
                        positions.append(p)
                        objects.append(ant)
                        pos_to_obj[p] = ant
                    except Exception:
                        continue
        else:
            # Fallback: scan grid occupancy if available
            try:
                grid = getattr(environment, "grid", None)
                if grid is not None:
                    for y, row in enumerate(grid):
                        for x, cell in enumerate(row):
                            ant = getattr(cell, "ant", None)
                            if ant is not None:
                                positions.append((x, y))
                                objects.append(ant)
                                pos_to_obj[(x, y)] = ant
            except Exception:
                pass

        kdtree = None
        # Try to construct KDTree (optional; tolerate missing deps)
        if positions:
            try:
                import numpy as np  # type: ignore
                try:
                    from scipy.spatial import cKDTree  # type: ignore
                    kdtree = cKDTree(np.array(positions))
                except Exception:
                    kdtree = None  # SciPy not available: still useful to share positions mapping
            except Exception:
                # NumPy not available: still share positions mapping
                kdtree = None

        cache = {"tick": tick, "positions": positions, "objects": objects, "pos_to_obj": pos_to_obj, "kdtree": kdtree}
        self._spatial_cache[env_id] = cache
        self._expose_spatial_on_env(environment, cache)

        logger.debug(
            "spatial_index_built tick=%s ants=%d kdtree=%s",
            tick, len(objects), "yes" if kdtree is not None else "no"
        )
        return cache

    @staticmethod
    def _expose_spatial_on_env(environment: Any, cache: Dict[str, Any]) -> None:
        """Expose spatial index artifacts for shared use (read-only by sensors, pure)."""
        try:
            setattr(environment, "spatial_index", cache.get("kdtree"))
            setattr(environment, "spatial_index_positions", list(cache.get("positions", [])))
            setattr(environment, "spatial_index_objects", list(cache.get("objects", [])))
            setattr(environment, "position_to_ant", dict(cache.get("pos_to_obj", {})))
        except Exception:
            # Never fail due to attribute setting; it's an optimization only.
            pass

    # ---------- Sensor execution ----------

    def run_sensors(self, worker: 'Worker', environment: Any, 
                    sensor_list: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run sensors and collect their output (with policy-based skipping and timing).
        
        Args:
            worker: Worker to run sensors for
            environment: Environment instance
            sensor_list: Optional list of specific sensors to run (None = all)
            
        Returns:
            Merged dictionary of all sensor outputs
        """
        sensors_to_consider = sensor_list if sensor_list else list(self._sensor_cache.keys())
        merged_data: Dict[str, Any] = {}
        ran: List[str] = []

        wid = getattr(worker, "id", "?")
        logger.debug("Running up to %d sensors for worker %s", len(sensors_to_consider), wid)

        for sensor_name in sensors_to_consider:
            sensor_func = self._sensor_cache.get(sensor_name)
            if not sensor_func:
                logger.warning("Sensor '%s' not found", sensor_name)
                continue

            # Policy check
            if not self._should_run_sensor(sensor_name, environment):
                logger.debug("sensor_skip name=%s reason=policy_on_interval", sensor_name)
                continue

            try:
                t0 = time.perf_counter()
                sensor_data = sensor_func(worker, environment)
                dt_ms = (time.perf_counter() - t0) * 1000.0
                ran.append(sensor_name)

                if sensor_data and isinstance(sensor_data, dict):
                    logger.debug("sensor_run name=%s keys=%d duration_ms=%.3f", sensor_name, len(sensor_data), dt_ms)
                    for key, value in sensor_data.items():
                        if key in merged_data:
                            logger.warning("Key '%s' already exists, overwriting with %s data", key, sensor_name)
                        merged_data[key] = value
                else:
                    logger.debug("sensor_run name=%s returned_empty=True duration_ms=%.3f", sensor_name, dt_ms)

            except Exception as e:
                logger.error("Error running sensor '%s': %s", sensor_name, e, exc_info=True)

        # Remember actually run sensors for subsequent logging
        self._last_ran_sensors = ran
        return merged_data

    def update_worker(self, worker: 'Worker', environment: Any,
                      sensor_list: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run sensors and update worker's blackboard.
        
        Args:
            worker: Worker to update
            environment: Environment instance
            sensor_list: Optional list of specific sensors to run
            
        Returns:
            Dictionary of changes made to blackboard
        """
        # Build/reuse central spatial index once per tick (shared across sensors/plugins)
        self._ensure_spatial_index(environment)

        # Run sensors (with policies)
        sensor_data = self.run_sensors(worker, environment, sensor_list)

        # Update blackboard with sensor data (pure write into BB)
        bb = getattr(worker, "blackboard", None)
        pre_cycle = None
        wid = getattr(worker, "id", "unknown")
        try:
            pre_cycle = bb.get("cycle", None) if bb else None
        except Exception:
            pre_cycle = None
        worker.update_from_sensors(sensor_data)
        
        # Get and commit changes
        changes = worker.blackboard.diff()
        worker.blackboard.commit()
        
        if changes:
            logger.info(
                "Worker %s updated with %d changes: %s",
                getattr(worker, "id", "?"), len(changes), list(changes.keys())
            )
        # Structured sensor update event (use actually ran sensors)
        try:
            tick = worker.blackboard.get("cycle", getattr(environment, "cycle_count", 0))
            self._events.log_event(
                EventType.SENSOR_UPDATE,
                int(tick) if isinstance(tick, int) else 0,
                wid,
                {
                    "sensors_run": list(self._last_ran_sensors),
                    "change_count": len(changes),
                    "changed_keys": list(changes.keys()),
                    "pre_cycle": pre_cycle,
                    "post_cycle": worker.blackboard.get("cycle", pre_cycle),
                },
                tags=[f"worker:{wid}", f"changes:{len(changes)}"]
            )
        except Exception:
            # Never fail because of logging
            pass
        
        return changes

    def run_selective(self, worker: 'Worker', environment: Any,
                      condition: callable) -> Dict[str, Any]:
        """Run only sensors that meet a condition.
        
        Args:
            worker: Worker to run sensors for
            environment: Environment instance
            condition: Function that takes sensor name and returns bool
            
        Returns:
            Merged sensor data
        """
        sensors_to_run = [name for name in self._sensor_cache if condition(name)]
        return self.run_sensors(worker, environment, sensors_to_run)

    def get_available_sensors(self) -> List[str]:
        """Get list of available sensor names."""
        return list(self._sensor_cache.keys())

# FILE: antsim/registry/manager.py
# antsim/registry/manager.py
"""Plugin management system for ant simulation."""
import logging
import pluggy
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import importlib.util
import sys

logger = logging.getLogger(__name__)

# Robuste Hookspec-Referenz: direktes Modul importieren
from . import hookspecs


class PluginManager:
    """Manages plugin discovery, loading and access."""
    
    def __init__(self, dev_mode: bool = False):
        """Initialize plugin manager.
        
        Args:
            dev_mode: Enable development mode with auto-loading from plugins directory
        """
        self.pm = pluggy.PluginManager("antsim")
        self.pm.add_hookspecs(hookspecs)
        
        self._steps: Dict[str, Callable] = {}
        self._triggers: Dict[str, Callable] = {}
        self._sensors: Dict[str, Callable] = {}
        
        self.dev_mode = dev_mode
        logger.info(f"PluginManager initialized (dev_mode={dev_mode})")
        
    def discover_and_register(self):
        """Discover and register all available plugins (idempotent)."""
        # Reset interner Zustand, um wiederholbare Aufrufe zu erlauben
        self._steps.clear()
        self._triggers.clear()
        self._sensors.clear()
        self.pm = pluggy.PluginManager("antsim")
        self.pm.add_hookspecs(hookspecs)
        
        # Load from entry points
        self._load_entry_point_plugins()
        
        # Load from dev directory if in dev mode
        if self.dev_mode:
            self._load_dev_plugins()
            
        # Collect all registered components
        self._collect_components()
        
        logger.info(
            "Plugin discovery complete: %d steps, %d triggers, %d sensors",
            len(self._steps), len(self._triggers), len(self._sensors)
        )
    
    def _load_entry_point_plugins(self):
        """Load plugins from setuptools entry points."""
        try:
            # Python 3.8+: importlib.metadata
            try:
                import importlib.metadata as importlib_metadata
            except Exception:  # pragma: no cover
                import importlib_metadata  # type: ignore
        except Exception:
            logger.debug("importlib.metadata not available, skipping entry point loading")
            return
        
        try:
            eps = importlib_metadata.entry_points()
            # Python 3.10+: EntryPoints.select
            if hasattr(eps, "select"):
                iter_eps = eps.select(group="antsim.plugins")
            else:
                # Vor 3.10: dict-artiger Zugriff
                iter_eps = eps.get("antsim.plugins", [])
            for ep in iter_eps:
                try:
                    plugin = ep.load()
                    self.pm.register(plugin)
                    logger.info("Loaded plugin from entry point: %s", getattr(ep, "name", ep))
                except Exception as e:
                    logger.error("Failed to load plugin %s: %s", getattr(ep, "name", ep), e, exc_info=True)
        except Exception as e:
            logger.error("Entry point discovery failed: %s", e, exc_info=True)
    
    def _load_dev_plugins(self):
        """Load plugins from development directory."""
        plugins_dir = Path(__file__).parent.parent / "plugins"
        if not plugins_dir.exists():
            logger.debug("Dev plugins directory not found: %s", plugins_dir)
            return
            
        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
                
            try:
                spec = importlib.util.spec_from_file_location(
                    f"antsim.plugins.{plugin_file.stem}", 
                    plugin_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = module
                    spec.loader.exec_module(module)
                    self.pm.register(module)
                    logger.info("Loaded dev plugin: %s", plugin_file.name)
            except Exception as e:
                logger.error("Failed to load dev plugin %s: %s", plugin_file, e, exc_info=True)

    @staticmethod
    def _origin_of(func: Callable) -> str:
        """Resolve origin of a function for clearer collision errors."""
        try:
            mod = getattr(func, "__module__", "unknown")
            qual = getattr(func, "__qualname__", getattr(func, "__name__", "unknown"))
            return f"{mod}:{qual}"
        except Exception:
            return "unknown"

    def _register_items(
        self,
        registry_map: Dict[str, Callable],
        items: Dict[str, Callable],
        kind: str
    ) -> None:
        """
        Register items into a specific registry map with duplicate detection.
        Raises ValueError with detailed origin info on collisions.
        """
        if not items:
            return
        for name, func in items.items():
            if name in registry_map:
                existing = registry_map[name]
                msg = (
                    f"Duplicate {kind} registration detected for '{name}'. "
                    f"Existing: {self._origin_of(existing)}; New: {self._origin_of(func)}. "
                    f"Names must be unique across all plugins."
                )
                # Log clear error before raising
                logger.error(msg)
                raise ValueError(msg)
            registry_map[name] = func
            logger.debug("Registered %s: %s (from %s)", kind, name, self._origin_of(func))
    
    def _collect_components(self):
        """Collect all components from registered plugins with clear collision errors."""
        # Collect steps
        for step_dict in self.pm.hook.register_steps():
            if not step_dict:
                continue
            self._register_items(self._steps, step_dict, kind="step")

        # Collect triggers
        for trigger_dict in self.pm.hook.register_triggers():
            if not trigger_dict:
                continue
            self._register_items(self._triggers, trigger_dict, kind="trigger")

        # Collect sensors
        for sensor_dict in self.pm.hook.register_sensors():
            if not sensor_dict:
                continue
            self._register_items(self._sensors, sensor_dict, kind="sensor")
    
    def get_step(self, name: str) -> Optional[Callable]:
        """Get a registered step function by name."""
        return self._steps.get(name)
    
    def get_trigger(self, name: str) -> Optional[Callable]:
        """Get a registered trigger function by name."""
        return self._triggers.get(name)
    
    def get_sensor(self, name: str) -> Optional[Callable]:
        """Get a registered sensor function by name."""
        return self._sensors.get(name)
    
    def list_steps(self) -> List[str]:
        """List all registered step names."""
        return list(self._steps.keys())
    
    def list_triggers(self) -> List[str]:
        """List all registered trigger names."""
        return list(self._triggers.keys())
    
    def list_sensors(self) -> List[str]:
        """List all registered sensor names."""
        return list(self._sensors.keys())

# FILE: antsim/io/config_loader.py
"""
Konfigurations-Loader und Pydantic-Schemata für antsim.

Ziele:
- YAML/JSON/OmegaConf (optional) laden und gegen Schemata validieren.
- Step-/Trigger-Namen gegen PluginManager prüfen (klare Fehlermeldungen).
- Aus validierter Struktur BT-Spezifikation erzeugen und via TreeBuilder bauen.
- Klare, aggregierte Validierungsfehler ausgeben.

Hinweise:
- Rein-funktional: keine Seiteneffekte außerhalb von Logging.
- Hydra/OmegaConf optional: Wird verwendet, wenn omegaconf vorhanden ist.
- Erweiterung (Step 7): TriggerRef/TaskConfig ergänzt; ConditionRef akzeptiert Trigger mit Parametern.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator, model_validator

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except Exception:
    _YAML_AVAILABLE = False

# Optional: OmegaConf-Unterstützung (Hydra-kompatible Loader-Oberfläche)
try:
    from omegaconf import OmegaConf  # type: ignore
    _OMEGA_AVAILABLE = True
except Exception:
    _OMEGA_AVAILABLE = False

from ..registry.manager import PluginManager
from ..behavior.bt import TreeBuilder

log = logging.getLogger(__name__)


# ---------- Pydantic Schemata ----------

class EnvironmentConfig(BaseModel):
    """Umgebungsschema mit Nest-Konfiguration."""
    width: int = Field(20, ge=1)
    height: int = Field(20, ge=1)
    entry_positions: Optional[List[Tuple[int, int]]] = None
    
    # Nest-Konfiguration
    nest_type: str = Field("standard", description="Nest type: 'standard', 'custom', 'none'")
    nest_size: Optional[Tuple[int, int]] = Field(None, description="Custom nest size as (width, height)")
    center_nest: bool = Field(True, description="Whether to center the nest on the field")
    
    @field_validator("nest_type")
    @classmethod
    def validate_nest_type(cls, v: str) -> str:
        valid_types = {"standard", "custom", "none"}
        if v not in valid_types:
            raise ValueError(f"nest_type must be one of {valid_types}, got '{v}'")
        return v


class QueenEnergyConfig(BaseModel):
    """Queen energy system configuration."""
    energy_conversion_rate: int = Field(8, ge=1, description="Energy gained per stomach unit per tick")
    energy_loss_rate: int = Field(3, ge=0, description="Energy lost per tick when stomach empty")
    stomach_depletion_rate: int = Field(5, ge=1, description="Stomach units consumed per tick")
    hunger_pheromone_strength: int = Field(3, ge=1, description="Strength of hunger pheromone signal")


class BroodConfig(BaseModel):
    """Brood (egg/larvae) configuration."""
    initial_energy: int = Field(50, ge=0, description="Starting energy for new brood")
    max_energy: int = Field(100, ge=1, description="Maximum energy for brood")
    initial_stomach: int = Field(0, ge=0, description="Starting stomach contents")
    stomach_capacity: int = Field(80, ge=1, description="Maximum stomach capacity")
    
    # Growth and maturation
    maturation_time: int = Field(50, ge=1, description="Ticks needed to mature into worker")
    
    # Energy processing
    energy_conversion_rate: int = Field(5, ge=1, description="Energy gained per stomach unit per tick")
    energy_loss_rate: int = Field(2, ge=0, description="Energy lost per tick when stomach empty")
    stomach_depletion_rate: int = Field(3, ge=1, description="Stomach units consumed per tick")
    hunger_pheromone_strength: int = Field(2, ge=1, description="Strength of hunger pheromone signal")


class EmergentBehaviorConfig(BaseModel):
    """Configuration for emergent behavior parameters."""
    hunger_pheromone_detection_range: int = Field(3, ge=1, description="Detection range for hunger pheromones")
    trail_success_multiplier: float = Field(2.0, gt=0, description="Trail reinforcement factor on success")
    trail_failure_multiplier: float = Field(0.5, gt=0, description="Trail weakening factor on failure")
    hunger_detection_threshold: float = Field(1.1, gt=0, description="Hunger detection threshold ratio")
    direct_feeding_range: int = Field(1, ge=1, description="Range for direct feeding (8-neighborhood)")


class PheromoneConfig(BaseModel):
    """Configuration for pheromone system parameters."""
    evaporation_rate: float = Field(0.01, ge=0.0, lt=1.0, description="Pheromone evaporation rate per tick")
    diffusion_alpha: float = Field(0.1, ge=0.0, le=0.25, description="Diffusion weight to 4-neighbors")
    types: List[str] = Field(default_factory=lambda: ["trail", "hunger", "alarm"], description="Available pheromone types")
    allow_dynamic_types: bool = Field(True, description="Allow creating new pheromone types at runtime")


class SimulationTimingConfig(BaseModel):
    """Configuration for simulation timing and execution parameters."""
    max_cycles: int = Field(1000, ge=1, description="Maximum number of simulation cycles")
    tick_interval_ms: int = Field(100, ge=1, description="Milliseconds between simulation ticks")
    dashboard_update_frequency: int = Field(3, ge=1, description="Update dashboard every N ticks")


class ColonyConfig(BaseModel):
    """Configuration for initial colony setup."""
    queen_count: int = Field(1, ge=1, description="Number of queens in initial colony")
    worker_count: int = Field(5, ge=0, description="Number of workers in initial colony")
    entry_positions: List[Tuple[int, int]] = Field(
        default_factory=lambda: [(10, 10), (11, 10), (10, 11)],
        description="Entry positions for initial colony placement"
    )


class DefaultFoodSourcesConfig(BaseModel):
    """Configuration for default food sources."""
    enabled: bool = Field(True, description="Whether to create default food sources")
    sources: List[FoodSourceConfig] = Field(
        default_factory=lambda: [
            FoodSourceConfig(position=(5, 5), amount=200),
            FoodSourceConfig(position=(35, 25), amount=150),
            FoodSourceConfig(position=(20, 5), amount=100)
        ],
        description="Default food source configurations"
    )


class AgentConfig(BaseModel):
    """Configuration for both queens and workers."""
    # Legacy support: total agent count (deprecated)
    count: Optional[int] = Field(None, ge=1, description="Total agent count (deprecated, use queen_count + worker_count)")
    
    # New composition-based configuration
    queen_count: int = Field(1, ge=1, description="Number of queens")
    worker_count: int = Field(2, ge=0, description="Number of workers")
    
    # Queen-specific configuration
    queen_config: Dict[str, Any] = Field(default_factory=lambda: {
        "energy": 200,
        "max_energy": 200,
        "social_stomach": 150,
        "social_stomach_capacity": 150,
        "egg_laying_interval": 10,
        "max_eggs": 100,
        "hunger_threshold": 75,
    })
    
    # Worker-specific configuration
    worker_config: Dict[str, Any] = Field(default_factory=lambda: {
        "energy": 100,
        "max_energy": 100,
        "stomach_capacity": 100,
        "social_stomach_capacity": 100,
        "hunger_threshold": 50,
    })
    
    @field_validator("count")
    @classmethod
    def validate_legacy_count(cls, v, values):
        """Warn about deprecated count field."""
        if v is not None:
            import logging
            logging.getLogger(__name__).warning(
                "AgentConfig.count is deprecated. Use queen_count and worker_count instead."
            )
        return v


class StepRef(BaseModel):
    """Referenz auf Step-Plugin inkl. optionaler Parameter."""
    name: str = Field(..., description="Plugin Step-Name")
    params: Dict[str, Any] = Field(default_factory=dict)


class TriggerRef(BaseModel):
    """Referenz auf Trigger-Plugin inkl. optionaler Parameter."""
    name: str = Field(..., description="Plugin Trigger-Name")
    params: Dict[str, Any] = Field(default_factory=dict)


class ConditionRef(BaseModel):
    """Ausdruck über Trigger-Plugins."""
    # Unterstützt sowohl einfache Namen als auch strukturierte TriggerRef-Objekte
    triggers: List[Union[str, TriggerRef]] = Field(default_factory=list)
    logic: str = Field("AND")

    @field_validator("logic")
    @classmethod
    def _logic_ok(cls, v: str) -> str:
        lv = (v or "AND").upper()
        if lv not in ("AND", "OR"):
            raise ValueError(f"logic must be AND or OR, got '{v}'")
        return lv

    def trigger_names(self) -> List[str]:
        names: List[str] = []
        for t in self.triggers or []:
            if isinstance(t, str):
                names.append(t)
            elif isinstance(t, TriggerRef):
                names.append(t.name)
        return names

    def trigger_params_map(self) -> Dict[str, Dict[str, Any]]:
        """
        Liefert optionale Parameter je Trigger-Name.
        Falls mehrfach derselbe Name referenziert wird, gewinnt der letzte Eintrag.
        """
        out: Dict[str, Dict[str, Any]] = {}
        for t in self.triggers or []:
            if isinstance(t, TriggerRef):
                out[t.name] = dict(t.params or {})
        return out


class BTNode(BaseModel):
    """Discriminated Node-Schema: type in {'sequence','selector','condition','step'}"""
    type: str = Field(..., description="Node-Typ")
    name: Optional[str] = None
    # For composites
    children: Optional[List["BTNode"]] = None
    # For condition
    condition: Optional[ConditionRef] = None
    # For step
    step: Optional[StepRef] = None

    @model_validator(mode='after')
    def _validate_shape(self):
        t = (self.type or "").lower()
        if t in ("sequence", "selector"):
            if not self.children:
                raise ValueError(f"{t} node requires children")
        elif t == "condition":
            if not self.condition:
                raise ValueError("condition node requires 'condition'")
        elif t == "step":
            if not self.step:
                raise ValueError("step node requires 'step'")
        else:
            raise ValueError(f"Unsupported node type '{self.type}'")
        return self

    def all_triggers(self) -> List[str]:
        t = (self.type or "").lower()
        out: List[str] = []
        if t == "condition" and self.condition:
            out.extend(self.condition.trigger_names())
        if self.children:
            for c in self.children:
                out.extend(c.all_triggers())
        return out

    def all_steps(self) -> List[str]:
        t = (self.type or "").lower()
        out: List[str] = []
        if t == "step" and self.step:
            out.append(self.step.name)
        if self.children:
            for c in self.children:
                out.extend(c.all_steps())
        return out

    def to_builder_spec(self) -> Dict[str, Any]:
        """Konvertiert in TreeBuilder-kompatibles Spec-Dict (rein)."""
        t = (self.type or "").lower()
        base = {"type": t, "name": self.name or t}
        if t in ("sequence", "selector"):
            base["children"] = [c.to_builder_spec() for c in (self.children or [])]
            return base
        if t == "condition" and self.condition:
            base["triggers"] = self.condition.trigger_names()
            base["logic"] = self.condition.logic
            # Optional: Parameter mitgeben (TreeBuilder ignoriert unbekannte Felder robust)
            params_map = self.condition.trigger_params_map()
            if params_map:
                base["trigger_params"] = params_map
            return base
        if t == "step" and self.step:
            base["step"] = self.step.name
            base["params"] = dict(self.step.params or {})
            return base
        # Defensive fallback
        raise ValueError(f"Cannot render node of type '{self.type}'")

# Für rekursive Typen
BTNode.update_forward_refs()


class BehaviorTreeConfig(BaseModel):
    """Top-Level BT-Konfiguration."""
    root: BTNode

    def all_triggers(self) -> List[str]:
        return self.root.all_triggers()

    def all_steps(self) -> List[str]:
        return self.root.all_steps()

    def to_builder_spec(self) -> Dict[str, Any]:
        return self.root.to_builder_spec()


class TaskConfig(BaseModel):
    """
    Optionales Task-Schema (Kompatibilität zur Roadmap; derzeit von BT nicht verwendet).
    Erlaubt Steps/Trigger mit Parametern zu definieren.
    """
    name: str
    priority: int = 0
    steps: List[Union[str, StepRef]] = Field(default_factory=list)
    triggers: List[Union[str, TriggerRef]] = Field(default_factory=list)
    logic: str = Field("AND")

    @field_validator("logic")
    @classmethod
    def _task_logic_ok(cls, v: str) -> str:
        lv = (v or "AND").upper()
        if lv not in ("AND", "OR"):
            raise ValueError(f"logic must be AND or OR, got '{v}'")
        return lv


class FoodSourceConfig(BaseModel):
    """Konfiguration für Futterquellen."""
    position: Tuple[int, int] = Field(..., description="Position der Futterquelle als (x, y)")
    amount: int = Field(..., ge=1, description="Menge der Nahrung an dieser Quelle")
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


class SimulationConfig(BaseModel):
    """Vollständige Simulation-Konfiguration."""
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    behavior_tree: BehaviorTreeConfig
    tasks: Optional[List[TaskConfig]] = None
    food_sources: Optional[List[FoodSourceConfig]] = None
    
    # Energy system configurations
    queen_energy: Optional[QueenEnergyConfig] = Field(default_factory=QueenEnergyConfig)
    brood: Optional[BroodConfig] = Field(default_factory=BroodConfig)
    
    # New high-priority configurable sections
    emergent_behavior: Optional[EmergentBehaviorConfig] = Field(default_factory=EmergentBehaviorConfig)
    pheromones: Optional[PheromoneConfig] = Field(default_factory=PheromoneConfig)
    simulation: Optional[SimulationTimingConfig] = Field(default_factory=SimulationTimingConfig)
    colony: Optional[ColonyConfig] = Field(default_factory=ColonyConfig)
    default_food_sources: Optional[DefaultFoodSourcesConfig] = Field(default_factory=DefaultFoodSourcesConfig)


# ---------- Loader-/Validierungsfunktionen ----------

def _as_path(p: Union[str, Path]) -> Path:
    return Path(p) if not isinstance(p, Path) else p


def _load_text(path_or_text: Union[str, Path]) -> str:
    """
    Lädt Text aus Datei oder interpretiert Eingabe als Text (rein).
    """
    # If it's already a Path object, check if it exists
    if isinstance(path_or_text, Path):
        if path_or_text.exists():
            return path_or_text.read_text(encoding="utf-8")
        return str(path_or_text)
    
    # For strings, check if it looks like JSON/YAML content (contains newlines or braces)
    # or if it's too long to be a valid path
    if isinstance(path_or_text, str):
        # If it contains newlines or starts with { or [, treat as content
        if '\n' in path_or_text or path_or_text.strip().startswith(('{', '[', 'behavior_tree:')):
            return path_or_text
        
        # If it's too long to be a valid path, treat as content
        if len(path_or_text) > 255:  # Most filesystems have a 255 char limit
            return path_or_text
        
        # Otherwise, try to treat it as a path
        try:
            p = Path(path_or_text)
            if p.exists():
                return p.read_text(encoding="utf-8")
        except (OSError, ValueError):
            # If creating the Path fails, treat as content
            pass
    
    return str(path_or_text)


def load_raw_config_yaml_or_json(path_or_text: Union[str, Path]) -> Dict[str, Any]:
    """
    Lädt YAML (präferiert) oder JSON in ein Dict (rein).
    """
    text = _load_text(path_or_text)
    if _YAML_AVAILABLE:
        try:
            data = yaml.safe_load(text)  # type: ignore
            if not isinstance(data, dict):
                raise ValueError("Top-level YAML must be a mapping")
            return data
        except Exception as e:
            raise ValueError(f"YAML parse error: {e}")
    # Fallback: JSON
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Top-level JSON must be an object")
        return data
    except Exception as e:
        raise ValueError(f"JSON parse error (PyYAML not available): {e}")


def load_raw_config_omegaconf(path_or_text: Union[str, Path]) -> Dict[str, Any]:
    """
    Optionaler Loader via OmegaConf (Hydra-kompatibel). Rein.
    - Akzeptiert Pfad zu YAML/JSON oder reinen Text.
    - Gibt natives Dict zurück (resolve=True).
    """
    if not _OMEGA_AVAILABLE:
        raise RuntimeError("OmegaConf not available")
    p = _as_path(path_or_text)
    try:
        if p.exists():
            cfg = OmegaConf.load(str(p))  # type: ignore
        else:
            cfg = OmegaConf.create(str(path_or_text))  # type: ignore
        data = OmegaConf.to_container(cfg, resolve=True)  # type: ignore
        if not isinstance(data, dict):
            raise ValueError("Top-level config must be a mapping/object")
        return data  # type: ignore
    except Exception as e:
        raise ValueError(f"OmegaConf parse error: {e}")


def load_raw_config(path_or_text: Union[str, Path], prefer_omegaconf: bool = False) -> Dict[str, Any]:
    """
    Lädt Konfiguration als Dict:
    - Wenn prefer_omegaconf=True und OmegaConf verfügbar: nutze OmegaConf.
    - Sonst YAML/JSON-Loader.
    """
    if prefer_omegaconf and _OMEGA_AVAILABLE:
        return load_raw_config_omegaconf(path_or_text)
    return load_raw_config_yaml_or_json(path_or_text)


def parse_simulation_config(data: Dict[str, Any]) -> SimulationConfig:
    """
    Validiert rohes Dict gegen pydantic-Modelle (rein).
    Erlaubt BT unter 'behavior_tree' oder direkt als 'root'.
    """
    if "behavior_tree" not in data and "root" in data:
        data = dict(data)
        data["behavior_tree"] = {"root": data.pop("root")}
    try:
        cfg = SimulationConfig(**data)
        return cfg
    except Exception as e:
        raise ValueError(f"Schema validation failed: {e}")


def validate_plugin_names(pm: PluginManager, bt: BehaviorTreeConfig) -> None:
    """
    Prüft, ob alle referenzierten Steps/Trigger existieren; aggregiert Fehler.
    """
    steps_available = set(pm.list_steps())
    triggers_available = set(pm.list_triggers())

    # extrahiere referenzierte Namen aus dem BT
    steps_ref = set(bt.all_steps())
    triggers_ref = set(bt.all_triggers())

    missing_steps = sorted(steps_ref - steps_available)
    missing_triggers = sorted(triggers_ref - triggers_available)

    errs = []
    if missing_steps:
        errs.append(f"Unknown steps: {missing_steps}")
    if missing_triggers:
        errs.append(f"Unknown triggers: {missing_triggers}")

    if errs:
        # Kompakte, klare Fehlermeldung
        raise ValueError("; ".join(errs))

    log.info("Config validated against plugins: steps=%d triggers=%d",
             len(steps_ref), len(triggers_ref))


def build_tree_from_config(pm: PluginManager, cfg: SimulationConfig) -> Any:
    """
    Baut den Behavior Tree aus validierter Konfiguration (rein).
    """
    bt_cfg = cfg.behavior_tree
    validate_plugin_names(pm, bt_cfg)
    spec = bt_cfg.to_builder_spec()
    log.debug("BT spec prepared: %s", spec)
    builder = TreeBuilder(pm)
    root = builder.build(spec)
    log.info("Behavior Tree built successfully (root=%s)", spec.get("name", "root"))
    return root


def load_behavior_tree(pm: PluginManager, path_or_text: Union[str, Path], prefer_omegaconf: bool = False) -> Any:
    """
    Bequeme End-to-End-Funktion: Datei/Text laden -> validieren -> BT bauen.
    - prefer_omegaconf: nutzt OmegaConf wenn verfügbar (Hydra-kompatibel).
    """
    raw = load_raw_config(path_or_text, prefer_omegaconf=prefer_omegaconf)
    cfg = parse_simulation_config(raw)
    return build_tree_from_config(pm, cfg)


# --------- Komfort-APIs für Applikationen/Tests ---------

def load_simulation_config(pm: PluginManager, path_or_text: Union[str, Path], prefer_omegaconf: bool = False) -> Tuple[Any, SimulationConfig]:
    """
    Lädt vollständige SimulationConfig und baut den BT.
    Returns: (bt_root, simulation_config)
    """
    raw = load_raw_config(path_or_text, prefer_omegaconf=prefer_omegaconf)
    cfg = parse_simulation_config(raw)
    root = build_tree_from_config(pm, cfg)
    return root, cfg


def validate_config_against_plugins(pm: PluginManager, path_or_text: Union[str, Path], prefer_omegaconf: bool = False) -> Dict[str, Any]:
    """
    Validiert eine Konfiguration gegen Plugins ohne BT zu bauen.
    Liefert Diagnose-Infos (rein, für Tests/Tools).
    """
    raw = load_raw_config(path_or_text, prefer_omegaconf=prefer_omegaconf)
    cfg = parse_simulation_config(raw)
    steps_ref = sorted(set(cfg.behavior_tree.all_steps()))
    triggers_ref = sorted(set(cfg.behavior_tree.all_triggers()))
    steps_available = sorted(pm.list_steps())
    triggers_available = sorted(pm.list_triggers())

    missing_steps = sorted(set(steps_ref) - set(steps_available))
    missing_triggers = sorted(set(triggers_ref) - set(triggers_available))

    info = {
        "steps_referenced": steps_ref,
        "triggers_referenced": triggers_ref,
        "steps_available": steps_available,
        "triggers_available": triggers_available,
        "missing_steps": missing_steps,
        "missing_triggers": missing_triggers,
        "ok": not (missing_steps or missing_triggers),
    }
    # Log kurz & prägnant
    if info["ok"]:
        log.info("Config OK against plugins (steps=%d, triggers=%d)", len(steps_ref), len(triggers_ref))
    else:
        log.error("Config invalid: missing_steps=%s missing_triggers=%s", missing_steps, missing_triggers)
    return info

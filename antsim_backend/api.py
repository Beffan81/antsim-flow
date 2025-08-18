# FILE: antsim_backend/api.py
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from antsim.registry.manager import PluginManager
from antsim.io.config_loader import parse_simulation_config, validate_config_against_plugins
from .run_manager import RunManager  # NEU

# Robustes Logging-Setup (nutzt antsim internes Setup falls vorhanden)
try:
    from antsim.io.logging_setup import setup_logging
    setup_logging(level=logging.INFO, json_lines=False)
except Exception:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

log = logging.getLogger(__name__)

# PluginManager global (dev_mode per ENV überschreibbar; Default: True für lokale Entwicklung)
_DEV_MODE = os.environ.get("ANTSIM_DEV_PLUGINS", "1").lower() in ("1", "true", "yes")
_pm = PluginManager(dev_mode=_DEV_MODE)
try:
    _pm.discover_and_register()
except Exception as e:
    log.error("Plugin discovery failed at startup: %s", e, exc_info=True)

# RunManager global
_run_manager = RunManager(_pm)

app = FastAPI(title="antsim backend", version="0.2.0")

# CORS für lokale Entwicklung bewusst offen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/plugins")
def get_plugins() -> Dict[str, List[str]]:
    """
    Liefert die verfügbaren Plugin-Namen (Steps, Triggers, Sensors).
    """
    try:
        steps = sorted(_pm.list_steps())
        triggers = sorted(_pm.list_triggers())
        sensors = sorted(_pm.list_sensors())
    except Exception as e:
        log.error("Error listing plugins: %s", e, exc_info=True)
        steps, triggers, sensors = [], [], []
    return {"steps": steps, "triggers": triggers, "sensors": sensors}


@app.post("/validate")
def validate_config(config: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Validiert eine SimulationConfig-ähnliche Struktur gegen registrierte Plugins.
    - Nutzt parse_simulation_config für Schema-Prüfung (Pydantic).
    - Gegen Plugins prüfen via validate_config_against_plugins.
    Antwort: ok true/false + missing_steps/missing_triggers (+ Diagnosefelder).
    """
    # 1) Schema-Validierung (liefert klare Fehlermeldung)
    try:
        _ = parse_simulation_config(config)
    except Exception as e:
        log.warning("Schema validation failed: %s", e)
        return {
            "ok": False,
            "error": f"schema: {e}",
            "missing_steps": [],
            "missing_triggers": [],
        }

    # 2) Gegen Plugins prüfen (nutzt denselben Codepfad wie Datei-Validierung, per JSON-String)
    try:
        info = validate_config_against_plugins(_pm, json.dumps(config), prefer_omegaconf=False)
    except Exception as e:
        log.error("Plugin validation failed: %s", e, exc_info=True)
        return {
            "ok": False,
            "error": f"validation: {e}",
            "missing_steps": [],
            "missing_triggers": [],
        }

    return {
        "ok": bool(info.get("ok", False)),
        "missing_steps": info.get("missing_steps", []),
        "missing_triggers": info.get("missing_triggers", []),
        # Diagnose (nützlich fürs UI)
        "steps_referenced": info.get("steps_referenced", []),
        "triggers_referenced": info.get("triggers_referenced", []),
        "steps_available": info.get("steps_available", []),
        "triggers_available": info.get("triggers_available", []),
    }


@app.post("/start")
def start_run(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Startet eine Simulation:
    Body: { simulation: SimulationConfig, options?: { format?: "yaml" | "json" } }
    - Validiert Schema und Plugins
    - Schreibt Konfig in tmp-Datei (YAML/JSON)
    - Startet Subprozess: python -m antsim --bt <tmpfile>
    Antwort bei Erfolg: { ok: true, run_id, pid, config_path }
    Bei Fehler: { ok: false, error }
    """
    if not isinstance(payload, dict):
        return {"ok": False, "error": "invalid body, expected JSON object"}

    simulation = payload.get("simulation")
    options: Optional[Dict[str, Any]] = payload.get("options") or {}
    fmt = (options.get("format", "yaml") if isinstance(options, dict) else "yaml").lower()

    if not isinstance(simulation, dict):
        return {"ok": False, "error": "missing 'simulation' object in body"}

    try:
        res = _run_manager.start_run(simulation, fmt=fmt)
        return {"ok": True, **res}
    except Exception as e:
        log.error("Start failed: %s", e, exc_info=True)
        return {"ok": False, "error": str(e)}


@app.get("/status/{run_id}")
def get_status(run_id: str) -> Dict[str, Any]:
    """
    Liefert den Status eines gestarteten Runs.
    Antwort: { state: "running"|"exited"|"error", exit_code?: number, pid?: number, error?: string }
    """
    try:
        return _run_manager.get_status(run_id)
    except Exception as e:
        log.error("Status error for %s: %s", run_id, e, exc_info=True)
        return {"state": "error", "error": str(e)}


@app.post("/stop/{run_id}")
def stop_run(run_id: str) -> Dict[str, Any]:
    """
    Beendet den Subprozess (sanft, dann hart falls nötig).
    Antwort: { ok: true, state: "exited"|"running", exit_code?: number, pid?: number } oder { ok: false, error }
    """
    try:
        return _run_manager.stop_run(run_id)
    except Exception as e:
        log.error("Stop error for %s: %s", run_id, e, exc_info=True)
        return {"ok": False, "error": str(e)}

# FILE: antsim_backend/run_manager.py
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except Exception:
    _YAML_AVAILABLE = False

from antsim.registry.manager import PluginManager
from antsim.io.config_loader import parse_simulation_config, validate_config_against_plugins

log = logging.getLogger(__name__)


@dataclass
class RunRecord:
    run_id: str
    pid: Optional[int]
    process: Optional[Any]
    config_path: Path
    format: str
    created_at: float = field(default_factory=lambda: time.time())
    error: Optional[str] = None


class RunManager:
    """
    Verwalten von Simulation-Subprozessen, die mit 'python -m antsim --bt <tmpfile>' gestartet werden.
    - Validiert die Konfiguration gegen Plugins.
    - Speichert temporär als YAML/JSON.
    - Startet Subprozess und liefert run_id/pid.
    - Bietet Status-/Stop-Methoden.
    """

    def __init__(self, plugin_manager: PluginManager):
        self.pm = plugin_manager
        self._runs: Dict[str, RunRecord] = {}
        self._lock = threading.Lock()

    def _dump_config_file(self, config: Dict[str, Any], fmt: str = "yaml") -> Path:
        fmt = (fmt or "yaml").lower()
        if fmt not in ("yaml", "json"):
            raise ValueError("options.format must be 'yaml' or 'json'")
        if fmt == "yaml" and not _YAML_AVAILABLE:
            raise RuntimeError("PyYAML not installed; cannot write YAML. Use options.format='json' or install pyyaml.")

        suffix = ".yaml" if fmt == "yaml" else ".json"
        fd, tmp_path = tempfile.mkstemp(prefix="antsim_bt_", suffix=suffix)
        path = Path(tmp_path)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                if fmt == "yaml":
                    yaml.safe_dump(config, f, sort_keys=False)  # type: ignore
                else:
                    json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            raise RuntimeError(f"Failed to write temp config file: {e}")
        return path

    def start_run(self, simulation_config: Dict[str, Any], fmt: str = "yaml") -> Dict[str, Any]:
        """
        Validiert, speichert und startet den Subprozess. Gibt run_id und pid zurück.
        """
        # 1) Schema-Validierung
        try:
            _ = parse_simulation_config(simulation_config)
        except Exception as e:
            raise ValueError(f"Schema validation failed: {e}")

        # 2) Plugins-Validierung
        try:
            info = validate_config_against_plugins(self.pm, json.dumps(simulation_config))
        except Exception as e:
            raise RuntimeError(f"Plugin validation failed: {e}")
        if not info.get("ok"):
            missing_steps = info.get("missing_steps", [])
            missing_triggers = info.get("missing_triggers", [])
            raise ValueError(f"Config invalid: missing_steps={missing_steps}, missing_triggers={missing_triggers}")

        # 3) Datei schreiben
        cfg_path = self._dump_config_file(simulation_config, fmt)

        # 4) Subprozess starten
        cmd = [sys.executable, "-m", "antsim", "--bt", str(cfg_path)]
        env = os.environ.copy()
        # Unbuffered stdout for immediate logs (optional)
        env.setdefault("PYTHONUNBUFFERED", "1")
        try:
            import subprocess
            # Separate process group for better termination handling
            creationflags = 0
            preexec_fn = None
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            else:
                preexec_fn = os.setsid  # new session
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=None,
                stderr=None,
                stdin=None,
                creationflags=creationflags,
                preexec_fn=preexec_fn,
            )
        except Exception as e:
            try:
                cfg_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise RuntimeError(f"Failed to start subprocess: {e}")

        run_id = uuid.uuid4().hex
        rec = RunRecord(run_id=run_id, pid=proc.pid, process=proc, config_path=cfg_path, format=fmt)
        with self._lock:
            self._runs[run_id] = rec

        log.info("Started antsim run_id=%s pid=%s cfg=%s", run_id, proc.pid, cfg_path)
        return {"run_id": run_id, "pid": proc.pid, "config_path": str(cfg_path)}

    def get_status(self, run_id: str) -> Dict[str, Any]:
        with self._lock:
            rec = self._runs.get(run_id)
        if not rec:
            return {"state": "error", "error": "run_id not found"}
        proc = rec.process
        if proc is None:
            return {"state": "error", "error": rec.error or "process not available"}
        code = proc.poll()
        if code is None:
            # Running
            return {"state": "running", "pid": proc.pid}
        # Exited
        return {"state": "exited", "exit_code": int(code), "pid": proc.pid}

    def stop_run(self, run_id: str, timeout: float = 5.0) -> Dict[str, Any]:
        with self._lock:
            rec = self._runs.get(run_id)
        if not rec:
            return {"ok": False, "error": "run_id not found"}

        proc = rec.process
        if proc is None:
            return {"ok": False, "error": rec.error or "process handle missing"}

        # Already exited?
        code = proc.poll()
        if code is not None:
            return {"ok": True, "state": "exited", "exit_code": int(code), "pid": proc.pid}

        try:
            if os.name == "nt":
                # Windows: graceful terminate
                proc.terminate()
            else:
                # POSIX: send SIGTERM to the process group if set
                try:
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, signal.SIGTERM)
                except Exception:
                    proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except Exception:
                # Hard kill
                if os.name == "nt":
                    proc.kill()
                else:
                    try:
                        pgid = os.getpgid(proc.pid)
                        os.killpg(pgid, signal.SIGKILL)
                    except Exception:
                        proc.kill()
            final_code = proc.poll()
        except Exception as e:
            log.error("Error stopping run_id=%s: %s", run_id, e, exc_info=True)
            return {"ok": False, "error": str(e), "pid": proc.pid}

        return {"ok": True, "state": "exited" if final_code is not None else "running", "exit_code": final_code, "pid": proc.pid}

    def cleanup(self, run_id: str, remove_file: bool = False) -> None:
        """Optionales Aufräumen: temp-Datei löschen und RunRecord entfernen (nicht automatisch)."""
        with self._lock:
            rec = self._runs.pop(run_id, None)
        if not rec:
            return
        if remove_file:
            try:
                rec.config_path.unlink(missing_ok=True)
            except Exception:
                pass

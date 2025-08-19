# FILE: antsim/io/logging_setup.py
# antsim/io/logging_setup.py
"""
Zentrales Logging-Setup für den neuen Core.

Ziele:
- Einheitliches, konfigurierbares Logging für alle antsim-Komponenten.
- Strukturierte Ausgabe (Key-Value oder JSON-Lines) für gute Nachvollziehbarkeit.
- Idempotent: Mehrfacher Aufruf erzeugt keine doppelten Handler.
- Feingranulare Level-Steuerung je Namensraum (core/behavior/plugins/registry).

Hinweise:
- Dieses Modul verändert keine globalen Logger automatisch. setup_logging(...)
  muss von der Anwendung aufgerufen werden (z. B. in antsim/app/main.py).
- Formatierung ist bewusst leichtgewichtig, um externe Abhängigkeiten zu vermeiden.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Union


_DEFAULT_FMT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%dT%H:%M:%S"


class KVFormatter(logging.Formatter):
    """Key-Value-Formatter mit optionalen Extra-Feldern."""
    def __init__(self, base: str = _DEFAULT_FMT, datefmt: Optional[str] = _DEFAULT_DATEFMT):
        super().__init__(base, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        # Sammle interessante extra-Felder falls vorhanden
        extras = {}
        for k, v in record.__dict__.items():
            if k in ("args", "msg", "levelname", "levelno", "name", "pathname",
                     "filename", "module", "exc_info", "exc_text", "stack_info",
                     "lineno", "funcName", "created", "msecs", "relativeCreated",
                     "thread", "threadName", "processName", "process"):
                continue
            # Ausgewählte Extras aufnehmen
            if k in ("individual_id", "class", "function", "tick", "worker_id"):
                extras[k] = v
        if extras:
            return f"{msg} extras={extras}"
        return msg


class JSONFormatter(logging.Formatter):
    """JSON-Lines Formatter mit Basisfeldern und erkannten Extras."""
    def __init__(self, datefmt: Optional[str] = _DEFAULT_DATEFMT):
        super().__init__(datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": self.formatTime(record, self.datefmt),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # Zusätzliche kontextuelle Felder
        if hasattr(record, "individual_id"):
            data["individual_id"] = getattr(record, "individual_id")
        if hasattr(record, "class"):
            data["class"] = getattr(record, "class")
        if hasattr(record, "function"):
            data["function"] = getattr(record, "function")
        if hasattr(record, "tick"):
            data["tick"] = getattr(record, "tick")
        if hasattr(record, "worker_id"):
            data["worker_id"] = getattr(record, "worker_id")

        # Exception-Infos wenn vorhanden
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(data, ensure_ascii=False)


def _root_logger() -> logging.Logger:
    return logging.getLogger()


def _remove_handlers(logger: logging.Logger) -> None:
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.handlers = []


def setup_logging(
    level: int = logging.INFO,
    json_lines: bool = False,
    stream: Optional[object] = None,
    include_library_logs: bool = False,
) -> None:
    """
    Konfiguriert zentrales Logging idempotent.

    Args:
      level: Root-Level (INFO/DEBUG/...)
      json_lines: Wenn True, JSON-Lines; sonst Key-Value-Format.
      stream: Ziel-Stream (Default: sys.stdout)
      include_library_logs: Wenn True, dämpfe keine Drittlogger.

    Effekte:
      - Setzt Level auf antsim-Logger-Hierarchie (core/behavior/plugins/registry/io).
      - Entfernt vorherige Handler und installiert einen neuen StreamHandler.
      - Markiert Root-Logger, um Doppelkonfiguration zu vermeiden.
    """
    root = _root_logger()
    already_configured = getattr(root, "_antsim_logging_configured", False)

    # Immer abräumen und neu setzen, aber nur einmal pro Prozess-Lebensdauer markieren
    _remove_handlers(root)

    handler = logging.StreamHandler(stream or sys.stdout)
    if json_lines:
        formatter = JSONFormatter()
    else:
        formatter = KVFormatter(_DEFAULT_FMT, _DEFAULT_DATEFMT)
    handler.setFormatter(formatter)
    handler.setLevel(level)

    root.addHandler(handler)
    root.setLevel(level)

    # Setze spezifische Level für unsere Namensräume (erstmal gleich dem Root-Level)
    for name in (
        "antsim", "antsim.core", "antsim.behavior", "antsim.plugins",
        "antsim.registry", "antsim.io", "antsim.app",
    ):
        logging.getLogger(name).setLevel(level)

    # Drittanbieter-Libraries ggf. dämpfen
    if not include_library_logs:
        for lib in ("pluggy", "urllib3", "matplotlib", "PIL", "numba", "numpy"):
            logging.getLogger(lib).setLevel(max(level, logging.WARNING))

    if not already_configured:
        setattr(root, "_antsim_logging_configured", True)


def set_namespace_levels(levels: Dict[str, Union[int, str]]) -> None:
    """
    Setzt Level pro Logger-Namespace.

    Args:
      levels: Mapping z. B. {"antsim.behavior": "DEBUG", "antsim.core.executor": logging.INFO}
    """
    for name, lvl in levels.items():
        if isinstance(lvl, str):
            lvl = getattr(logging, lvl.upper(), logging.INFO)
        logging.getLogger(name).setLevel(int(lvl))


def add_file_handler(
    path: Union[str, Path],
    level: int = logging.INFO,
    json_lines: bool = True,
    mode: str = "a",
) -> logging.Handler:
    """
    Ergänzt einen File-Handler (z. B. für Langläufer/Produktion).

    Args:
      path: Dateipfad
      level: Level für Handler
      json_lines: JSON-Lines statt Text
      mode: Dateimodus

    Returns:
      Der hinzugefügte Handler (kann später entfernt werden).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    fh = logging.FileHandler(str(p), mode=mode, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(JSONFormatter() if json_lines else KVFormatter())
    logging.getLogger().addHandler(fh)
    return fh


def silence(logger_names: Optional[list[str]] = None) -> None:
    """Unterdrückt ausgewählte Logger vollständig (Level=CRITICAL+1)."""
    if not logger_names:
        return
    for name in logger_names:
        logging.getLogger(name).setLevel(logging.CRITICAL + 1)


def get_logger(name: str) -> logging.Logger:
    """Bequemer Zugriff für Konsumenten; nutzt Root-Konfiguration."""
    return logging.getLogger(name)

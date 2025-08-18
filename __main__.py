# FILE: antsim/__main__.py
"""
antsim.__main__: Paketweiter Entry-Point für den neuen Core (Cutover, Step 11).

- Startet ausschließlich den neuen Core-Einstieg antsim.app.main.main().
- Führt einen optionalen Cutover-Check durch und warnt, wenn Legacy-Module im Pfad
  auffindbar sind (ohne sie zu importieren). In Strict-Mode (ANTSIM_STRICT_CUTOVER=1)
  wird bei erkannter Legacy-Präsenz abgebrochen.
- Liefert einen knappen Migrationshinweis (Nutzung von --bt <YAML/JSON> bzw. ANTSIM_BT).

Hinweis:
- Keine Berührung des Legacy-Codes; rein im neuen Namespace.
- Logging-Konfiguration erfolgt innerhalb von antsim.app.main (vereinheitlicht).
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from typing import List

log = logging.getLogger(__name__)


def _detect_legacy_presence(names: List[str]) -> List[str]:
    """Best-effort Detection: Prüft, ob Legacy-Modulnamen im Importpfad auffindbar wären (ohne Import)."""
    present = []
    for n in names:
        try:
            if importlib.util.find_spec(n) is not None:
                present.append(n)
        except Exception:
            # Fehler bei find_spec ignorieren; konservativ keine Präsenz melden
            pass
    return present


def _cutover_check() -> None:
    """
    Warnung/Abbruch, falls typische Legacy-Startpunkte im Pfad auffindbar sind.
    Strict-Mode via ANTSIM_STRICT_CUTOVER=1.
    """
    strict = os.environ.get("ANTSIM_STRICT_CUTOVER", "0") in ("1", "true", "TRUE", "yes", "YES")
    legacy_candidates = [
        # häufige Legacy-Dateien/Namen aus dem alten Start
        "main", "simulation", "environment", "entities",
        "sensor_manager", "scheduler", "function_registry", "steps", "config_manager", "decorators",
    ]
    found = _detect_legacy_presence(legacy_candidates)
    if found:
        msg = f"Legacy modules detectable in sys.path (not imported): {sorted(found)}"
        if strict:
            raise RuntimeError(f"CUTOVER STRICT: {msg}. Remove legacy paths/packages before running antsim.")
        # Warnung ausgeben, aber Start erlauben
        try:
            # Einfache, robuste Log-Ausgabe ohne globales Setup zu erzwingen
            logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        except Exception:
            pass
        log.warning("CUTOVER WARNING: %s", msg)
        log.info("Migration hint: Use the new entry point. Provide a BT config via '--bt <path>' or ANTSIM_BT env.")


def main() -> None:
    """
    Paketweiter Einstieg:
    - Enforce-Cutover-Check
    - Delegation an antsim.app.main.main()
    """
    _cutover_check()
    # Delegiere an den neuen Core-Start
    from antsim.app.main import main as new_main
    new_main()


if __name__ == "__main__":
    main()

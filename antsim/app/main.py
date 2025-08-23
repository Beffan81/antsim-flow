# FILE: antsim/app/main.py
# antsim/app/main.py
"""Minimaler Entry-Point für den neuen Core.

Startet einen Demo-Run:
- PluginManager (dev_mode) lädt neue Plugins
- Worker + minimalistische Environment
- Behavior Tree wird aus validierter Konfiguration (Pydantic) via config_loader gebaut
  NEU: Optionales Laden der BT-Konfiguration aus YAML/JSON-Datei (ENV/CLI)
- BehaviorEngine führt Ticks aus: pre-sensors -> bt.tick (Intents) -> apply_intents -> post-sensors
- PheromoneField (Double-Buffer) wird pro Tick aktualisiert; Deposits aus Executor werden erfasst.
- NEU (Step 10): Pygame-Renderer nutzt ausschließlich neue Core-Daten (Environment/Grid/Pheromone/Agents)
  und rendert pro Tick (keine Legacy-Anteile)

Logging fokussiert Trigger-/Sensorentscheidungen, Step-Resultate, Executor-Ausführung und Pheromon-Summary.
Nutzt zentrales Logging-Setup aus antsim/io/logging_setup.py (vereinheitlicht, Level steuerbar).
Erweitert: Konfiguration des EventLogger (strukturierte Ereignisse, Auto-Flush), konsistentes Tick-Flush.
"""

import logging
import os
import sys
import time
from typing import Any, Dict, Optional, List, Tuple

from ..registry.manager import PluginManager
from ..behavior.bt import BehaviorEngine
from ..core.worker import Worker
from ..core.queen import Queen
from ..core.agents import AgentFactory
from ..io.config_loader import load_behavior_tree
from ..core.engine.pheromones import PheromoneField  # Double-Buffer Engine
from ..io.logging_setup import setup_logging, set_namespace_levels
from ..io.event_logger import configure_event_logger, get_event_logger
from .renderer import Renderer  # NEU: Renderer-Integration (Step 10)


# ----------------- Minimal Environment -----------------

class _Cell:
    """Kleine Zelle mit Typ, optionaler Nahrung, Pheromonen und optionaler Belegung (ant)."""
    __slots__ = ("x", "y", "cell_type", "food", "pheromone_level", "pheromones", "_owner", "ant")

    def __init__(self, x: int, y: int, owner: Optional["DemoEnvironment"] = None, cell_type: str = "empty"):
        self.x = x
        self.y = y
        self.cell_type = cell_type
        self.food = None
        self.pheromone_level = 0
        # Freiform-Container für einfache Demos (Legacy-kompatible Ansicht)
        self.pheromones: Dict[str, int] = {}
        # Back-Reference zur Environment, um PheromoneField-Deposits mitzunehmen
        self._owner = owner
        # Zellenbelegung für Kollisionserkennung / Sensoren
        self.ant = None  # vom Executor gesetzt/geräumt

    def add_pheromone(self, pheromone_type: str, strength: int) -> None:
        """Zell-lokale Pheromonablage; spiegelt zusätzlich in PheromoneField (falls vorhanden)."""
        if pheromone_type not in self.pheromones:
            self.pheromones[pheromone_type] = 0
        self.pheromones[pheromone_type] += int(strength)
        # Legacy-Feld für einfache Renderer: Summiere generisch
        self.pheromone_level += int(strength)
        # Neues System: Double-Buffer Field befüllen (staging)
        env = self._owner
        if env and hasattr(env, "pheromones") and isinstance(env.pheromones, PheromoneField):
            env.pheromones.deposit(pheromone_type, self.x, self.y, float(strength))


class DemoEnvironment:
    """Minimal-Environment für Sensor-/Trigger-/Pheromon-Demo."""
    def __init__(self, width: int = 20, height: int = 20, entries: Optional[List[Tuple[int, int]]] = None):
        self.width = width
        self.height = height
        self.grid: List[List[_Cell]] = [[_Cell(x, y, owner=self) for x in range(width)] for y in range(height)]
        self.entry_positions: List[Tuple[int, int]] = entries or [(1, 1)]
        for ex, ey in self.entry_positions:
            self.grid[ey][ex].cell_type = "e"  # Eingang
        # Nest-Kern (ein paar Zellen) zur Demonstration
        for ny in range(2, 5):
            for nx in range(2, 5):
                self.grid[ny][nx].cell_type = "nest"
        self.cycle_count = 0

        # Double-Buffer Pheromon-Engine mit sinnvollen Defaults
        self.pheromones = PheromoneField(
            width=self.width,
            height=self.height,
            types=["food", "hunger", "nest", "brood"],
            evaporation=0.02,
            alpha=0.12,
            allow_dynamic_types=True,
        )

    def get_ant_at_position(self, x: int, y: int):
        """Liefert die Ameise an einer Position; unterstützt Executor-Kollisionserkennung/Sensoren."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x].ant
        return None

    def pheromones_tick(self) -> Dict[str, Dict[str, float]]:
        """Diffusion + Verdunstung + Swap; liefert kompakte Summary."""
        return self.pheromones.update_and_swap()


# ----------------- Demo Runner -----------------

def build_demo_colony() -> Tuple[List[Queen], List[Worker]]:
    """Erstellt eine Kolonie mit 1 Königin und 2 Arbeiterinnen."""
    factory = AgentFactory()
    
    # Entry positions for the colony
    entry_positions = [(1, 1), (1, 2), (2, 1)]
    
    # Create initial colony: 1 queen + 2 workers
    queens, workers = factory.create_initial_colony(
        entry_positions=entry_positions,
        queen_count=1,
        worker_count=2
    )
    
    return queens, workers


# Minimaler BT als Fallback (JSON-String)
BT_CONFIG_JSON = """
{
  "behavior_tree": {
    "root": {
      "type": "selector",
      "name": "Root",
      "children": [
        {
          "type": "sequence",
          "name": "CollectOutside",
          "children": [
            {
              "type": "condition",
              "name": "GateCollect",
              "condition": {
                "triggers": ["social_hungry", "not_in_nest"],
                "logic": "AND"
              }
            },
            {
              "type": "step",
              "name": "Move",
              "step": {
                "name": "example_move",
                "params": {}
              }
            }
          ]
        },
        {
          "type": "step",
          "name": "Idle",
          "step": {
            "name": "example_wait",
            "params": {}
          }
        }
      ]
    }
  }
}
""".strip()


def _resolve_bt_source(argv: List[str]) -> Optional[str]:
    """
    Ermittelt optionalen Pfad zur BT-Konfiguration.
    Priorität:
      1) CLI: --bt <path>
      2) ENV: ANTSIM_BT=<path>
      3) None -> interner Fallback (BT_CONFIG_JSON)
    """
    # CLI
    if "--bt" in argv:
        try:
            idx = argv.index("--bt")
            return argv[idx + 1]
        except Exception:
            logging.getLogger(__name__).error("--bt angegeben aber kein Pfad übergeben")
            sys.exit(2)
    # ENV
    env_path = os.environ.get("ANTSIM_BT")
    if env_path:
        return env_path
    return None


def _load_bt_root(pm: PluginManager, argv: List[str]):
    """
    Lädt den Behavior Tree Root:
      - aus Datei (YAML/JSON) falls angegeben (CLI/ENV),
      - sonst aus der eingebauten JSON-Fallback-Config.
    Liefert den Root-Knoten oder beendet mit Fehler bei ungültiger externen Config.
    """
    log = logging.getLogger(__name__)
    cfg_path = _resolve_bt_source(argv)
    if cfg_path:
        log.info("Lade Behavior Tree aus Datei: %s", cfg_path)
        try:
            root = load_behavior_tree(pm, cfg_path)
            log.info("Behavior Tree erfolgreich geladen (extern)")
            return root
        except Exception as e:
            log.error("Fehler beim Laden/Validieren der BT-Konfiguration '%s': %s", cfg_path, e, exc_info=True)
            sys.exit(3)
    # Fallback: eingebauter Minimal-Tree
    log.info("Keine externe BT-Konfiguration angegeben; nutze Fallback")
    return load_behavior_tree(pm, BT_CONFIG_JSON)


def run_demo(ticks: int = 100) -> None:
    """Führt eine kurze Demo der neuen Pipeline aus (BT aus validierter Config) und rendert mit dem neuen Renderer."""
    log = logging.getLogger(__name__)
    log.info("=== Neue Core-Demo startet ===")

    # 1) Plugins laden
    pm = PluginManager(dev_mode=True)
    pm.discover_and_register()
    log.info("Plugins geladen: steps=%s triggers=%s sensors=%s",
             pm.list_steps(), pm.list_triggers(), pm.list_sensors())

    # 2) Environment + Colony (1 Queen + 2 Workers)
    env = DemoEnvironment()
    queens, workers = build_demo_colony()
    
    # Set queen reference in environment for queen_steps to work
    env.queen = queens[0] if queens else None
    
    # Get all agents for processing
    all_agents = queens + workers
    
    # WICHTIG: Startbelegung im Grid setzen, damit Kollisionserkennung/Sensoren korrekt arbeiten
    for agent in all_agents:
        try:
            x, y = agent.position
            if 0 <= x < env.width and 0 <= y < env.height:
                env.grid[y][x].ant = agent
                log.debug("initial_occupancy_set agent=%s type=%s pos=%s", 
                         agent.id, type(agent).__name__, agent.position)
        except Exception as e:
            log.warning("could_not_set_initial_occupancy agent=%s err=%s", 
                       getattr(agent, 'id', 'unknown'), e)

    # 3) BT aus Config bauen (validiert Step-/Trigger-Namen)
    root = _load_bt_root(pm, sys.argv)
    log.info("Behavior Tree erfolgreich aus Config geladen und gebaut")

    # 4) Engine + Renderer
    engine = BehaviorEngine(pm, root)
    renderer = Renderer(cell_size=24, show_grid=False, show_pheromones=True)
    # Fenster initialisieren (tolerant, wenn pygame fehlt)
    log.info("Initialisiere Pygame-Fenster...")
    renderer.init_window(env.width, env.height, dashboard_width=0, title="antsim new core")
    
    # Check if renderer actually initialized properly
    if not hasattr(renderer, '_screen') or renderer._screen is None:
        log.warning("Pygame window failed to initialize - simulation will run without display")
        log.warning("This is common in containerized environments without display support")
        log.info("To run headless: export SDL_VIDEODRIVER=dummy")
        log.info("To enable X11 forwarding: export DISPLAY=:0 (and ensure X11 forwarding is set up)")
    else:
        log.info("Pygame-Fenster erfolgreich erstellt, starte Simulation")

    # 5) Tick-Schleife mit konfigurierbarer Geschwindigkeit
    # Optional: Pygame-Events verarbeiten, wenn verfügbar
    try:
        import pygame  # type: ignore
        _HAS_PYGAME = True
    except Exception:
        _HAS_PYGAME = False
    
    # Konfigurierbare Delays aus Environment-Variablen
    tick_delay = float(os.environ.get("ANTSIM_TICK_DELAY", "1.0"))
    window_hold = float(os.environ.get("ANTSIM_WINDOW_HOLD", "5.0"))
    log.info("Simulation läuft mit tick_delay=%.2fs, window_hold=%.2fs", tick_delay, window_hold)

    for t in range(1, ticks + 1):
        env.cycle_count = t
        log.info("---- TICK %d ---- (Colony: %d queens, %d workers)", 
                t, len(queens), len(workers))

        # BT-Tick for all agents (queens and workers)
        results = []
        for agent in all_agents:
            if hasattr(engine, 'tick_worker'):
                result = engine.tick_worker(agent, env)
            else:
                # Fallback for older engine versions
                result = engine.tick(agent, env)
            results.append((agent.id, type(agent).__name__, result))
        
        # Queen egg laying logic
        for queen in queens:
            if queen.can_lay_egg(t):
                queen.lay_egg(t)

        # Pheromon-Engine aktualisieren (Diffusion/Verdunstung/Swap einmal pro Tick)
        ph_summary = env.pheromones_tick()
        if ph_summary:
            log.info("pheromones_tick_summary tick=%d types=%d", t, len(ph_summary))

        # Rendering (nutzt ausschließlich neue Core-Daten)
        info_overlay = {
            "tick": t, 
            "queens": len(queens),
            "workers": len(workers),
            "results": results
        }
        try:
            renderer.draw(
                environment=env, 
                ants=workers,  # Workers as ants 
                queen=queens[0] if queens else None,  # First queen
                brood=[], 
                info=info_overlay
            )
            renderer.flip()
        except Exception as render_err:
            log.debug("Rendering failed (tick %d): %s - continuing simulation", t, render_err)

        # Events verarbeiten (nur falls pygame verfügbar und renderer initialized)
        if _HAS_PYGAME and hasattr(renderer, '_screen') and renderer._screen is not None:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        log.info("QUIT event received, aborting demo loop")
                        raise KeyboardInterrupt()
            except Exception as event_err:
                # Defensive: Rendering/Events dürfen die Demo nicht crashen
                log.debug("Event processing failed (tick %d): %s", t, event_err)

        # Zusammenfassung relevanter BB-Fakten für alle Agenten
        summary_keys = [
            "position", "in_nest", "at_entry", "food_detected", "food_position",
            "individual_stomach", "individual_hungry",
            "social_stomach", "social_hungry", "has_moved"
        ]
        
        # Log each agent's state
        for agent in all_agents:
            bb = agent.blackboard
            snapshot = {k: bb.get(k) for k in summary_keys}
            agent_type = type(agent).__name__
            log.info("Tick %d %s[%d] BB-Snapshot=%s", t, agent_type, agent.id, snapshot)
        
        # Log overall results
        log.info("Tick %d Results=%s", t, results)

        # Ereignisse pro Tick zuverlässig flushen (EventLogger ist threadsicher)
        try:
            get_event_logger().flush()
        except Exception:
            pass
        
        # Simulation verlangsamen für bessere Beobachtbarkeit
        if tick_delay > 0:
            time.sleep(tick_delay)

    log.info("=== Demo abgeschlossen ===")
    
    # Fenster offen halten für bessere Beobachtbarkeit (nur wenn display verfügbar)
    if window_hold > 0 and _HAS_PYGAME and hasattr(renderer, '_screen') and renderer._screen is not None:
        log.info("Halte Fenster für %.1f Sekunden offen (ESC oder Fenster schließen zum Beenden)", window_hold)
        start_time = time.time()
        while time.time() - start_time < window_hold:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        log.info("Vorzeitiges Beenden durch Benutzer")
                        break
                else:
                    time.sleep(0.1)  # Kurze Pause um CPU zu schonen
                    continue
                break  # Aus der while-Schleife wenn break aus for-Schleife
            except Exception:
                # Defensive: Events dürfen nicht crashen
                time.sleep(0.1)
    elif window_hold > 0:
        log.info("Halte Simulation für %.1f Sekunden am Leben (kein Display verfügbar)", window_hold)
        time.sleep(window_hold)
    
    # Abschließender Flush
    try:
        get_event_logger().flush()
    except Exception:
        pass
    # Fenster schließen (tolerant)
    try:
        renderer.close()
    except Exception:
        pass


def _parse_log_env_defaults() -> tuple[int, bool]:
    """
    Liest LOG-Umgebungsvariablen für Demo:
      ANTSIM_LOG_LEVEL: DEBUG/INFO/WARNING/ERROR (Default: INFO)
      ANTSIM_LOG_JSON: 1/0 (Default: 0)
    """
    level_name = os.environ.get("ANTSIM_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    json_lines = os.environ.get("ANTSIM_LOG_JSON", "0") in ("1", "true", "TRUE", "yes", "YES")
    return level, json_lines


def main():
    """CLI-Einstieg für die neue Pipeline-Demo mit zentralem Logging."""
    level, json_lines = _parse_log_env_defaults()
    setup_logging(level=level, json_lines=json_lines)
    # Create logger instance after setup
    log = logging.getLogger(__name__)
    
    # Optional: spezifische Level anpassen (Beispiel)
    set_namespace_levels({
        "antsim.behavior": level,
        "antsim.core.executor": "INFO",
        "antsim.plugins": level,
        "antsim.io.event_logger": "INFO",
        "antsim.core.sensors_runner": "INFO",
    })

    # Strukturierte Event-Logs konfigurieren:
    # - Flush relativ zeitnah (alle 50 Events oder pro Tick manuell)
    # - Alle Event-Typen aktiv lassen (Default)
    # - großer Buffer für längere Runs
    configure_event_logger(
        buffer_size=5000,
        auto_flush_interval=50,
        enabled_types=None  # None = alle EventType
    )

    # Konfigurierbare Tick-Anzahl aus Environment-Variable
    ticks = int(os.environ.get("ANTSIM_TICKS", "10000"))
    log.info("Simulation startet mit %d Ticks (konfigurierbar via ANTSIM_TICKS)", ticks)
    run_demo(ticks=ticks)


if __name__ == "__main__":
    main()

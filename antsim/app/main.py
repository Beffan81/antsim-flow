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
from ..behavior.queen_behavior import build_queen_behavior_tree
from ..core.worker import Worker
from ..core.queen import Queen
from ..core.agents import AgentFactory
from ..core.environment import Environment
from ..core.nest_builder import NestBuilder
from ..io.config_loader import load_behavior_tree, load_simulation_config
from ..core.engine.pheromones import PheromoneField  # Double-Buffer Engine
from ..io.logging_setup import setup_logging, set_namespace_levels
from ..io.event_logger import configure_event_logger, get_event_logger
from .renderer import Renderer  # NEU: Renderer-Integration (Step 10)


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


def _load_simulation_config(pm: PluginManager, argv: List[str]):
    """
    Lädt die vollständige Simulation-Konfiguration:
      - aus Datei (YAML/JSON) falls angegeben (CLI/ENV),
      - sonst aus der eingebauten JSON-Fallback-Config.
    Liefert (root_node, simulation_config) oder beendet mit Fehler bei ungültiger externen Config.
    """
    log = logging.getLogger(__name__)
    cfg_path = _resolve_bt_source(argv)
    if cfg_path:
        log.info("Lade Simulation-Konfiguration aus Datei: %s", cfg_path)
        try:
            root, sim_config = load_simulation_config(pm, cfg_path)
            log.info("Simulation-Konfiguration erfolgreich geladen (extern)")
            return root, sim_config
        except Exception as e:
            log.error("Fehler beim Laden/Validieren der Simulation-Konfiguration '%s': %s", cfg_path, e, exc_info=True)
            sys.exit(3)
    # Fallback: eingebauter Minimal-Tree
    log.info("Keine externe Simulation-Konfiguration angegeben; nutze Fallback")
    root = load_behavior_tree(pm, BT_CONFIG_JSON)
    return root, None


def initialize_food_sources(env: Environment, sim_config) -> None:
    """Initialisiert Futterquellen basierend auf der Konfiguration."""
    log = logging.getLogger(__name__)
    
    if not sim_config or not sim_config.food_sources:
        # Standard-Futterquellen wenn keine Konfiguration vorhanden
        default_sources = [
            (5, 5, 200),
            (35, 25, 150), 
            (20, 5, 100)
        ]
        for x, y, amount in default_sources:
            # Prüfe ob Position innerhalb der Environment-Grenzen liegt
            if 0 <= x < env.width and 0 <= y < env.height:
                env.add_food(x, y, amount)
                log.info("Standard-Futterquelle hinzugefügt: pos=(%d,%d) amount=%d", x, y, amount)
        return
    
    # Futterquellen aus Konfiguration
    count = 0
    for food_config in sim_config.food_sources:
        x, y = food_config.position
        amount = food_config.amount
        
        # Validiere Position
        if not (0 <= x < env.width and 0 <= y < env.height):
            log.warning("Futterquelle ignoriert (außerhalb der Grenzen): pos=(%d,%d)", x, y)
            continue
            
        env.add_food(x, y, amount)
        count += 1
        log.info("Futterquelle hinzugefügt: pos=(%d,%d) amount=%d", x, y, amount)
    
    log.info("Futterquellen-Initialisierung abgeschlossen: %d Quellen hinzugefügt", count)


def collect_dashboard_data(env: Environment, queens: List[Queen], workers: List[Worker]) -> Dict[str, Any]:
    """Collect all data needed for the dashboard display."""
    # Calculate total food sources in environment
    total_food_sources = 0
    for y in range(env.height):
        for x in range(env.width):
            cell = env.grid[y][x]
            if cell.food is not None:
                total_food_sources += getattr(cell.food, 'amount', 0)
    
    # Calculate total social food across all workers
    total_social_food = sum(
        worker.blackboard.get('social_stomach', 0) for worker in workers
    )
    
    # Get queen data (first queen)
    queen_data = {}
    if queens:
        queen = queens[0]
        queen_data = {
            'energy': queen.blackboard.get('energy', 0),
            'max_energy': queen.blackboard.get('max_energy', 100),
            'individual_stomach': queen.blackboard.get('individual_stomach', 0),
            'stomach_capacity': queen.blackboard.get('stomach_capacity', 50)
        }
    
    # Get top 5 workers by ID
    sorted_workers = sorted(workers, key=lambda w: w.id)[:5]
    top_workers = []
    for worker in sorted_workers:
        worker_data = {
            'id': worker.id,
            'energy': worker.blackboard.get('energy', 0),
            'max_energy': worker.blackboard.get('max_energy', 100),
            'individual_stomach': worker.blackboard.get('individual_stomach', 0),
            'social_stomach': worker.blackboard.get('social_stomach', 0),
            'current_step': worker.blackboard.get('current_step', 'idle')
        }
        top_workers.append(worker_data)
    
    return {
        'total_food_sources': total_food_sources,
        'total_social_food': total_social_food,
        'ant_count': len(workers),
        'brood_count': len(env.brood_registry),
        'queen': queen_data,
        'top_workers': top_workers
    }


def run_demo(ticks: int = 100) -> None:
    """Führt eine kurze Demo der neuen Pipeline aus (BT aus validierter Config) und rendert mit dem neuen Renderer."""
    log = logging.getLogger(__name__)
    log.info("=== Neue Core-Demo startet ===")

    # 1) Plugins laden
    pm = PluginManager(dev_mode=True)
    pm.discover_and_register()
    log.info("Plugins geladen: steps=%s triggers=%s sensors=%s",
             pm.list_steps(), pm.list_triggers(), pm.list_sensors())

    # 2) Environment mit Standard-Nest erstellen
    env = Environment(width=40, height=30)
    
    # Nest-Layout erstellen
    nest_builder = NestBuilder()
    entry_x, entry_y = nest_builder.build_standard_nest(env, center=True)
    log.info("Standard nest built with entry at (%d, %d)", entry_x, entry_y)
    
    # 3) Colony (1 Queen + 2 Workers) mit korrekter Positionierung
    queens, workers = build_demo_colony()
    
    # Queen im Nest-Zentrum platzieren
    nest_center = nest_builder.get_nest_center(env.width, env.height)
    queens[0].position = nest_center
    
    # Workers nahe der Entry platzieren
    worker_positions = [(entry_x, entry_y + 1), (entry_x + 1, entry_y + 1)]
    for i, worker in enumerate(workers):
        if i < len(worker_positions):
            worker.position = worker_positions[i]
    
    # Set queen reference in environment for queen_steps to work
    env.queen = queens[0] if queens else None
    
    # Get all agents for processing
    all_agents = queens + workers
    
    # WICHTIG: Agents in Environment registrieren für korrekte Kollisionserkennung/Sensoren
    for agent in all_agents:
        try:
            env.add_ant(agent)
            log.debug("Agent registered: id=%s type=%s pos=%s", 
                     agent.id, type(agent).__name__, agent.position)
        except Exception as e:
            log.warning("Could not register agent id=%s: %s", 
                       getattr(agent, 'id', 'unknown'), e)

    # 3) BT aus Config bauen (validiert Step-/Trigger-Namen) und Futterquellen initialisieren
    worker_root, sim_config = _load_simulation_config(pm, sys.argv)
    log.info("Worker Behavior Tree erfolgreich aus Config geladen und gebaut")
    
    # Build separate queen behavior tree
    queen_root = build_queen_behavior_tree(pm)
    log.info("Queen Behavior Tree erfolgreich erstellt (hart-codiert)")
    
    # Futterquellen initialisieren
    initialize_food_sources(env, sim_config)

    # 4) Engine + Renderer - with separate trees for queen and workers
    engine = BehaviorEngine(pm, worker_root, queen_root)
    renderer = Renderer(cell_size=24, show_grid=False, show_pheromones=True)
    # Fenster initialisieren mit Dashboard (300px breit)
    log.info("Initialisiere Pygame-Fenster mit Dashboard...")
    renderer.init_window(env.width, env.height, dashboard_width=300, title="antsim new core")
    
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

        # BT-Tick for all agents (queens and workers) - using new tick_agent method
        results = []
        for agent in all_agents:
            result = engine.tick_agent(agent, env)
            agent_type = "Queen" if hasattr(agent, 'egg_laying_interval') else "Worker"
            results.append((agent.id, agent_type, result))
        
        # Process queen energy and egg laying lifecycle
        for queen in queens:
            # Process energy conversion and hunger signaling
            energy_result = queen.process_energy_cycle(t)
            if not energy_result['is_alive']:
                log.warning("Queen %s died at tick %d", queen.id, t)
                queens.remove(queen)
                env.remove_ant(queen.id)
                continue
            
            # Handle queen's pheromone intents from energy processing
            if energy_result.get('intents'):
                for intent in energy_result['intents']:
                    if hasattr(intent, 'ptype') and intent.ptype == "hunger":
                        # Deposit hunger pheromone at queen's position
                        qx, qy = queen.position
                        if hasattr(env, 'grid') and 0 <= qx < env.width and 0 <= qy < env.height:
                            env.grid[qy][qx].add_pheromone("hunger", intent.strength)
            
            # Egg laying if conditions are met (100% energy required)
            if queen.can_lay_egg(t):
                success = queen.lay_egg(t)
                if success:
                    # Create new brood at queen's position
                    from antsim.core.brood import Brood
                    brood_id = len(env.brood_registry) + 1000  # Offset brood IDs
                    brood_config = {
                        'initial_energy': 50,
                        'max_energy': 100,
                        'maturation_time': 30,  # Shorter for demo
                        'energy_conversion_rate': 5,
                        'energy_loss_rate': 2,
                        'hunger_pheromone_strength': 2
                    }
                    new_brood = Brood(brood_id, queen.position, brood_config)
                    new_brood.blackboard.set('created_tick', t)
                    env.add_brood(new_brood)
                    log.info("Queen %s laid egg -> Brood %s at tick %d", queen.id, brood_id, t)
        
        # Process brood lifecycle
        brood_to_remove = []
        brood_to_mature = []
        
        for brood in list(env.brood_registry.values()):
            # Process brood energy cycle
            energy_result = brood.process_energy_cycle(t)
            if not energy_result['is_alive']:
                log.info("Brood %s died at tick %d", brood.id, t)
                brood_to_remove.append(brood.id)
                continue
            
            # Handle brood's pheromone intents from energy processing
            if energy_result.get('intents'):
                for intent in energy_result['intents']:
                    if hasattr(intent, 'ptype') and intent.ptype == "hunger":
                        # Deposit hunger pheromone at brood's position
                        bx, by = brood.position
                        if hasattr(env, 'grid') and 0 <= bx < env.width and 0 <= by < env.height:
                            env.grid[by][bx].add_pheromone("hunger", intent.strength)
            
            # Growth if at full energy
            if brood.can_grow():
                brood.grow(t)
            
            # Check for maturation
            if brood.can_mature(t):
                brood_to_mature.append(brood)
        
        # Remove dead brood
        for brood_id in brood_to_remove:
            env.remove_brood(brood_id)
        
        # Mature brood into workers
        for brood in brood_to_mature:
            from antsim.core.agents import Agent  # Import worker class
            worker_id = len(env.ant_registry) + 2000  # Offset worker IDs
            worker_config = {
                'energy': 100,
                'max_energy': 100,
                'stomach_capacity': 100,
                'social_stomach_capacity': 100,
                'hunger_threshold': 50
            }
            new_worker = Agent(worker_id, brood.position, worker_config)
            
            # Add to environment and workers list
            env.add_ant(new_worker)
            workers.append(new_worker)
            all_agents.append(new_worker)
            
            # Remove brood
            env.remove_brood(brood.id)
            log.info("Brood %s matured into Worker %s at tick %d", brood.id, worker_id, t)

        # Pheromon-Engine aktualisieren (Diffusion/Verdunstung/Swap einmal pro Tick)
        ph_summary = env.pheromones_tick()
        if ph_summary:
            log.info("pheromones_tick_summary tick=%d types=%d", t, len(ph_summary))

        # Collect dashboard data for real-time display
        dashboard_data = collect_dashboard_data(env, queens, workers)
        
        # Rendering (nutzt ausschließlich neue Core-Daten)
        info_overlay = {
            "tick": t, 
            "queens": len(queens),
            "workers": len(workers),
            "brood": len(env.brood_registry),
            "results": results,
            "nest_center": nest_center,
            "entry": (entry_x, entry_y),
            "dashboard": dashboard_data
        }
        try:
            renderer.draw(
                environment=env, 
                ants=workers,  # Workers as ants 
                queen=queens[0] if queens else None,  # First queen
                brood=list(env.brood_registry.values()),  # Pass brood list
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

# FILE: antsim/core/environment.py
"""
Leichte Core-Environment für den neuen Namespace.

Ziele:
- Minimaler, generischer Environment-Typ ohne Legacy-Abhängigkeiten.
- Grid mit Zellen (Cell), besetzbar durch Agents (z. B. Worker).
- Unterstützt Entry-Positionen, Pheromon-Engine (Double-Buffer) und einfache Lookup-APIs.
- Kompatibel mit Sensoren/Executor: get_ant_at_position, get_ant_by_id, width/height, grid[][].

Hinweise:
- Rein im neuen Namespace; keine Shims/Brücken zum Legacy-Code.
- Logging fokussiert Zustandsänderungen (Ant-Registrierung, Pheromon-Tick).
- Idempotent: Mehrfaches Registrieren derselben Ant-Instanz wird abgefangen.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .engine.pheromones import PheromoneField

log = logging.getLogger(__name__)


@dataclass
class Cell:
    """Gitterzelle mit Typ, optionaler Nahrung, Pheromonen und Belegung."""
    x: int
    y: int
    cell_type: str = "empty"  # 'empty', 'wall'/'w', 'nest', 'e' (entry), ...
    food: Optional[Any] = None
    ant: Optional[Any] = None
    pheromone_level: float = 0.0  # Legacy-kompatibles Summenfeld (z. B. für einfache Renderer)
    # Freiform-Container für verschiedene Pheromon-Typen (lightweight view)
    pheromones: Dict[str, float] = field(default_factory=dict)
    _owner: Optional["Environment"] = None  # Backref, um Field-Deposits zu spiegeln

    def add_pheromone(self, pheromone_type: str, strength: float) -> None:
        """Zell-lokale Ablage; spiegelt zusätzlich in das Double-Buffer-Feld der Environment."""
        try:
            ptype = str(pheromone_type)
            sval = max(0.0, float(strength))
        except Exception:
            return
        # lokale Sicht (Legacy-/Renderer-kompatibel)
        self.pheromones[ptype] = self.pheromones.get(ptype, 0.0) + sval
        self.pheromone_level += sval
        # Double-Buffer Deposit (staging)
        if self._owner and isinstance(self._owner.pheromones, PheromoneField):
            try:
                self._owner.pheromones.deposit(ptype, self.x, self.y, sval)
            except Exception:
                # nicht scheitern wegen Pheromon-Logging/Deposit
                pass


class Environment:
    """Neue, generische Environment für den Core."""

    def __init__(
        self,
        width: int = 20,
        height: int = 20,
        entries: Optional[List[Tuple[int, int]]] = None,
        pheromone_types: Optional[List[str]] = None,
        evaporation: float = 0.02,
        alpha: float = 0.12,
        allow_dynamic_pheromone_types: bool = True,
    ):
        if not (isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0):
            raise ValueError(f"Invalid size: {width}x{height}")

        self.width = width
        self.height = height
        self.grid: List[List[Cell]] = [[Cell(x, y) for x in range(width)] for y in range(height)]
        # Backrefs setzen
        for row in self.grid:
            for cell in row:
                cell._owner = self

        # Entry-Positionen
        self.entry_positions: List[Tuple[int, int]] = []
        if entries:
            for pos in entries:
                self.add_entry(pos)

        # Ant-Registry (id -> obj)
        self.ant_registry: Dict[int, Any] = {}

        # Simulationszählung (Tick/Cycle)
        self.cycle_count: int = 0

        # Pheromon Double-Buffer Engine
        self.pheromones = PheromoneField(
            width=self.width,
            height=self.height,
            types=list(pheromone_types or ["food", "nest", "hunger", "brood"]),
            evaporation=float(evaporation),
            alpha=float(alpha),
            allow_dynamic_types=bool(allow_dynamic_pheromone_types),
        )

        log.info("Environment initialized size=%dx%d entries=%d types=%s",
                 self.width, self.height, len(self.entry_positions), sorted(self.pheromones.types))

    # --------------- Topologie / Zellen ---------------

    def add_entry(self, pos: Tuple[int, int]) -> None:
        """Markiert eine Zelle als Entry ('e') und merkt sich die Position (idempotent)."""
        x, y = int(pos[0]), int(pos[1])
        if not self._in_bounds(x, y):
            raise ValueError(f"Entry out of bounds: {pos}")
        if (x, y) not in self.entry_positions:
            self.entry_positions.append((x, y))
        self.grid[y][x].cell_type = "e"

    def set_wall(self, pos: Tuple[int, int]) -> None:
        """Markiert eine Zelle als Wand ('w')."""
        x, y = int(pos[0]), int(pos[1])
        if self._in_bounds(x, y):
            self.grid[y][x].cell_type = "w"

    def set_nest(self, pos: Tuple[int, int]) -> None:
        """Markiert eine Zelle als Nest."""
        x, y = int(pos[0]), int(pos[1])
        if self._in_bounds(x, y):
            self.grid[y][x].cell_type = "nest"

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_cell_free(self, x: int, y: int) -> bool:
        """True, wenn kein 'wall' und keine Ant belegt."""
        if not self._in_bounds(x, y):
            return False
        cell = self.grid[y][x]
        if cell.cell_type in ("w", "wall"):
            return False
        return cell.ant is None

    # --------------- Anten-Registry / Belegung ---------------

    def add_ant(self, ant: Any) -> None:
        """Registriert eine Ant und belegt die aktuelle Zelle (idempotent für gleiche id, gleiche Position)."""
        ant_id = getattr(ant, "id", None)
        pos = getattr(ant, "position", None)
        if not isinstance(ant_id, int):
            raise ValueError("Ant must have integer 'id'")
        if not (isinstance(pos, (tuple, list)) and len(pos) == 2):
            raise ValueError("Ant must have 2-tuple/list 'position'")

        x, y = int(pos[0]), int(pos[1])
        if not self._in_bounds(x, y):
            raise ValueError(f"Ant position out of bounds: {pos}")

        # idempotent occupancy update
        prev = self.ant_registry.get(ant_id)
        if prev is ant:
            # ensure occupancy is correct
            self._occupy_cell(ant, x, y)
            return

        # remove previous occupancy if id reused
        if prev is not None:
            prev_pos = getattr(prev, "position", None)
            if isinstance(prev_pos, (tuple, list)) and len(prev_pos) == 2:
                px, py = int(prev_pos[0]), int(prev_pos[1])
                if self._in_bounds(px, py) and self.grid[py][px].ant is prev:
                    self.grid[py][px].ant = None

        self.ant_registry[ant_id] = ant
        self._occupy_cell(ant, x, y)
        log.info("ant_registered id=%s pos=%s", ant_id, (x, y))

    def remove_ant(self, ant_id: int) -> None:
        """Entfernt Ant aus Registry und Grid-Belegung."""
        ant = self.ant_registry.pop(int(ant_id), None)
        if ant is None:
            return
        pos = getattr(ant, "position", None)
        if isinstance(pos, (tuple, list)) and len(pos) == 2:
            x, y = int(pos[0]), int(pos[1])
            if self._in_bounds(x, y) and self.grid[y][x].ant is ant:
                self.grid[y][x].ant = None
        log.info("ant_removed id=%s", ant_id)

    def _occupy_cell(self, ant: Any, x: int, y: int) -> None:
        """Setzt die Zellbelegung auf 'ant' (best-effort), räumt vorher alte Zelle auf."""
        # räume potentielle Doppelbelegung
        for row in self.grid:
            for c in row:
                if c.ant is ant and (c.x != x or c.y != y):
                    c.ant = None
        self.grid[y][x].ant = ant

    def get_ant_at_position(self, x: int, y: int) -> Optional[Any]:
        """Liefert Ant an Position (falls vorhanden)."""
        if not self._in_bounds(int(x), int(y)):
            return None
        return self.grid[int(y)][int(x)].ant

    def get_ant_by_id(self, ant_id: int) -> Optional[Any]:
        """Registry-Lookup für Ant-ID."""
        return self.ant_registry.get(int(ant_id))

    # --------------- Pheromone / Tick ---------------

    def pheromones_tick(self) -> Dict[str, Dict[str, float]]:
        """Diffusion/Verdunstung + Swap. Liefert kompakte Summary; niemals Exceptions werfen lassen."""
        try:
            summary = self.pheromones.update_and_swap()
            return summary
        except Exception as e:
            log.error("pheromones_tick error: %s", e, exc_info=True)
            return {}

    # --------------- Hilfen ---------------

    def place_rect(self, top_left: Tuple[int, int], bottom_right: Tuple[int, int], cell_type: str) -> int:
        """Hilfsfunktion, markiert ein Rechteck mit 'cell_type'. Gibt markierte Zellenanzahl zurück."""
        (x1, y1), (x2, y2) = top_left, bottom_right
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        count = 0
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if self._in_bounds(x, y):
                    self.grid[y][x].cell_type = str(cell_type)
                    count += 1
        return count

    def add_food(self, position: Tuple[int, int], food_obj: Any) -> None:
        """Optional: Food-Objekt in eine Zelle legen (tolerant)."""
        x, y = int(position[0]), int(position[1])
        if self._in_bounds(x, y):
            self.grid[y][x].food = food_obj

    def remove_food(self, position: Tuple[int, int]) -> None:
        """Optional: Food an Position entfernen (tolerant)."""
        x, y = int(position[0]), int(position[1])
        if self._in_bounds(x, y):
            self.grid[y][x].food = None

# FILE: antsim/app/renderer.py
"""
Lightweight Pygame renderer for the new antsim core.

Goals:
- Render antsim.core.environment.Environment (grid, entries, nest, walls)
- Optionally render pheromone fields (Double-Buffer via PheromoneField)
- Draw agent positions (workers, queen, brood) if provided
- No coupling to legacy modules; read-only access to the new core types
- Idempotent draw calls, structured logging, graceful fallback if pygame missing

Performance:
- Pheromone overlays are rendered via NumPy + pygame.surfarray with a single blit per type
  (batch drawing) and additive blending. Avoids per-pixel Python loops.

Usage (example):
    from antsim.core.environment import Environment
    from antsim.app.renderer import Renderer

    env = Environment(width=40, height=30, entries=[(1,1)])
    rnd = Renderer(cell_size=20, show_pheromones=True)
    rnd.init_window(env.width, env.height, dashboard_width=0)
    rnd.draw(env, ants=[...], queen=..., brood=[...])
    rnd.flip()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# Optional NumPy for batch pheromone rendering
try:
    import numpy as np  # type: ignore
    _NP_OK = True
except Exception as e:
    _NP_OK = False
    log.debug("numpy not available for renderer: %s", e)

try:
    import pygame  # type: ignore
    _PYGAME_OK = True
except Exception as e:
    _PYGAME_OK = False
    log.debug("pygame not available: %s", e)


# --------- Color utilities ---------

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _to_color(v: float, max_v: float, base: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Map scalar v in [0, max_v] to color intensity of 'base'."""
    if max_v <= 0:
        return (0, 0, 0)
    t = _clamp(v / max_v, 0.0, 1.0)
    r, g, b = base
    return (int(_clamp(r * t, 0, 255)), int(_clamp(g * t, 0, 255)), int(_clamp(b * t, 0, 255)))


# --------- Renderer ---------

class Renderer:
    """Pygame-based renderer for antsim new core."""

    def __init__(
        self,
        cell_size: int = 16,
        show_grid: bool = False,
        show_pheromones: bool = True,
        pheromone_types: Optional[List[str]] = None,
        pheromone_colors: Optional[Dict[str, Tuple[int, int, int]]] = None,
        background_color: Tuple[int, int, int] = (245, 245, 245),
        wall_color: Tuple[int, int, int] = (100, 100, 100),
        nest_color: Tuple[int, int, int] = (220, 220, 255),
        entry_color: Tuple[int, int, int] = (0, 220, 220),
        ant_color: Tuple[int, int, int] = (0, 0, 0),
        queen_color: Tuple[int, int, int] = (220, 0, 0),
        brood_color: Tuple[int, int, int] = (150, 75, 0),
    ):
        """
        Args:
          cell_size: pixel size of a grid cell
          show_grid: draw grid lines
          show_pheromones: render pheromone layers using current front buffer
          pheromone_types: which types to render (None = all available)
          pheromone_colors: RGB base color per pheromone type (default mapping)
        """
        self.cell_size = int(cell_size)
        self.show_grid = bool(show_grid)
        self.show_pheromones = bool(show_pheromones)
        self._screen = None
        self._surface = None
        self._font = None

        # Default base colors for pheromones
        self.pheromone_colors = pheromone_colors or {
            "food": (0, 180, 0),
            "nest": (0, 0, 180),
            "hunger": (220, 0, 220),
            "brood": (180, 120, 0),
        }
        self.pheromone_types = pheromone_types  # filtered in draw if provided

        self.background_color = background_color
        self.wall_color = wall_color
        self.nest_color = nest_color
        self.entry_color = entry_color
        self.ant_color = ant_color
        self.queen_color = queen_color
        self.brood_color = brood_color

        if not _PYGAME_OK:
            log.warning("Renderer initialized without pygame; drawing disabled")

    # ---------- Pygame init/teardown ----------

    def init_window(self, width: int, height: int, dashboard_width: int = 0, title: str = "antsim") -> None:
        """Initialize Pygame window sized for the environment grid."""
        if not _PYGAME_OK:
            log.error("Cannot init window: pygame not available")
            return
        try:
            pygame.init()
            window_w = width * self.cell_size + int(dashboard_width)
            window_h = height * self.cell_size
            self._screen = pygame.display.set_mode((window_w, window_h))
            pygame.display.set_caption(title)
            self._surface = pygame.Surface((window_w, window_h))
            self._font = pygame.font.Font(None, 16)
            log.info("Renderer window initialized size=%dx%d", window_w, window_h)
        except Exception as e:
            log.error("Pygame init failed: %s", e, exc_info=True)
            self._screen = None

    def close(self) -> None:
        """Close window and quit Pygame."""
        if not _PYGAME_OK:
            return
        try:
            pygame.quit()
            log.info("Renderer closed")
        except Exception:
            pass

    # ---------- Public drawing API ----------

    def draw(
        self,
        environment: Any,
        ants: Optional[List[Any]] = None,
        queen: Optional[Any] = None,
        brood: Optional[List[Any]] = None,
        info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Draw the environment state onto the backbuffer."""
        if not (_PYGAME_OK and self._surface):
            return

        w = getattr(environment, "width", 0)
        h = getattr(environment, "height", 0)
        grid = getattr(environment, "grid", None)

        # Background
        self._surface.fill(self.background_color)

        # 1) Grid cells
        if grid is not None:
            self._draw_cells(environment)

        # 2) Pheromones
        if self.show_pheromones:
            self._draw_pheromones(environment)

        # 3) Agents (queen/brood/ants)
        self._draw_agents(ants or [], queen, brood or [])

        # 4) Overlays (optional info)
        if info:
            self._draw_info(info)

        if self.show_grid:
            self._draw_grid(w, h)

    def flip(self) -> None:
        """Blit and present the backbuffer."""
        if not (_PYGAME_OK and self._surface and self._screen):
            return
        try:
            self._screen.blit(self._surface, (0, 0))
            pygame.display.flip()
        except Exception:
            pass

    # ---------- Internal drawing helpers ----------

    def _cell_rect(self, x: int, y: int) -> Tuple[int, int, int, int]:
        return (x * self.cell_size, y * self.cell_size, self.cell_size, self.cell_size)

    def _draw_cells(self, env: Any) -> None:
        """Draw base cells: walls, nest, entries."""
        grid = env.grid
        for y in range(env.height):
            row = grid[y]
            for x in range(env.width):
                cell = row[x]
                ctype = getattr(cell, "cell_type", "empty")
                if ctype in ("w", "wall"):
                    color = self.wall_color
                elif ctype in ("nest",):
                    color = self.nest_color
                elif ctype in ("e", "entry"):
                    color = self.entry_color
                else:
                    # leave as background
                    continue
                pygame.draw.rect(self._surface, color, self._cell_rect(x, y))

    def _draw_pheromones(self, env: Any) -> None:
        """Draw pheromone types as batched overlays using NumPy and surfarray (no per-cell Python loops)."""
        # Preconditions
        field = getattr(env, "pheromones", None)
        if field is None or not _NP_OK or not _PYGAME_OK:
            return

        # Determine types to render
        try:
            types = list(field.types)
        except Exception:
            types = []
        if self.pheromone_types:
            types = [t for t in types if t in self.pheromone_types]
        if not types:
            return

        # Stats for scaling
        try:
            stats = field.stats()
        except Exception:
            stats = {}

        env_w_px = env.width * self.cell_size
        env_h_px = env.height * self.cell_size

        for ptype in types:
            try:
                base = self.pheromone_colors.get(ptype, (120, 120, 120))
                arr = field.field_for(ptype)  # numpy array (h, w)
                if arr is None:
                    continue
                max_v = float(stats.get(ptype, {}).get("max", 0.0)) if isinstance(stats, dict) else float(np.max(arr))
                if max_v <= 0.0:
                    continue

                # Normalize [0,1]; compute RGB layer (h, w, 3) via broadcasting
                norm = (arr / max_v).astype(np.float32)
                rgb = np.empty((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
                rgb[..., 0] = np.clip(norm * base[0], 0, 255).astype(np.uint8)
                rgb[..., 1] = np.clip(norm * base[1], 0, 255).astype(np.uint8)
                rgb[..., 2] = np.clip(norm * base[2], 0, 255).astype(np.uint8)

                # Pygame surfarray expects (w, h, 3)
                surf_small = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
                # Scale to cell_size
                surf = pygame.transform.smoothscale(surf_small, (env_w_px, env_h_px))

                # Additive overlay to accumulate pheromone intensity
                self._surface.blit(surf, (0, 0), special_flags=pygame.BLEND_ADD)
            except Exception as e:
                # Tolerate rendering issues per type to avoid disrupting the frame
                log.debug("pheromone_render_skip type=%s err=%s", ptype, e)

    def _draw_agents(self, ants: List[Any], queen: Optional[Any], brood: List[Any]) -> None:
        # Queen
        if queen is not None:
            self._draw_circle_agent(queen, self.queen_color, radius_factor=0.45)
        # Brood
        for b in brood:
            self._draw_circle_agent(b, self.brood_color, radius_factor=0.35)
        # Ants/workers
        for a in ants:
            self._draw_circle_agent(a, self.ant_color, radius_factor=0.30)

    def _draw_circle_agent(self, agent: Any, color: Tuple[int, int, int], radius_factor: float) -> None:
        try:
            pos = getattr(agent, "position", None)
            if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
                return
            x, y = int(pos[0]), int(pos[1])
            cx = x * self.cell_size + self.cell_size // 2
            cy = y * self.cell_size + self.cell_size // 2
            r = max(2, int(self.cell_size * radius_factor))
            pygame.draw.circle(self._surface, color, (cx, cy), r)
        except Exception:
            pass

    def _draw_grid(self, w: int, h: int) -> None:
        color = (200, 200, 200)
        for x in range(w + 1):
            px = x * self.cell_size
            pygame.draw.line(self._surface, color, (px, 0), (px, h * self.cell_size), 1)
        for y in range(h + 1):
            py = y * self.cell_size
            pygame.draw.line(self._surface, color, (0, py), (w * self.cell_size, py), 1)

    def _draw_info(self, info: Dict[str, Any]) -> None:
        """Draw key-value info text in top-left corner."""
        if not self._font:
            return
        x, y = 6, 6
        for k, v in info.items():
            try:
                txt = f"{k}: {v}"
                surf = self._font.render(txt, True, (30, 30, 30))
                self._surface.blit(surf, (x, y))
                y += 16
            except Exception:
                continue

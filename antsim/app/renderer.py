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


class DashboardRenderer:
    """Renders real-time simulation metrics in a dashboard panel."""
    
    def __init__(self, width: int = 300, font_size: int = 14):
        self.width = width
        self.font_size = font_size
        self.font = None
        self.small_font = None
        self.title_font = None
        
    def init_fonts(self):
        """Initialize fonts for different text sizes."""
        if not _PYGAME_OK:
            return
        try:
            self.font = pygame.font.Font(None, self.font_size)
            self.small_font = pygame.font.Font(None, self.font_size - 2)
            self.title_font = pygame.font.Font(None, self.font_size + 2)
        except Exception as e:
            log.warning("Dashboard font initialization failed: %s", e)
            self.font = self.small_font = self.title_font = None
    
    def render_dashboard(self, surface, dashboard_data, x_offset=0, y_start=10):
        """Main dashboard rendering method."""
        if not self.font:
            self.init_fonts()
        if not self.font:
            return
            
        y = y_start
        # Clear dashboard area
        dashboard_rect = (x_offset, 0, self.width, surface.get_height())
        pygame.draw.rect(surface, (240, 240, 240), dashboard_rect)
        pygame.draw.line(surface, (200, 200, 200), (x_offset + self.width - 1, 0), 
                        (x_offset + self.width - 1, surface.get_height()), 2)
        
        y = self._render_colony_overview(surface, dashboard_data, x_offset, y)
        y += 20
        y = self._render_queen_status(surface, dashboard_data, x_offset, y)
        y += 20
        y = self._render_worker_details(surface, dashboard_data, x_offset, y)
        
    def _render_colony_overview(self, surface, data, x_offset, y):
        """Render colony-wide statistics."""
        y = self._render_section_title(surface, "COLONY STATS", x_offset, y)
        y += 5
        
        # Food sources
        food_color = self._get_status_color(data['total_food_sources'], 100, 300)
        y = self._render_metric(surface, "Food Sources", data['total_food_sources'], 
                               x_offset, y, food_color)
        
        # Total social food
        social_color = self._get_status_color(data['total_social_food'], 50, 200)
        y = self._render_metric(surface, "Social Food", data['total_social_food'], 
                               x_offset, y, social_color)
        
        # Ant and brood counts
        y = self._render_metric(surface, "Ants", data['ant_count'], x_offset, y)
        y = self._render_metric(surface, "Brood", data['brood_count'], x_offset, y)
        
        return y
    
    def _render_queen_status(self, surface, data, x_offset, y):
        """Render queen status information."""
        queen_data = data.get('queen', {})
        if not queen_data:
            return y
            
        y = self._render_section_title(surface, "QUEEN STATUS", x_offset, y)
        y += 5
        
        # Energy bar
        energy = queen_data.get('energy', 0)
        max_energy = queen_data.get('max_energy', 100)
        energy_color = self._get_status_color(energy, max_energy * 0.3, max_energy * 0.6)
        y = self._render_progress_bar(surface, "Energy", energy, max_energy, 
                                     x_offset, y, energy_color)
        
        # Individual stomach
        stomach = queen_data.get('individual_stomach', 0)
        stomach_cap = queen_data.get('stomach_capacity', 50)
        stomach_color = self._get_status_color(stomach_cap - stomach, stomach_cap * 0.2, stomach_cap * 0.5)
        y = self._render_progress_bar(surface, "Stomach", stomach, stomach_cap, 
                                     x_offset, y, stomach_color)
        
        return y
    
    def _render_worker_details(self, surface, data, x_offset, y):
        """Render detailed information for top 5 workers."""
        workers = data.get('top_workers', [])
        if not workers:
            return y
            
        y = self._render_section_title(surface, "WORKERS", x_offset, y)
        y += 5
        
        for worker in workers:
            y = self._render_worker_entry(surface, worker, x_offset, y)
            y += 8
            
        return y
    
    def _render_worker_entry(self, surface, worker, x_offset, y):
        """Render single worker's detailed status."""
        worker_id = worker.get('id', 0)
        energy = worker.get('energy', 0)
        max_energy = worker.get('max_energy', 100)
        ind_stomach = worker.get('individual_stomach', 0)
        soc_stomach = worker.get('social_stomach', 0)
        current_step = worker.get('current_step', 'idle')
        
        # Worker ID and current step
        id_text = f"#{worker_id}"
        step_text = f" {current_step}"
        y = self._render_text(surface, id_text, x_offset + 10, y, (0, 0, 0), self.small_font)
        self._render_text(surface, step_text, x_offset + 60, y, (100, 100, 100), self.small_font)
        y += 14
        
        # Compact stats: E:67 I:23 S:45
        stats_text = f"E:{energy} I:{ind_stomach} S:{soc_stomach}"
        energy_color = self._get_status_color(energy, max_energy * 0.3, max_energy * 0.6)
        y = self._render_text(surface, stats_text, x_offset + 15, y, energy_color, self.small_font)
        
        return y
    
    def _render_section_title(self, surface, title, x_offset, y):
        """Render a section title with underline."""
        title_surface = self.title_font.render(title, True, (50, 50, 50))
        surface.blit(title_surface, (x_offset + 10, y))
        title_width = title_surface.get_width()
        pygame.draw.line(surface, (150, 150, 150), 
                        (x_offset + 10, y + 16), 
                        (x_offset + 10 + title_width, y + 16), 1)
        return y + 20
    
    def _render_metric(self, surface, label, value, x_offset, y, color=(0, 0, 0)):
        """Render a simple label: value metric."""
        text = f"{label}: {value}"
        return self._render_text(surface, text, x_offset + 10, y, color)
    
    def _render_progress_bar(self, surface, label, value, max_value, x_offset, y, color=(0, 150, 0)):
        """Render a labeled progress bar."""
        # Label and values
        text = f"{label}: {value}/{max_value}"
        y = self._render_text(surface, text, x_offset + 10, y, (0, 0, 0))
        y += 16
        
        # Progress bar
        bar_width = self.width - 40
        bar_height = 8
        progress = min(1.0, value / max_value) if max_value > 0 else 0
        
        # Background
        bar_rect = (x_offset + 20, y, bar_width, bar_height)
        pygame.draw.rect(surface, (220, 220, 220), bar_rect)
        
        # Filled portion
        if progress > 0:
            filled_width = int(bar_width * progress)
            filled_rect = (x_offset + 20, y, filled_width, bar_height)
            pygame.draw.rect(surface, color, filled_rect)
        
        # Border
        pygame.draw.rect(surface, (150, 150, 150), bar_rect, 1)
        
        return y + bar_height + 5
    
    def _render_text(self, surface, text, x, y, color=(0, 0, 0), font=None):
        """Render text and return new y position."""
        if font is None:
            font = self.font
        if font is None:
            return y + 14
            
        text_surface = font.render(str(text), True, color)
        surface.blit(text_surface, (x, y))
        return y + text_surface.get_height() + 2
    
    def _get_status_color(self, value, low_threshold, high_threshold):
        """Get color based on value thresholds (red=low, yellow=medium, green=high)."""
        if value <= low_threshold:
            return (200, 50, 50)  # Red
        elif value <= high_threshold:
            return (200, 150, 50)  # Yellow
        else:
            return (50, 150, 50)  # Green


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
        
        self.dashboard_width = dashboard_width
        
        # Check display availability
        import os
        display = os.environ.get("DISPLAY")
        if not display and os.name != "nt":
            log.warning("DISPLAY environment variable not set - trying headless mode")
            # Try setting SDL to use dummy video driver for headless mode
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        
        log.info("Attempting pygame initialization with DISPLAY=%s, SDL_VIDEODRIVER=%s",
                display, os.environ.get("SDL_VIDEODRIVER", "default"))
        
        try:
            pygame.init()
            
            # Check if pygame can actually create a display
            window_w = width * self.cell_size + int(dashboard_width)
            window_h = height * self.cell_size
            
            log.info("Creating pygame display with dashboard size %dx%d (dashboard: %dpx)", 
                    window_w, window_h, dashboard_width)
            self._screen = pygame.display.set_mode((window_w, window_h))
            
            if self._screen is None:
                raise RuntimeError("pygame.display.set_mode returned None")
            
            pygame.display.set_caption(title)
            self._surface = pygame.Surface((window_w, window_h))
            
            try:
                self._font = pygame.font.Font(None, 16)
            except Exception as font_err:
                log.warning("Font initialization failed, using default: %s", font_err)
                self._font = None
            
            log.info("Renderer window successfully initialized size=%dx%d", window_w, window_h)
            
        except Exception as e:
            log.error("Pygame window initialization failed: %s", e, exc_info=True)
            log.error("This is likely due to missing display or X11 forwarding in containerized environments")
            log.info("Consider running with headless mode: export SDL_VIDEODRIVER=dummy")
            self._screen = None
            self._surface = None
            self._font = None
            
        # Initialize dashboard renderer
        if not hasattr(self, 'dashboard_renderer'):
            self.dashboard_renderer = DashboardRenderer()

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

        # Simulation area offset (dashboard takes left side)
        sim_offset_x = self.dashboard_width

        # 1) Dashboard (if enabled)
        if self.dashboard_width > 0 and info and 'dashboard' in info:
            self.dashboard_renderer.render_dashboard(self._surface, info['dashboard'])

        # 2) Grid cells (offset for dashboard)
        if grid is not None:
            self._draw_cells(environment, sim_offset_x)

        # 3) Pheromones (offset for dashboard)
        if self.show_pheromones:
            self._draw_pheromones(environment, sim_offset_x)

        # 4) Agents (queen/brood/ants) (offset for dashboard)
        self._draw_agents(ants or [], queen, brood or [], sim_offset_x)

        # 5) Overlays (optional info) (offset for dashboard)
        if info:
            self._draw_info(info, sim_offset_x)

        if self.show_grid:
            self._draw_grid(w, h, sim_offset_x)

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

    def _cell_rect(self, x: int, y: int, x_offset: int = 0) -> Tuple[int, int, int, int]:
        return (x * self.cell_size + x_offset, y * self.cell_size, self.cell_size, self.cell_size)

    def _draw_cells(self, env: Any, x_offset: int = 0) -> None:
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
                pygame.draw.rect(self._surface, color, self._cell_rect(x, y, x_offset))

    def _draw_pheromones(self, env: Any, x_offset: int = 0) -> None:
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

                # Additive overlay to accumulate pheromone intensity (offset for dashboard)
                self._surface.blit(surf, (x_offset, 0), special_flags=pygame.BLEND_ADD)
            except Exception as e:
                # Tolerate rendering issues per type to avoid disrupting the frame
                log.debug("pheromone_render_skip type=%s err=%s", ptype, e)

    def _draw_agents(self, ants: List[Any], queen: Optional[Any], brood: List[Any], x_offset: int = 0) -> None:
        # Queen
        if queen is not None:
            self._draw_circle_agent(queen, self.queen_color, radius_factor=0.45, x_offset=x_offset)
        # Brood
        for b in brood:
            self._draw_circle_agent(b, self.brood_color, radius_factor=0.35, x_offset=x_offset)
        # Ants/workers
        for a in ants:
            self._draw_circle_agent(a, self.ant_color, radius_factor=0.30, x_offset=x_offset)

    def _draw_circle_agent(self, agent: Any, color: Tuple[int, int, int], radius_factor: float, x_offset: int = 0) -> None:
        try:
            pos = getattr(agent, "position", None)
            if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
                return
            x, y = int(pos[0]), int(pos[1])
            cx = x * self.cell_size + self.cell_size // 2 + x_offset
            cy = y * self.cell_size + self.cell_size // 2
            r = max(2, int(self.cell_size * radius_factor))
            pygame.draw.circle(self._surface, color, (cx, cy), r)
        except Exception:
            pass

    def _draw_grid(self, w: int, h: int, x_offset: int = 0) -> None:
        color = (200, 200, 200)
        for x in range(w + 1):
            px = x * self.cell_size + x_offset
            pygame.draw.line(self._surface, color, (px, 0), (px, h * self.cell_size), 1)
        for y in range(h + 1):
            py = y * self.cell_size
            pygame.draw.line(self._surface, color, (x_offset, py), (w * self.cell_size + x_offset, py), 1)

    def _draw_info(self, info: Dict[str, Any], x_offset: int = 0) -> None:
        """Draw key-value info text in top-left corner of simulation area."""
        if not self._font:
            return
        x, y = 6 + x_offset, 6
        # Skip dashboard data from general info overlay
        filtered_info = {k: v for k, v in info.items() if k != 'dashboard'}
        for k, v in filtered_info.items():
            try:
                txt = f"{k}: {v}"
                surf = self._font.render(txt, True, (30, 30, 30))
                self._surface.blit(surf, (x, y))
                y += 16
            except Exception:
                continue

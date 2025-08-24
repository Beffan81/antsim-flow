"""
Nest-Layout Builder für antsim.

Ziele:
- Standardisiertes Nest-Layout basierend auf dem spezifizierten Pattern generieren
- Automatische Zentrierung auf dem Spielfeld
- Flexible Parameter für verschiedene Nest-Größen und -Formen
- Integration mit der Environment-Klasse für korrekte Zell-Markierung

Standard-Layout:
w,w,w,e,w,w,w,w,w,w,w,w,w
w,,,,,,,,,,,,w  
w,,,,,,,,,,,,w
w,,,,,,,,,,,,w
w,,,,,,,,,,,,w
w,,,,,,,,,,,,w
w,w,w,w,w,w,w,w,w,w,w,w,w

w = wall (Wand)
e = entrance (Eingang)
"leer" = freier Raum (nest-Zellen)
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

log = logging.getLogger(__name__)


class NestBuilder:
    """Baut standardisierte Nest-Layouts für die Environment."""
    
    def __init__(self):
        # Standard-Layout-Parameter (13x7 inkl. Wände)
        self.default_nest_width = 13
        self.default_nest_height = 7
        self.default_entry_offset = (3, 0)  # Entry-Position relativ zur Nest-Ecke
    
    def build_standard_nest(
        self, 
        environment: Any, 
        center: bool = True,
        nest_width: Optional[int] = None,
        nest_height: Optional[int] = None,
        entry_offset: Optional[Tuple[int, int]] = None
    ) -> Tuple[int, int]:
        """
        Baut das Standard-Nest-Layout in der Environment.
        
        Args:
            environment: Environment-Instanz zur Modifikation
            center: Ob das Nest zentriert platziert werden soll
            nest_width: Breite des Nests (inkl. Wände), Standard=13
            nest_height: Höhe des Nests (inkl. Wände), Standard=7
            entry_offset: Entry-Position relativ zur Nest-Ecke, Standard=(3,0)
            
        Returns:
            Tuple[int, int]: Absolute Position der Entry-Zelle
        """
        # Parameter setzen
        width = nest_width or self.default_nest_width
        height = nest_height or self.default_nest_height
        entry_rel = entry_offset or self.default_entry_offset
        
        # Validierung
        if width < 5 or height < 3:
            raise ValueError(f"Nest zu klein: {width}x{height} (minimum 5x3)")
        
        env_width = getattr(environment, 'width', 20)
        env_height = getattr(environment, 'height', 20)
        
        if width > env_width or height > env_height:
            raise ValueError(f"Nest {width}x{height} passt nicht in Environment {env_width}x{env_height}")
        
        # Platzierung berechnen
        if center:
            nest_x = (env_width - width) // 2
            nest_y = (env_height - height) // 2
        else:
            nest_x = 1
            nest_y = 1
        
        log.info("Building standard nest at (%d,%d) size=%dx%d", nest_x, nest_y, width, height)
        
        # Äußere Wände bauen
        self._build_outer_walls(environment, nest_x, nest_y, width, height)
        
        # Innenraum als Nest markieren  
        self._build_inner_nest(environment, nest_x, nest_y, width, height)
        
        # Entry-Zelle setzen
        entry_x = nest_x + entry_rel[0]
        entry_y = nest_y + entry_rel[1]
        
        if not (0 <= entry_x < env_width and 0 <= entry_y < env_height):
            log.warning("Entry position (%d,%d) out of bounds, using default", entry_x, entry_y)
            entry_x = nest_x + width // 2
            entry_y = nest_y
        
        # Entry setzen (überschreibt eventuell gesetzte Wand)
        if hasattr(environment, 'add_entry'):
            environment.add_entry((entry_x, entry_y))
        else:
            # Fallback für DemoEnvironment
            if hasattr(environment, 'grid') and hasattr(environment, 'entry_positions'):
                environment.grid[entry_y][entry_x].cell_type = "e"
                if (entry_x, entry_y) not in environment.entry_positions:
                    environment.entry_positions.append((entry_x, entry_y))
        
        log.info("Standard nest built: entry=(%d,%d) inner_cells=%d", 
                entry_x, entry_y, (width-2) * (height-2))
        
        return entry_x, entry_y
    
    def _build_outer_walls(self, environment: Any, nest_x: int, nest_y: int, width: int, height: int) -> None:
        """Baut die äußeren Wände des Nests."""
        # Obere und untere Wand
        for x in range(nest_x, nest_x + width):
            self._set_wall(environment, x, nest_y)  # Obere Wand
            self._set_wall(environment, x, nest_y + height - 1)  # Untere Wand
        
        # Linke und rechte Wand
        for y in range(nest_y, nest_y + height):
            self._set_wall(environment, nest_x, y)  # Linke Wand
            self._set_wall(environment, nest_x + width - 1, y)  # Rechte Wand
    
    def _build_inner_nest(self, environment: Any, nest_x: int, nest_y: int, width: int, height: int) -> None:
        """Markiert den Innenraum als Nest-Zellen."""
        for y in range(nest_y + 1, nest_y + height - 1):
            for x in range(nest_x + 1, nest_x + width - 1):
                self._set_nest(environment, x, y)
    
    def _set_wall(self, environment: Any, x: int, y: int) -> None:
        """Setzt eine Wand-Zelle (kompatibel mit Environment und DemoEnvironment)."""
        if hasattr(environment, 'set_wall'):
            environment.set_wall((x, y))
        elif hasattr(environment, 'grid'):
            # Fallback für DemoEnvironment
            environment.grid[y][x].cell_type = "w"
    
    def _set_nest(self, environment: Any, x: int, y: int) -> None:
        """Setzt eine Nest-Zelle (kompatibel mit Environment und DemoEnvironment)."""
        if hasattr(environment, 'set_nest'):
            environment.set_nest((x, y))
        elif hasattr(environment, 'grid'):
            # Fallback für DemoEnvironment
            environment.grid[y][x].cell_type = "nest"
    
    def get_nest_center(
        self, 
        env_width: int, 
        env_height: int, 
        nest_width: Optional[int] = None, 
        nest_height: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Berechnet die Nest-Zentrumsposition für Agent-Platzierung.
        
        Returns:
            Tuple[int, int]: Zentrale Position im Nest-Innenraum
        """
        width = nest_width or self.default_nest_width
        height = nest_height or self.default_nest_height
        
        nest_x = (env_width - width) // 2
        nest_y = (env_height - height) // 2
        
        # Zentrum des Innenraums
        center_x = nest_x + width // 2
        center_y = nest_y + height // 2
        
        return center_x, center_y
    
    def get_nest_bounds(
        self, 
        env_width: int, 
        env_height: int, 
        nest_width: Optional[int] = None, 
        nest_height: Optional[int] = None
    ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        Liefert die Nest-Grenzen als (top_left, bottom_right).
        
        Returns:
            Tuple mit ((x1, y1), (x2, y2)) für das gesamte Nest (inkl. Wände)
        """
        width = nest_width or self.default_nest_width
        height = nest_height or self.default_nest_height
        
        nest_x = (env_width - width) // 2
        nest_y = (env_height - height) // 2
        
        return (nest_x, nest_y), (nest_x + width - 1, nest_y + height - 1)
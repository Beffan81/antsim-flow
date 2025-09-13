# FILE: antsim/core/engine/pheromones.py
"""
PheromoneField: Double-Buffer Pheromon-Engine mit Diffusion, Verdunstung und Swap.

Ziele:
- Zwei Buffer pro Typ (front=read, back=write).
- API:
  * deposit(ptype, x, y, amount): addiert Ablage für den nächsten Swap.
  * update_and_swap(): Diffusion + Verdunstung von front -> back, addiert Deposits, dann Swap.
  * field_for(ptype): Read-Buffer (front) als NumPy-Array (float32).
  * stats(): Massen/Statistiken je Typ; snapshot(optional) für Serialisierung.
- Performance: vektorisiert mit NumPy; 4-Nachbarschaftskonvolution (massenerhaltend abzüglich Verdunstung).
- Logging: Tick-Start/Ende, Massenveränderungen, Kernel/Parameter; Level beachtet.

Hinweis:
- Integration in Environment/Renderer/Executor erfolgt in Folgeschritten.
- deposit() ist tolerant: unbekannte Typen werden (optional) dynamisch angelegt, wenn allow_dynamic_types=True.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)


def _ensure_2d(w: int, h: int) -> Tuple[int, int]:
    if not (isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0):
        raise ValueError(f"Invalid field size w={w} h={h}")
    return w, h


@dataclass
class PheromoneField:
    width: int
    height: int
    types: List[str] = field(default_factory=list)
    evaporation: float = 0.01  # fraction per tick [0..1) - now configurable
    alpha: float = 0.1         # diffusion weight to 4-neighbors - now configurable
    allow_dynamic_types: bool = True

    # internals
    _front: Dict[str, np.ndarray] = field(init=False, default_factory=dict)  # read buffer
    _back: Dict[str, np.ndarray] = field(init=False, default_factory=dict)   # write buffer (next)
    _deposits: Dict[str, np.ndarray] = field(init=False, default_factory=dict)  # staging for deposit

    @classmethod
    def from_config(cls, width: int, height: int, pheromone_config=None):
        """Create PheromoneField from configuration."""
        if pheromone_config:
            return cls(
                width=width,
                height=height,
                types=pheromone_config.types or [],
                evaporation=pheromone_config.evaporation_rate,
                alpha=pheromone_config.diffusion_alpha,
                allow_dynamic_types=pheromone_config.allow_dynamic_types
            )
        else:
            # Use defaults
            return cls(
                width=width,
                height=height,
                types=["trail", "hunger", "alarm"],
                evaporation=0.01,
                alpha=0.1,
                allow_dynamic_types=True
            )

    def __post_init__(self) -> None:
        w, h = _ensure_2d(self.width, self.height)
        for t in self.types:
            self._alloc_type(t, w, h)
        log.info(
            "PheromoneField initialized w=%d h=%d types=%s evap=%.3f alpha=%.3f",
            w, h, list(self.types), self.evaporation, self.alpha
        )

    # ---------- Public API ----------

    def add_type(self, ptype: str) -> None:
        """Add new pheromone type (idempotent)."""
        if ptype in self._front:
            return
        self._alloc_type(ptype, self.width, self.height)
        log.info("Pheromone type added: %s", ptype)

    def field_for(self, ptype: str) -> np.ndarray:
        """Get read buffer (front) for a type; raises on unknown type."""
        if ptype not in self._front:
            raise KeyError(f"Unknown pheromone type '{ptype}'")
        return self._front[ptype]

    def deposit(self, ptype: str, x: int, y: int, amount: float) -> None:
        """
        Deposit pheromone into staging buffer (applied on next update_and_swap()).
        Tolerant für Out-of-bounds (ignoriert) und negative Beträge (geclamped auf 0).
        """
        if amount <= 0:
            return
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        if ptype not in self._deposits:
            if self.allow_dynamic_types:
                self._alloc_type(ptype, self.width, self.height)
                log.debug("deposit: dynamically added type '%s'", ptype)
            else:
                raise KeyError(f"Unknown pheromone type '{ptype}'")
        self._deposits[ptype][y, x] += float(amount)

    def deposit_batch(self, ptype: str, positions: List[Tuple[int, int]], amount: float = 1.0) -> int:
        """Batch deposit same amount to multiple positions; returns how many were applied."""
        if amount <= 0:
            return 0
        if ptype not in self._deposits:
            if self.allow_dynamic_types:
                self._alloc_type(ptype, self.width, self.height)
            else:
                raise KeyError(f"Unknown pheromone type '{ptype}'")
        dep = self._deposits[ptype]
        applied = 0
        for (x, y) in positions:
            if 0 <= x < self.width and 0 <= y < self.height:
                dep[y, x] += float(amount)
                applied += 1
        return applied

    def update_and_swap(self) -> Dict[str, Dict[str, float]]:
        """
        Diffusion + Verdunstung (front -> back) je Typ, addiert Deposits, dann Swap.
        Returns per-type summary with masses before/after.
        """
        self._validate_params()
        summary: Dict[str, Dict[str, float]] = {}

        for ptype in sorted(self._front.keys()):
            f = self._front[ptype]
            b = self._back[ptype]
            d = self._deposits[ptype]

            mass_before = float(f.sum())
            # Diffuse/evaporate
            self._diffuse_evaporate_into(f, b)
            # Add deposits staged during the tick
            if d is not None:
                b += d
            # Clamp to non-negative
            np.maximum(b, 0.0, out=b)
            mass_after = float(b.sum())

            summary[ptype] = {
                "mass_before": mass_before,
                "mass_after": mass_after,
                "deposited": float(d.sum()) if d is not None else 0.0,
            }

        # Swap & clear back/deposits
        self._swap_and_clear()
        # Log summary compactly
        if log.isEnabledFor(logging.INFO):
            log.info("pheromones_tick types=%d summary=%s", len(summary), summary)
        return summary

    def stats(self) -> Dict[str, Dict[str, float]]:
        """Return simple per-type stats from front buffers."""
        out: Dict[str, Dict[str, float]] = {}
        for t, f in self._front.items():
            out[t] = {
                "min": float(f.min()) if f.size else 0.0,
                "max": float(f.max()) if f.size else 0.0,
                "sum": float(f.sum()),
                "mean": float(f.mean()) if f.size else 0.0,
            }
        return out

    def snapshot(self, include_arrays: bool = False) -> Dict[str, object]:
        """
        Serialize minimal snapshot for debugging/QA.
        include_arrays=True serializes arrays as nested lists (large).
        """
        data = {
            "width": self.width,
            "height": self.height,
            "types": sorted(self._front.keys()),
            "stats": self.stats(),
        }
        if include_arrays:
            data["fields"] = {
                t: self._front[t].tolist() for t in sorted(self._front.keys())
            }
        return data

    # ---------- Internals ----------

    def _alloc_type(self, ptype: str, w: int, h: int) -> None:
        a = np.zeros((h, w), dtype=np.float32)
        b = np.zeros((h, w), dtype=np.float32)
        d = np.zeros((h, w), dtype=np.float32)
        self._front[ptype] = a
        self._back[ptype] = b
        self._deposits[ptype] = d
        if ptype not in self.types:
            self.types.append(ptype)

    def _swap_and_clear(self) -> None:
        for t in self._front.keys():
            # swap
            self._front[t], self._back[t] = self._back[t], self._front[t]
            # clear old back (new back is previous front)
            self._back[t].fill(0.0)
            self._deposits[t].fill(0.0)

    def _validate_params(self) -> None:
        if not (0.0 <= self.evaporation < 1.0):
            raise ValueError(f"evaporation must be in [0,1), got {self.evaporation}")
        if not (0.0 <= self.alpha <= 0.25):
            # 4 neighbors * alpha + center (1 - 4a) must remain >= 0
            raise ValueError(f"alpha must be in [0,0.25], got {self.alpha}")

    def _diffuse_evaporate_into(self, front: np.ndarray, back: np.ndarray) -> None:
        """
        4-Nachbarschaft Diffusion:
            center' = (1 - 4a) * center + a*(up + down + left + right)
        Verdunstung am Ende: back *= (1 - evaporation)
        Randbedingungen: Neumann (edge replicate).
        """
        a = self.alpha
        # shift operations (edge replicated)
        up = np.roll(front, -1, axis=0)
        down = np.roll(front, 1, axis=0)
        left = np.roll(front, -1, axis=1)
        right = np.roll(front, 1, axis=1)

        # Edge replicate: overwrite the wrapped edges to simulate no-flux boundaries
        # top row: 'down' of top should be itself; bottom row: 'up' of bottom should be itself
        up[-1, :] = front[-1, :]
        down[0, :] = front[0, :]
        left[:, -1] = front[:, -1]
        right[:, 0] = front[:, 0]

        np.multiply(front, (1.0 - 4.0 * a), out=back)
        back += a * (up + down + left + right)

        # evaporation
        if self.evaporation > 0.0:
            back *= (1.0 - self.evaporation)

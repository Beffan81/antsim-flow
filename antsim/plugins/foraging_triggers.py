# FILE: antsim/plugins/foraging_triggers.py
"""Foraging trigger plugins for comprehensive ant foraging behavior."""
import logging
from typing import Any, Dict
from pluggy import HookimplMarker

hookimpl = HookimplMarker("antsim")
logger = logging.getLogger(__name__)


def _get(bb: Any, key: str, default=None):
    """Safe getter for Blackboard-like or dict-like."""
    if bb is None:
        return default
    if hasattr(bb, "get"):
        try:
            return bb.get(key, default)
        except TypeError:
            pass
    try:
        return bb[key]
    except Exception:
        return default


def _log(name: str, value: bool, **ctx) -> bool:
    """Log trigger evaluation with context."""
    logger.debug("trigger=%s result=%s ctx=%s", name, value, ctx)
    return value


@hookimpl
def register_triggers() -> Dict[str, callable]:
    """Expose foraging triggers."""
    return {
        # Social stomach state
        "social_stomach_full": social_stomach_full,
        "social_stomach_empty": social_stomach_empty,
        
        # Location state  
        "outside_nest": outside_nest,
        "near_nest_entry": near_nest_entry,
        
        # Food availability
        "food_available_nearby": food_available_nearby,
        "best_food_source_found": best_food_source_found,
        
        # Foraging phases
        "in_foraging_phase": in_foraging_phase,
        "food_search_exhausted": food_search_exhausted,
        
        # Pheromone conditions
        "pheromone_detected_simple": pheromone_gradient_available,
        "should_deposit_trail": should_deposit_trail,
    }


def social_stomach_full(bb: Any) -> bool:
    """True if social stomach is at or near capacity."""
    social = _get(bb, "social_stomach", 0)
    capacity = _get(bb, "social_stomach_capacity", 100)
    threshold = capacity * 0.8  # Consider 80% as "full"
    result = social >= threshold
    return _log("social_stomach_full", result, social=social, capacity=capacity, threshold=threshold)


def social_stomach_empty(bb: Any) -> bool:
    """True if social stomach is empty or nearly empty."""
    social = _get(bb, "social_stomach", 0)
    result = social <= 0
    return _log("social_stomach_empty", result, social=social)


def outside_nest(bb: Any) -> bool:
    """True if worker is outside the nest."""
    in_nest = _get(bb, "in_nest", False)
    result = not in_nest
    return _log("outside_nest", result, in_nest=in_nest)


def near_nest_entry(bb: Any) -> bool:
    """True if worker is near a nest entry."""
    entry_distance = _get(bb, "nearest_entry_distance", 999)
    result = entry_distance <= 2  # Within 2 cells of entry
    return _log("near_nest_entry", result, distance=entry_distance)


def food_available_nearby(bb: Any) -> bool:
    """True if food sources are detected within reasonable range."""
    food_sources = _get(bb, "food_sources_nearby", [])
    # Check for food within close range (distance <= 3)
    close_food = any(f.get("distance", 999) <= 3 for f in food_sources)
    result = close_food
    return _log("food_available_nearby", result, sources_count=len(food_sources), close_food=close_food)


def best_food_source_found(bb: Any) -> bool:
    """True if a good quality food source has been identified."""
    best_source = _get(bb, "best_food_source", None)
    if not best_source:
        result = False
    else:
        # Consider it "good" if quality > 50 and distance <= 5
        quality = best_source.get("quality", 0)
        distance = best_source.get("distance", 999)
        result = quality > 50 and distance <= 5
    return _log("best_food_source_found", result, source=best_source)


def in_foraging_phase(bb: Any, phase: str = "") -> bool:
    """True if currently in specified foraging phase."""
    current_phase = _get(bb, "foraging_phase", "idle")
    if phase:
        result = current_phase == phase
    else:
        result = current_phase != "idle"
    return _log("in_foraging_phase", result, current=current_phase, target=phase)


def food_search_exhausted(bb: Any) -> bool:
    """True if food search has been going on too long without success."""
    search_cycles = _get(bb, "food_search_cycles", 0)
    exhausted = _get(bb, "food_search_exhausted", False)
    result = search_cycles > 15 or exhausted
    return _log("food_search_exhausted", result, cycles=search_cycles, exhausted=exhausted)


def pheromone_gradient_available(bb: Any) -> bool:
    """True if a pheromone gradient is available to follow."""
    pheromone_detected = _get(bb, "pheromone_detected", False)
    pheromone_type = _get(bb, "pheromone_type", None)
    
    # Consider gradient available if any pheromone is detected
    # In future, could filter by specific pheromone types (food trail, etc.)
    result = pheromone_detected
    return _log("pheromone_gradient_available", result, 
               detected=pheromone_detected, type=pheromone_type)


def should_deposit_trail(bb: Any) -> bool:
    """True if worker should deposit pheromone trail (returning with food)."""
    foraging_phase = _get(bb, "foraging_phase", "idle")
    social_stomach = _get(bb, "social_stomach", 0)
    outside_nest = not _get(bb, "in_nest", False)
    
    # Deposit trail when returning to nest with food
    result = (foraging_phase == "returning_to_nest" and 
              social_stomach > 0 and 
              outside_nest)
    return _log("should_deposit_trail", result, 
               phase=foraging_phase, social=social_stomach, outside=outside_nest)
# FILE: antsim/plugins/core_triggers.py
# plugins/core_triggers.py
"""Core trigger plugins (pure, BB read-only)."""
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
            return bb.get(key, default)  # antsim.core.blackboard.Blackboard
        except TypeError:
            pass
    # Fallback dict
    try:
        return bb[key]
    except Exception:
        return default


def _log(name: str, value: bool, **ctx) -> bool:
    logger.debug("trigger=%s result=%s ctx=%s", name, value, ctx)
    return value


@hookimpl
def register_triggers() -> Dict[str, callable]:
    """Expose core triggers."""
    return {
        # hunger/state
        "social_hungry": social_hungry,
        "not_social_hungry": not_social_hungry,
        "individual_hungry": individual_hungry,
        "not_individual_hungry": not_individual_hungry,
        # positional/environmental
        "in_nest": in_nest,
        "not_in_nest": not_in_nest,
        "at_entry": at_entry,
        "not_at_entry": not_at_entry,
        # detection
        "food_detected": food_detected,
        "individual_hungry_neighbor_found": hungry_neighbor_found,
        "neighbor_with_food_found": neighbor_with_food_found,
        # legacy/domain parity additions
        "queen_pheromone_detected": queen_pheromone_detected,
        # Provide both canonical and legacy-cased names for unsuccessful search
        "search_for_food_unsuccessful": search_for_food_unsuccessful,
        "SearchForFoodUnsuccessful": search_for_food_unsuccessful,
        # generic helpers
        "bb_true": bb_true,
        "bb_false": bb_false,
    }


# Hunger/state triggers
def social_hungry(bb: Any) -> bool:
    v = bool(_get(bb, "social_hungry", False))
    return _log("social_hungry", v, social=_get(bb, "social_stomach"), cap=_get(bb, "social_stomach_capacity"))

def not_social_hungry(bb: Any) -> bool:
    v = not bool(_get(bb, "social_hungry", False))
    return _log("not_social_hungry", v, social=_get(bb, "social_stomach"))

def individual_hungry(bb: Any) -> bool:
    v = bool(_get(bb, "individual_hungry", False))
    return _log("individual_hungry", v, indiv=_get(bb, "individual_stomach"), thr=_get(bb, "hunger_threshold"))

def not_individual_hungry(bb: Any) -> bool:
    v = not bool(_get(bb, "individual_hungry", False))
    return _log("not_individual_hungry", v, indiv=_get(bb, "individual_stomach"), thr=_get(bb, "hunger_threshold"))


# Positional/environment triggers
def in_nest(bb: Any) -> bool:
    v = bool(_get(bb, "in_nest", False))
    return _log("in_nest", v, pos=_get(bb, "position"))

def not_in_nest(bb: Any) -> bool:
    v = not bool(_get(bb, "in_nest", False))
    return _log("not_in_nest", v, pos=_get(bb, "position"))

def at_entry(bb: Any) -> bool:
    v = bool(_get(bb, "at_entry", False))
    return _log("at_entry", v, pos=_get(bb, "position"))

def not_at_entry(bb: Any) -> bool:
    v = not bool(_get(bb, "at_entry", False))
    return _log("not_at_entry", v, pos=_get(bb, "position"))


# Detection triggers
def food_detected(bb: Any) -> bool:
    v = bool(_get(bb, "food_detected", False))
    return _log("food_detected", v, food_pos=_get(bb, "food_position"))

def hungry_neighbor_found(bb: Any) -> bool:
    v = bool(_get(bb, "individual_hungry_neighbor_found", False))
    return _log("individual_hungry_neighbor_found", v, neighbor_id=_get(bb, "hungry_neighbor_id"))

def neighbor_with_food_found(bb: Any) -> bool:
    v = bool(_get(bb, "neighbor_with_food_found", False))
    return _log("neighbor_with_food_found", v)


# Domain parity additions

def queen_pheromone_detected(bb: Any) -> bool:
    """
    True if a pheromone has been detected in BB that is assumed to originate from the queen.
    Note: Current sensors provide a generic 'pheromone_detected' and 'pheromone_position' without type.
    This trigger remains pure and BB-read-only; future sensors may add 'pheromone_type' for stricter checks.
    """
    detected = bool(_get(bb, "pheromone_detected", False))
    pos = _get(bb, "pheromone_position", None)
    # If sensors later provide a 'pheromone_type', prefer checking it equals 'hunger'
    ptype = _get(bb, "pheromone_type", None)
    if ptype is not None:
        result = detected and (ptype == "hunger")
        return _log("queen_pheromone_detected", result, pheromone_detected=detected, pheromone_type=ptype, pos=pos)
    return _log("queen_pheromone_detected", detected, pos=pos)

def search_for_food_unsuccessful(bb: Any) -> bool:
    """
    Mirror of legacy 'SearchForFoodUnsuccessful' trigger.
    Reads BB key 'search_unsuccessful' (bool).
    """
    v = bool(_get(bb, "search_unsuccessful", False))
    return _log("search_for_food_unsuccessful", v)


# Generic helper triggers
def bb_true(bb: Any, key: str = "", default: bool = False) -> bool:
    """True if key evaluates truthy. For quick wiring/tests."""
    v = bool(_get(bb, key, default)) if key else False
    return _log("bb_true", v, key=key, value=_get(bb, key))

def bb_false(bb: Any, key: str = "", default: bool = True) -> bool:
    """True if key evaluates falsy. For quick wiring/tests."""
    v = not bool(_get(bb, key, default)) if key else False
    return _log("bb_false", v, key=key, value=_get(bb, key))

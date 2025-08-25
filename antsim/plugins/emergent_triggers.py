# plugins/emergent_triggers.py
"""Emergent behavior triggers for direct communication and hunger response."""
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
    """Expose emergent behavior triggers."""
    return {
        "direct_feeding_opportunity": direct_feeding_opportunity_trigger,
        "hunger_pheromone_detected": hunger_pheromone_detected_trigger,
        "trail_following_successful": trail_following_successful_trigger,
    }


def direct_feeding_opportunity_trigger(bb: Any) -> bool:
    """True if there's an opportunity for direct tactile feeding."""
    opportunity = _get(bb, "direct_feeding_opportunity", False)
    social_food = _get(bb, "social_stomach", 0)
    has_food_and_opportunity = opportunity and social_food > 0
    return _log("direct_feeding_opportunity", has_food_and_opportunity, 
               opportunity=opportunity, social_food=social_food)


def hunger_pheromone_detected_trigger(bb: Any) -> bool:
    """True if hunger pheromones are detected and worker has food to share."""
    hunger_detected = _get(bb, "hunger_pheromone_detected", False)
    social_food = _get(bb, "social_stomach", 0)
    can_respond = hunger_detected and social_food > 0
    return _log("hunger_pheromone_detected", can_respond, 
               detected=hunger_detected, social_food=social_food)


def trail_following_successful_trigger(bb: Any) -> bool:
    """True if trail following was successful (found food)."""
    success = _get(bb, "followed_pheromone_success", False)
    return _log("trail_following_successful", success, success=success)
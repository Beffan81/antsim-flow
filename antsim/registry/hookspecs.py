"""Hook specifications for the ant simulation plugin system."""
import pluggy
from typing import Dict, Any, Optional, Tuple, List

hookspec = pluggy.HookspecMarker("antsim")


@hookspec
def register_steps():
    """Register step functions that can be used in behavior trees.
    
    Returns:
        Dict[str, callable]: Mapping of step names to functions
    """
    pass


@hookspec
def register_triggers():
    """Register trigger functions for behavior tree conditions.
    
    Returns:
        Dict[str, callable]: Mapping of trigger names to functions
    """
    pass


@hookspec
def register_sensors():
    """Register sensor functions that populate the blackboard.
    
    Returns:
        Dict[str, callable]: Mapping of sensor names to functions
    """
    pass

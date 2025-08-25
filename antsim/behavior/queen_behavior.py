"""Hard-coded Queen Behavior Tree Implementation.

This module provides a separate, simplified behavior tree specifically for queens.
Queens have minimal tasks: signal hunger, wait to be fed, and lay eggs (handled outside BT).
"""

from typing import Dict, Any
from .bt import TreeBuilder, Node


def get_queen_behavior_tree_spec() -> Dict[str, Any]:
    """Returns hard-coded queen behavior tree specification.
    
    Queen behavior is minimal:
    1. If hungry -> signal hunger (no movement)
    2. Otherwise -> idle (wait passively)
    
    Egg laying is handled separately in main.py, not in the behavior tree.
    """
    return {
        "type": "selector",
        "name": "QueenRootBehavior",
        "children": [
            {
                "type": "sequence",
                "name": "QueenHungerSignaling",
                "children": [
                    {
                        "type": "condition",
                        "name": "CheckQueenHungry",
                        "triggers": ["individual_hungry"],
                        "logic": "AND"
                    },
                    {
                        "type": "step",
                        "name": "SignalHunger",
                        "stepName": "signal_hunger",
                        "params": {}
                    }
                ]
            },
            {
                "type": "step",
                "name": "QueenIdle",
                "stepName": "idle",
                "params": {}
            }
        ]
    }


def build_queen_behavior_tree(plugin_manager) -> Node:
    """Build the hard-coded queen behavior tree.
    
    Args:
        plugin_manager: Plugin manager for tree building
        
    Returns:
        Root node of the queen behavior tree
    """
    spec = get_queen_behavior_tree_spec()
    builder = TreeBuilder(plugin_manager)
    return builder.build(spec)
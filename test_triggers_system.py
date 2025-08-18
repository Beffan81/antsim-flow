# test_triggers_system.py
"""Smoke test for trigger plugins and evaluator."""
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from antsim.registry.manager import PluginManager
from antsim.core.blackboard import Blackboard
from antsim.core.triggers_evaluator import TriggersEvaluator

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


def main():
    """Run trigger evaluation tests."""
    log.info("=== Trigger System Test ===")
    pm = PluginManager(dev_mode=True)
    pm.discover_and_register()
    te = TriggersEvaluator(pm)

    # Prepare a BB resembling a worker state
    bb = Blackboard(agent_id=42)
    bb.set("position", [7, 3])
    bb.set("in_nest", False)
    bb.set("at_entry", True)
    bb.set("individual_stomach", 20)
    bb.set("hunger_threshold", 50)
    bb.set("social_stomach", 0)
    bb.set("social_stomach_capacity", 100)
    bb.set("individual_hungry", True)
    bb.set("social_hungry", True)
    bb.set("food_detected", False)
    bb.set("individual_hungry_neighbor_found", True)
    bb.set("neighbor_with_food_found", False)
    bb.commit()

    # Evaluate single triggers
    for t in ["social_hungry", "not_social_hungry", "individual_hungry", "in_nest", "at_entry",
              "food_detected", "individual_hungry_neighbor_found", "neighbor_with_food_found"]:
        res = te.evaluate(t, bb)
        log.info("trigger=%s -> %s", t, res)

    # Evaluate combined gates
    te.evaluate_task_gate(
        task_name="FeedNeighbor",
        trigger_names=["not_social_hungry", "individual_hungry_neighbor_found"],
        blackboard=bb,
        logic="AND",
    )
    te.evaluate_task_gate(
        task_name="FindFood",
        trigger_names=["social_hungry", "food_detected"],
        blackboard=bb,
        logic="AND",
    )
    log.info("Trigger tests finished")


if __name__ == "__main__":
    main()

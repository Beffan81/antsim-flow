"""Test script to verify blackboard and sensors runner functionality."""
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from antsim.registry.manager import PluginManager
from antsim.core.blackboard import Blackboard
from antsim.core.worker import Worker
from antsim.core.sensors_runner import SensorsRunner

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_blackboard():
    """Test blackboard functionality."""
    logger.info("\n=== Testing Blackboard ===")
    
    # Create blackboard
    bb = Blackboard(agent_id=1)
    
    # Test basic get/set
    bb.set('position', [10, 20])
    bb.set('energy', 80)
    bb.set('hungry', True)
    
    logger.info(f"Position: {bb.get('position')}")
    logger.info(f"Energy: {bb.get('energy')}")
    logger.info(f"Hungry: {bb.get('hungry')}")
    
    # Test diff tracking
    logger.info(f"\nChanges before commit: {bb.diff()}")
    
    # Commit changes
    committed = bb.commit()
    logger.info(f"Committed changes: {committed}")
    logger.info(f"Changes after commit: {bb.diff()}")
    
    # Make new changes
    bb.set('energy', 70)
    bb.set('position', [11, 20])
    logger.info(f"\nNew changes: {bb.diff()}")
    
    # Test rollback
    bb.rollback()
    logger.info(f"After rollback - Energy: {bb.get('energy')}, Position: {bb.get('position')}")
    
    # Test JSON serialization
    bb.set('test_data', {'nested': {'value': 42}, 'list': [1, 2, 3]})
    state = bb.to_dict()
    logger.info(f"\nExported state: {state}")
    
    # Test subscribe
    def on_energy_change(agent_id, key, value):
        logger.info(f"CALLBACK: Agent {agent_id} energy changed to {value}")
    
    bb.subscribe('energy', on_energy_change)
    bb.set('energy', 60)
    
    logger.info("\nBlackboard test completed successfully!")


def test_worker():
    """Test worker with blackboard."""
    logger.info("\n=== Testing Worker ===")
    
    # Worker configuration
    config = {
        'energy': 100,
        'max_energy': 100,
        'stomach_capacity': 100,
        'social_stomach_capacity': 100,
        'hunger_threshold': 50
    }
    
    # Create worker
    worker = Worker(worker_id=1, position=(5, 5), config=config)
    
    # Test property access
    logger.info(f"Worker: {worker}")
    logger.info(f"Position: {worker.position}")
    logger.info(f"Energy: {worker.energy}")
    
    # Test state summary
    summary = worker.get_state_summary()
    logger.info(f"\nState summary: {summary}")
    
    # Test sensor update
    sensor_data = {
        'food_detected': True,
        'food_position': [10, 10],
        'pheromone_detected': False,
        'individual_stomach': 40  # Below threshold
    }
    
    worker.update_from_sensors(sensor_data)
    
    # Check updated state
    logger.info(f"\nAfter sensor update:")
    logger.info(f"Food detected: {worker.blackboard.get('food_detected')}")
    logger.info(f"Individual hungry: {worker.blackboard.get('individual_hungry')}")
    
    # Get changes
    changes = worker.blackboard.diff()
    logger.info(f"\nChanges: {changes}")
    
    logger.info("\nWorker test completed successfully!")


def test_sensors_runner():
    """Test sensors runner with plugin system."""
    logger.info("\n=== Testing Sensors Runner ===")
    
    # Create plugin manager
    pm = PluginManager(dev_mode=True)
    pm.discover_and_register()
    
    # Create sensors runner
    runner = SensorsRunner(pm)
    
    # List available sensors
    available = runner.get_available_sensors()
    logger.info(f"Available sensors: {available}")
    
    if not available:
        logger.warning("No sensors available, skipping runner test")
        return
    
    # Create test worker
    config = {'energy': 100, 'stomach_capacity': 100, 'social_stomach_capacity': 100, 'hunger_threshold': 50}
    worker = Worker(worker_id=2, position=(10, 10), config=config)
    
    # Mock environment
    class MockEnvironment:
        def __init__(self):
            self.width = 50
            self.height = 50
            self.cycle_count = 1
    
    env = MockEnvironment()
    
    # Run all sensors once
    changes1 = runner.update_worker(worker, env)
    logger.info(f"\nWorker updated with changes: {changes1}")

    # Run again in same tick (same env.cycle_count) -> should be idempotent (no changes)
    changes2 = runner.update_worker(worker, env)
    assert not changes2, f"Expected no changes on second run in same tick, got: {changes2}"
    logger.info("Idempotency check passed (no changes on second run in same tick)")
    
    # Update worker with sensor data
    changes = runner.update_worker(worker, env)
    logger.info(f"\nWorker updated with changes: {changes}")
    
    # Test selective sensors
    def only_position_sensors(name):
        return 'position' in name
    
    selective_data = runner.run_selective(worker, env, only_position_sensors)
    logger.info(f"\nSelective sensor data (position only): {selective_data}")
    
    logger.info("\nSensors runner test completed successfully!")


def main():
    """Run all tests."""
    logger.info("Starting blackboard system tests")
    
    try:
        test_blackboard()
        test_worker()
        test_sensors_runner()
        
        logger.info("\n=== ALL TESTS PASSED ===")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

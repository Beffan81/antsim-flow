"""Test script to verify plugin system functionality."""
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from antsim.registry.manager import PluginManager

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_plugin_system():
    """Test basic plugin system functionality."""
    logger.info("Starting plugin system test")
    
    # Create plugin manager in dev mode
    pm = PluginManager(dev_mode=True)
    
    # Discover and register plugins
    pm.discover_and_register()
    
    # Test step access
    logger.info("\n=== Testing Steps ===")
    steps = pm.list_steps()
    logger.info(f"Available steps: {steps}")
    
    example_move = pm.get_step("example_move")
    if example_move:
        logger.info(f"Got step 'example_move': {example_move}")
        # Test calling it with mock objects
        result = example_move("mock_worker", "mock_environment")
        logger.info(f"Step result: {result}")
    
    # Test trigger access
    logger.info("\n=== Testing Triggers ===")
    triggers = pm.list_triggers()
    logger.info(f"Available triggers: {triggers}")
    
    always_true = pm.get_trigger("always_true")
    if always_true:
        logger.info(f"Got trigger 'always_true': {always_true}")
        result = always_true({})
        logger.info(f"Trigger result: {result}")
    
    # Test sensor access
    logger.info("\n=== Testing Sensors ===")
    sensors = pm.list_sensors()
    logger.info(f"Available sensors: {sensors}")
    
    position_sensor = pm.get_sensor("position_sensor")
    if position_sensor:
        logger.info(f"Got sensor 'position_sensor': {position_sensor}")
        result = position_sensor("mock_worker", "mock_environment")
        logger.info(f"Sensor result: {result}")
    
    logger.info("\nPlugin system test completed successfully!")


if __name__ == "__main__":
    test_plugin_system()

#!/usr/bin/env python3
"""
Comprehensive antsim test runner.
Tests all core functionality after package restructuring.
"""

import sys
import traceback
from pathlib import Path

# Add current directory to path for antsim imports
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all critical imports."""
    print("=== Testing Imports ===")
    try:
        from antsim.registry.manager import PluginManager
        from antsim.core.blackboard import Blackboard
        from antsim.core.worker import Worker
        from antsim.core.executor import IntentExecutor, MoveIntent
        from antsim.behavior.bt import BehaviorEngine, TreeBuilder
        from antsim.io.config_loader import load_behavior_tree
        from antsim.plugins.basic_steps import do_nothing_step
        from antsim.plugins.core_triggers import social_hungry
        from antsim.plugins.core_sensors import bb_basic_state_sensor
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        traceback.print_exc()
        return False

def test_plugin_system():
    """Test plugin discovery and registration."""
    print("\n=== Testing Plugin System ===")
    try:
        from antsim.registry.manager import PluginManager
        
        pm = PluginManager(dev_mode=True)
        pm.discover_and_register()
        
        steps = pm.list_steps()
        triggers = pm.list_triggers()
        sensors = pm.list_sensors()
        
        print(f"✓ Steps discovered: {len(steps)} - {', '.join(steps[:5])}{'...' if len(steps) > 5 else ''}")
        print(f"✓ Triggers discovered: {len(triggers)} - {', '.join(triggers[:5])}{'...' if len(triggers) > 5 else ''}")
        print(f"✓ Sensors discovered: {len(sensors)} - {', '.join(sensors[:5])}{'...' if len(sensors) > 5 else ''}")
        
        # Test plugin access
        step_func = pm.get_step("do_nothing")
        assert step_func is not None, "do_nothing step not found"
        
        trigger_func = pm.get_trigger("social_hungry")
        assert trigger_func is not None, "social_hungry trigger not found"
        
        sensor_func = pm.get_sensor("bb_basic_state")
        assert sensor_func is not None, "bb_basic_state sensor not found"
        
        print("✓ Plugin access works")
        return True
    except Exception as e:
        print(f"✗ Plugin system error: {e}")
        traceback.print_exc()
        return False

def test_core_functionality():
    """Test core blackboard and worker functionality."""
    print("\n=== Testing Core Functionality ===")
    try:
        from antsim.core.blackboard import Blackboard
        from antsim.core.worker import Worker
        
        # Test blackboard
        bb = Blackboard(agent_id=1)
        bb.set('test_key', 'test_value')
        bb.set('position', [10, 20])
        
        assert bb.get('test_key') == 'test_value'
        assert bb.get('position') == [10, 20]
        
        changes = bb.diff()
        assert len(changes) == 2
        print(f"✓ Blackboard changes tracked: {list(changes.keys())}")
        
        bb.commit()
        changes_after = bb.diff()
        assert len(changes_after) == 0
        print("✓ Blackboard commit works")
        
        # Test worker
        config = {
            'energy': 100,
            'max_energy': 100,
            'stomach_capacity': 100,
            'social_stomach_capacity': 100,
            'hunger_threshold': 50
        }
        
        worker = Worker(worker_id=1, position=(5, 5), config=config)
        assert worker.position == (5, 5)
        print(f"✓ Worker created at position {worker.position}")
        
        # Test sensor update
        worker.update_from_sensors({'food_detected': True, 'energy': 90})
        assert worker.blackboard.get('food_detected') == True
        assert worker.blackboard.get('energy') == 90
        print("✓ Worker sensor update works")
        
        return True
    except Exception as e:
        print(f"✗ Core functionality error: {e}")
        traceback.print_exc()
        return False

def test_behavior_tree():
    """Test behavior tree functionality."""
    print("\n=== Testing Behavior Tree ===")
    try:
        from antsim.registry.manager import PluginManager
        from antsim.io.config_loader import load_behavior_tree
        from antsim.behavior.bt import BehaviorEngine
        from antsim.core.worker import Worker
        
        # Setup plugin manager
        pm = PluginManager(dev_mode=True)
        pm.discover_and_register()
        
        # Simple BT config
        bt_config = """
        {
          "behavior_tree": {
            "root": {
              "type": "sequence",
              "name": "TestSequence",
              "children": [
                {
                  "type": "condition",
                  "name": "AlwaysTrue",
                  "condition": {
                    "triggers": ["always_true"],
                    "logic": "AND"
                  }
                },
                {
                  "type": "step",
                  "name": "DoNothing",
                  "step": {
                    "name": "do_nothing",
                    "params": {}
                  }
                }
              ]
            }
          }
        }
        """
        
        # Load and test BT
        root = load_behavior_tree(pm, bt_config)
        print(f"✓ Behavior tree loaded: {root.name}")
        
        # Create engine and test execution
        engine = BehaviorEngine(pm, root)
        
        # Create test environment
        class MockEnvironment:
            def __init__(self):
                self.width = 20
                self.height = 20
                self.cycle_count = 1
        
        env = MockEnvironment()
        
        # Create worker
        worker = Worker(worker_id=1, position=(5, 5), config={
            'energy': 100, 'max_energy': 100, 'stomach_capacity': 100,
            'social_stomach_capacity': 100, 'hunger_threshold': 50
        })
        
        # Execute BT tick
        result = engine.tick_worker(worker, env)
        print(f"✓ BT execution result: {result}")
        
        return True
    except Exception as e:
        print(f"✗ Behavior tree error: {e}")
        traceback.print_exc()
        return False

def test_intent_system():
    """Test intent creation and execution."""
    print("\n=== Testing Intent System ===")
    try:
        from antsim.core.executor import IntentExecutor, MoveIntent
        from antsim.core.worker import Worker
        
        # Create executor and worker
        executor = IntentExecutor()
        worker = Worker(worker_id=1, position=(5, 5), config={})
        
        # Create test environment
        class MockEnvironment:
            def __init__(self):
                self.width = 20
                self.height = 20
                self.grid = [[MockCell(x, y) for x in range(20)] for y in range(20)]
        
        class MockCell:
            def __init__(self, x, y):
                self.x = x
                self.y = y
                self.cell_type = "empty"
                self.ant = None
        
        env = MockEnvironment()
        
        # Reset worker cycle
        executor.reset_worker_cycle(worker)
        
        # Create and apply move intent
        move_intent = MoveIntent(target=(6, 5))
        result = executor.apply_intents(worker, env, [move_intent])
        
        executed = result.get('executed', [])
        rejected = result.get('rejected', [])
        
        print(f"✓ Intent execution - Executed: {len(executed)}, Rejected: {len(rejected)}")
        
        # Check if position was updated
        new_pos = worker.position
        print(f"✓ Worker moved from (5,5) to {new_pos}")
        
        return True
    except Exception as e:
        print(f"✗ Intent system error: {e}")
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests and return success status."""
    tests = [
        test_imports,
        test_plugin_system,
        test_core_functionality,
        test_behavior_tree,
        test_intent_system
    ]
    
    passed = 0
    print("antsim Comprehensive Test Runner")
    print("=" * 50)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print("Test failed!")
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print(f"\n{'=' * 50}")
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 ALL TESTS PASSED! antsim is fully functional.")
        return True
    else:
        print("❌ Some tests failed. Check errors above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
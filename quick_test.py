#!/usr/bin/env python3
"""Quick test to identify antsim issues."""

import sys
import traceback

def test_basic_imports():
    """Test if basic modules can be imported."""
    print("=== Testing Basic Imports ===")
    try:
        import sys
        from pathlib import Path
        
        # Add current directory to path for antsim imports
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Test registry import
        from antsim.registry.manager import PluginManager
        print("✓ PluginManager import OK")
        
        # Test core imports
        from antsim.core.blackboard import Blackboard
        from antsim.core.worker import Worker
        print("✓ Core imports OK")
        
        # Test behavior imports
        from antsim.behavior.bt import BehaviorEngine
        print("✓ Behavior imports OK")
        
        # Test plugin imports
        from antsim.plugins.basic_steps import do_nothing_step
        print("✓ Plugin imports OK")
        
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
        
        print(f"✓ Found {len(steps)} steps: {steps}")
        print(f"✓ Found {len(triggers)} triggers: {triggers}")
        print(f"✓ Found {len(sensors)} sensors: {sensors}")
        
        if not steps:
            print("⚠ Warning: No steps found")
        if not triggers:
            print("⚠ Warning: No triggers found")
        if not sensors:
            print("⚠ Warning: No sensors found")
            
        return True
    except Exception as e:
        print(f"✗ Plugin system error: {e}")
        traceback.print_exc()
        return False

def test_blackboard():
    """Test blackboard functionality."""
    print("\n=== Testing Blackboard ===")
    try:
        from antsim.core.blackboard import Blackboard
        
        bb = Blackboard(agent_id=1)
        bb.set('test_key', 'test_value')
        bb.set('position', [10, 20])
        
        assert bb.get('test_key') == 'test_value'
        assert bb.get('position') == [10, 20]
        
        changes = bb.diff()
        print(f"✓ Blackboard changes: {changes}")
        
        bb.commit()
        changes_after = bb.diff()
        assert not changes_after
        
        print("✓ Blackboard functionality OK")
        return True
    except Exception as e:
        print(f"✗ Blackboard error: {e}")
        traceback.print_exc()
        return False

def test_worker():
    """Test worker functionality."""
    print("\n=== Testing Worker ===")
    try:
        from antsim.core.worker import Worker
        
        config = {
            'energy': 100,
            'max_energy': 100,
            'stomach_capacity': 100,
            'social_stomach_capacity': 100,
            'hunger_threshold': 50
        }
        
        worker = Worker(worker_id=1, position=(5, 5), config=config)
        print(f"✓ Worker created: {worker}")
        
        # Test state access
        pos = worker.position
        assert pos == (5, 5)
        print(f"✓ Worker position: {pos}")
        
        # Test state update
        worker.update_from_sensors({'food_detected': True})
        assert worker.blackboard.get('food_detected') == True
        print("✓ Worker sensor update OK")
        
        return True
    except Exception as e:
        print(f"✗ Worker error: {e}")
        traceback.print_exc()
        return False

def test_config_loading():
    """Test config loading functionality."""
    print("\n=== Testing Config Loading ===")
    try:
        from antsim.registry.manager import PluginManager
        from antsim.io.config_loader import load_behavior_tree
        
        pm = PluginManager(dev_mode=True)
        pm.discover_and_register()
        
        # Test with basic config string
        basic_config = """
        {
          "behavior_tree": {
            "root": {
              "type": "step",
              "name": "test_step",
              "step": {
                "name": "do_nothing",
                "params": {}
              }
            }
          }
        }
        """
        
        root = load_behavior_tree(pm, basic_config)
        print(f"✓ Config loaded, root node: {root}")
        
        return True
    except Exception as e:
        print(f"✗ Config loading error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Starting antsim quick test...\n")
    
    tests = [
        test_basic_imports,
        test_plugin_system,
        test_blackboard,
        test_worker,
        test_config_loading
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n=== Summary ===")
    print(f"Passed: {passed}/{len(tests)} tests")
    
    if passed == len(tests):
        print("✓ All tests passed! antsim core appears to be working.")
        return 0
    else:
        print("✗ Some tests failed. See errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
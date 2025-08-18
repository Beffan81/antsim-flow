#!/usr/bin/env python3
"""
Test script for Step 2 - Start mechanism verification
Tests the /start, /status, and /stop endpoints with a minimal simulation config.
"""

import json
import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_minimal_simulation():
    """Test with minimal simulation config"""
    # Minimal simulation config that should work
    test_config = {
        "simulation": {
            "environment": {
                "width": 100,
                "height": 100,
                "entry_positions": [[50, 50]]
            },
            "agent": {
                "energy": 100,
                "max_energy": 100,
                "stomach_capacity": 50,
                "social_stomach_capacity": 50,
                "hunger_threshold": 30
            },
            "behavior_tree": {
                "root": {
                    "type": "step",
                    "name": "test_move",
                    "step": {
                        "name": "move",
                        "params": {}
                    }
                }
            }
        },
        "options": {
            "format": "json"
        }
    }
    
    print("=== Testing /start endpoint ===")
    try:
        response = requests.post(f"{BASE_URL}/start", json=test_config)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get("ok") and "run_id" in result:
            run_id = result["run_id"]
            pid = result.get("pid")
            print(f"✓ Successfully started simulation with run_id: {run_id}, pid: {pid}")
            
            # Test status endpoint
            print(f"\n=== Testing /status/{run_id} ===")
            status_response = requests.get(f"{BASE_URL}/status/{run_id}")
            status_result = status_response.json()
            print(f"Status response: {json.dumps(status_result, indent=2)}")
            
            # Wait a moment
            print("Waiting 2 seconds...")
            time.sleep(2)
            
            # Check status again
            status_response = requests.get(f"{BASE_URL}/status/{run_id}")
            status_result = status_response.json()
            print(f"Status after 2s: {json.dumps(status_result, indent=2)}")
            
            # Test stop endpoint
            print(f"\n=== Testing /stop/{run_id} ===")
            stop_response = requests.post(f"{BASE_URL}/stop/{run_id}")
            stop_result = stop_response.json()
            print(f"Stop response: {json.dumps(stop_result, indent=2)}")
            
            if stop_result.get("ok"):
                print("✓ Successfully stopped simulation")
            else:
                print("⚠ Stop failed or process already exited")
                
        else:
            print("✗ Failed to start simulation")
            if "error" in result:
                print(f"Error: {result['error']}")
                
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to backend. Make sure it's running on http://127.0.0.1:8000")
        print("Start with: python start_backend.py")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    
    return True

def test_plugins_first():
    """Test if plugins endpoint works first"""
    print("=== Testing /plugins endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/plugins")
        result = response.json()
        print(f"Available plugins: {json.dumps(result, indent=2)}")
        
        steps = result.get("steps", [])
        if not steps:
            print("⚠ No steps available - this might cause start failures")
        else:
            print(f"✓ Found {len(steps)} steps")
            
        return True
    except Exception as e:
        print(f"✗ Plugins test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing antsim backend Step 2 functionality...")
    print("Make sure backend is running with: python start_backend.py\n")
    
    # Test plugins first
    if not test_plugins_first():
        sys.exit(1)
        
    print()
    
    # Test start/status/stop
    if test_minimal_simulation():
        print("\n✓ All Step 2 tests passed!")
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)
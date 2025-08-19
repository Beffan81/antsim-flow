#!/usr/bin/env python3
"""Run all available antsim tests to identify issues."""

import sys
import subprocess
import os
from pathlib import Path

def run_test_file(test_file):
    """Run a test file and return success status."""
    print(f"\n{'='*50}")
    print(f"Running: {test_file}")
    print('='*50)
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, timeout=30)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✓ {test_file} PASSED")
            return True
        else:
            print(f"✗ {test_file} FAILED (return code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ {test_file} TIMEOUT")
        return False
    except Exception as e:
        print(f"✗ {test_file} ERROR: {e}")
        return False

def main():
    """Run all test files."""
    # Find all test files
    test_files = [
        "quick_test.py",
        "test_plugin_system.py", 
        "test_blackboard_system.py",
        "test_triggers_system.py"
    ]
    
    print("antsim Test Runner")
    print("="*50)
    
    results = {}
    for test_file in test_files:
        if Path(test_file).exists():
            results[test_file] = run_test_file(test_file)
        else:
            print(f"⚠ Test file not found: {test_file}")
            results[test_file] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_file, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_file}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
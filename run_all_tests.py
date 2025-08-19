#!/usr/bin/env python3
"""
Master test runner for all AntSim tests
Runs health check followed by comprehensive test suite
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print('='*60)
    
    try:
        result = subprocess.run(command, check=False, text=True)
        success = result.returncode == 0
        
        print(f"{'✅' if success else '❌'} {description}: {'PASSED' if success else 'FAILED'}")
        return success
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False

def main():
    """Run all tests in sequence"""
    print("🚀 AntSim Complete Test Suite")
    print("="*60)
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    test_results = []
    
    # 1. Health Check (mandatory)
    success = run_command(
        [sys.executable, "codespace_health_check.py"],
        "Environment Health Check"
    )
    test_results.append(("Health Check", success))
    
    if not success:
        print("\n❌ Health check failed - aborting remaining tests")
        print("Please fix environment issues before proceeding")
        return False
    
    # 2. Core AntSim Tests
    if os.path.exists("antsim_test_runner.py"):
        success = run_command(
            [sys.executable, "antsim_test_runner.py"],
            "AntSim Core Functionality"
        )
        test_results.append(("Core Tests", success))
    
    # 3. Backend API Tests
    if os.path.exists("tests/test_backend_api.py"):
        success = run_command(
            [sys.executable, "-m", "unittest", "tests.test_backend_api"],
            "Backend API Tests"
        )
        test_results.append(("Backend API", success))
    
    # 4. Frontend Integration Tests
    if os.path.exists("tests/test_frontend_integration.py"):
        success = run_command(
            [sys.executable, "-m", "unittest", "tests.test_frontend_integration"],
            "Frontend Integration Tests"
        )
        test_results.append(("Frontend Integration", success))
    
    # 5. End-to-End Tests
    if os.path.exists("tests/test_integration_e2e.py"):
        success = run_command(
            [sys.executable, "-m", "unittest", "tests.test_integration_e2e"],
            "End-to-End Integration Tests"
        )
        test_results.append(("E2E Tests", success))
    
    # 6. Frontend Build Test
    if os.path.exists("package.json"):
        success = run_command(
            ["npm", "run", "build"],
            "Frontend Production Build"
        )
        test_results.append(("Frontend Build", success))
    
    # 7. TypeScript Check
    if os.path.exists("tsconfig.json"):
        success = run_command(
            ["npx", "tsc", "--noEmit"],
            "TypeScript Compilation Check"
        )
        test_results.append(("TypeScript", success))
    
    # Final Report
    print("\n" + "="*60)
    print("📊 FINAL TEST REPORT")
    print("="*60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, success in test_results if success)
    failed_tests = total_tests - passed_tests
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:<10} {test_name}")
    
    print(f"\nSummary: {passed_tests}/{total_tests} tests passed")
    
    if failed_tests == 0:
        print("🎉 ALL TESTS PASSED! Project is fully functional.")
        return True
    else:
        print(f"❌ {failed_tests} test(s) failed. Please review and fix issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
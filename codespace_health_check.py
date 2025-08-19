#!/usr/bin/env python3
"""
Comprehensive health check for AntSim in GitHub Codespaces
Tests all components from environment setup to full simulation workflow
"""

import os
import sys
import subprocess
import requests
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class HealthChecker:
    def __init__(self):
        self.results = {}
        self.backend_url = "http://127.0.0.1:8000"
        self.frontend_url = "http://127.0.0.1:5173"
        self.backend_process = None
        self.frontend_process = None
        
    def log(self, test_name: str, status: str, message: str = ""):
        """Log test result"""
        status_symbol = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "INFO": "ℹ"}
        print(f"{status_symbol.get(status, '?')} {test_name}: {message}")
        self.results[test_name] = {"status": status, "message": message}
        
    def run_command(self, command: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """Run command and return success, stdout, stderr"""
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                cwd=os.getcwd()
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout}s"
        except Exception as e:
            return False, "", str(e)

    def test_system_requirements(self):
        """Test basic system requirements"""
        print("\n=== 1. System Requirements ===")
        
        # Python version
        python_version = sys.version_info
        if python_version >= (3, 8):
            self.log("Python Version", "PASS", f"Python {python_version.major}.{python_version.minor}")
        else:
            self.log("Python Version", "FAIL", f"Python {python_version.major}.{python_version.minor} < 3.8")
            
        # Node.js version
        success, stdout, stderr = self.run_command(["node", "--version"])
        if success:
            version = stdout.strip()
            self.log("Node.js", "PASS", version)
        else:
            self.log("Node.js", "FAIL", "Node.js not available")
            
        # pip availability
        success, _, _ = self.run_command(["pip", "--version"])
        self.log("pip", "PASS" if success else "FAIL", "pip available" if success else "pip not found")
        
        # npm availability
        success, _, _ = self.run_command(["npm", "--version"])
        self.log("npm", "PASS" if success else "FAIL", "npm available" if success else "npm not found")
        
        # Write permissions
        try:
            with tempfile.NamedTemporaryFile(delete=True) as f:
                f.write(b"test")
            self.log("Write Permissions", "PASS", "Temporary file creation works")
        except Exception as e:
            self.log("Write Permissions", "FAIL", str(e))

    def test_dependencies(self):
        """Test dependency installation"""
        print("\n=== 2. Dependencies ===")
        
        # Python dependencies
        if os.path.exists("requirements.txt"):
            success, stdout, stderr = self.run_command(["pip", "install", "-r", "requirements.txt"], timeout=120)
            self.log("Python Dependencies", "PASS" if success else "FAIL", 
                    "requirements.txt installed" if success else stderr[:100])
        else:
            self.log("Python Dependencies", "WARN", "requirements.txt not found")
            
        # Node dependencies
        if os.path.exists("package.json"):
            success, stdout, stderr = self.run_command(["npm", "install"], timeout=180)
            self.log("Node Dependencies", "PASS" if success else "FAIL",
                    "package.json installed" if success else stderr[:100])
        else:
            self.log("Node Dependencies", "WARN", "package.json not found")

    def test_antsim_core(self):
        """Test antsim core functionality"""
        print("\n=== 3. AntSim Core ===")
        
        # Test imports
        try:
            sys.path.insert(0, os.getcwd())
            import antsim
            self.log("AntSim Import", "PASS", "antsim module imported")
        except ImportError as e:
            self.log("AntSim Import", "FAIL", str(e))
            return
            
        # Run core tests if available
        if os.path.exists("antsim_test_runner.py"):
            success, stdout, stderr = self.run_command(["python", "antsim_test_runner.py"], timeout=60)
            self.log("AntSim Core Tests", "PASS" if success else "FAIL",
                    "All core tests passed" if success else stderr[:100])
        else:
            self.log("AntSim Core Tests", "WARN", "antsim_test_runner.py not found")

    def start_backend(self) -> bool:
        """Start backend server"""
        if not os.path.exists("start_backend.py"):
            self.log("Backend Start", "FAIL", "start_backend.py not found")
            return False
            
        try:
            self.backend_process = subprocess.Popen(
                ["python", "start_backend.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for backend to start
            for i in range(30):  # 30 seconds timeout
                try:
                    response = requests.get(f"{self.backend_url}/plugins", timeout=2)
                    if response.status_code == 200:
                        self.log("Backend Start", "PASS", f"Backend running on port 8000")
                        return True
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
                
            self.log("Backend Start", "FAIL", "Backend failed to start within 30s")
            return False
        except Exception as e:
            self.log("Backend Start", "FAIL", str(e))
            return False

    def test_backend_api(self):
        """Test backend API endpoints"""
        print("\n=== 4. Backend API ===")
        
        if not self.start_backend():
            return
            
        endpoints = [
            ("GET", "/plugins", "Plugin Discovery"),
            ("GET", "/docs", "API Documentation"),
        ]
        
        for method, endpoint, name in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{self.backend_url}{endpoint}", timeout=5)
                else:
                    response = requests.post(f"{self.backend_url}{endpoint}", timeout=5)
                    
                if response.status_code == 200:
                    self.log(name, "PASS", f"Status {response.status_code}")
                else:
                    self.log(name, "FAIL", f"Status {response.status_code}")
            except Exception as e:
                self.log(name, "FAIL", str(e))

    def test_simulation_workflow(self):
        """Test complete simulation workflow"""
        print("\n=== 5. Simulation Workflow ===")
        
        # Validation config format
        validation_config = {
            "environment": {
                "width": 50,
                "height": 50,
                "entry_positions": [[25, 25]]
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
                    "step": {"name": "move", "params": {}}
                }
            }
        }
        
        # Start payload format (wraps validation config)
        start_payload = {
            "simulation": validation_config,
            "options": {"format": "json"}
        }
        
        try:
            # Validate config
            response = requests.post(f"{self.backend_url}/validate", 
                                   json=validation_config, timeout=10)
            if response.status_code == 200:
                self.log("Config Validation", "PASS", "Config is valid")
            else:
                self.log("Config Validation", "FAIL", f"Status {response.status_code}")
                return
                
            # Start simulation
            response = requests.post(f"{self.backend_url}/start", 
                                   json=start_payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("ok") and "run_id" in result:
                    run_id = result["run_id"]
                    self.log("Simulation Start", "PASS", f"Started with run_id {run_id}")
                    
                    # Test status
                    time.sleep(2)
                    status_response = requests.get(f"{self.backend_url}/status/{run_id}", timeout=5)
                    if status_response.status_code == 200:
                        self.log("Status Check", "PASS", "Status endpoint working")
                    else:
                        self.log("Status Check", "FAIL", f"Status {status_response.status_code}")
                    
                    # Stop simulation
                    stop_response = requests.post(f"{self.backend_url}/stop/{run_id}", timeout=5)
                    if stop_response.status_code == 200:
                        self.log("Simulation Stop", "PASS", "Simulation stopped")
                    else:
                        self.log("Simulation Stop", "FAIL", f"Status {stop_response.status_code}")
                else:
                    self.log("Simulation Start", "FAIL", "Invalid start response")
            else:
                self.log("Simulation Start", "FAIL", f"Status {response.status_code}")
                
        except Exception as e:
            self.log("Simulation Workflow", "FAIL", str(e))

    def test_frontend_build(self):
        """Test frontend build"""
        print("\n=== 6. Frontend Build ===")
        
        if not os.path.exists("package.json"):
            self.log("Frontend Build", "FAIL", "package.json not found")
            return
            
        # Test build
        success, stdout, stderr = self.run_command(["npm", "run", "build"], timeout=120)
        self.log("Frontend Build", "PASS" if success else "FAIL",
                "Build successful" if success else stderr[:100])
        
        # Test dev server start (just check if it can start, don't wait)
        try:
            process = subprocess.Popen(
                ["npm", "run", "dev"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(10)  # Give it more time to start in Codespaces
            if process.poll() is None:  # Still running
                self.log("Frontend Dev Server", "PASS", "Dev server can start")
                process.terminate()
                process.wait(timeout=10)
            else:
                _, stderr = process.communicate()
                self.log("Frontend Dev Server", "FAIL", f"Dev server failed: {stderr[:100]}")
        except Exception as e:
            self.log("Frontend Dev Server", "FAIL", str(e))

    def test_codespaces_integration(self):
        """Test Codespaces-specific features"""
        print("\n=== 7. Codespaces Integration ===")
        
        # Check if running in Codespaces
        is_codespaces = os.getenv("CODESPACES") == "true"
        self.log("Codespaces Environment", "INFO", 
                "Running in Codespaces" if is_codespaces else "Not in Codespaces")
        
        # Check port forwarding (if in Codespaces)
        if is_codespaces:
            codespace_name = os.getenv("CODESPACE_NAME", "unknown")
            github_codespaces_port_forwarding_domain = os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
            
            if github_codespaces_port_forwarding_domain:
                public_url = f"https://{codespace_name}-8000.{github_codespaces_port_forwarding_domain}"
                try:
                    response = requests.get(f"{public_url}/plugins", timeout=10)
                    self.log("Public Port Access", "PASS" if response.status_code == 200 else "FAIL",
                            f"Backend accessible via {public_url}")
                except Exception as e:
                    self.log("Public Port Access", "WARN", f"Cannot test public access: {str(e)}")
            else:
                self.log("Public Port Access", "WARN", "Port forwarding domain not available")

    def cleanup(self):
        """Clean up processes"""
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
            except Exception:
                pass
                
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
            except Exception:
                pass

    def generate_report(self):
        """Generate final report"""
        print("\n" + "="*50)
        print("HEALTH CHECK SUMMARY")
        print("="*50)
        
        total_tests = len(self.results)
        passed = sum(1 for r in self.results.values() if r["status"] == "PASS")
        failed = sum(1 for r in self.results.values() if r["status"] == "FAIL")
        warnings = sum(1 for r in self.results.values() if r["status"] == "WARN")
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Warnings: {warnings} ⚠")
        
        if failed > 0:
            print("\n🚨 FAILED TESTS:")
            for name, result in self.results.items():
                if result["status"] == "FAIL":
                    print(f"  ✗ {name}: {result['message']}")
        
        if warnings > 0:
            print("\n⚠️  WARNINGS:")
            for name, result in self.results.items():
                if result["status"] == "WARN":
                    print(f"  ⚠ {name}: {result['message']}")
                    
        # Overall status
        if failed == 0:
            print(f"\n🎉 ALL CRITICAL TESTS PASSED! Project is ready for development.")
            return True
        else:
            print(f"\n❌ {failed} critical issues found. Please fix before proceeding.")
            return False

    def run_all(self):
        """Run all health checks"""
        print("🔍 AntSim GitHub Codespaces Health Check")
        print("=" * 50)
        
        try:
            self.test_system_requirements()
            self.test_dependencies()
            self.test_antsim_core()
            self.test_backend_api()
            self.test_simulation_workflow()
            self.test_frontend_build()
            self.test_codespaces_integration()
            
            return self.generate_report()
        finally:
            self.cleanup()

def main():
    checker = HealthChecker()
    success = checker.run_all()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
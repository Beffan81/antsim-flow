#!/usr/bin/env python3
"""
Comprehensive API endpoint tests for antsim backend
"""

import unittest
import requests
import json
import time
import subprocess
import os
import signal
from typing import Optional

class TestBackendAPI(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Start backend server for testing"""
        cls.base_url = "http://127.0.0.1:8000"
        cls.backend_process = None
        
        if os.path.exists("start_backend.py"):
            cls.backend_process = subprocess.Popen(
                ["python", "start_backend.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for backend to start
            for _ in range(30):
                try:
                    response = requests.get(f"{cls.base_url}/plugins", timeout=2)
                    if response.status_code == 200:
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
            else:
                raise Exception("Backend failed to start within 30 seconds")
    
    @classmethod
    def tearDownClass(cls):
        """Stop backend server"""
        if cls.backend_process:
            cls.backend_process.terminate()
            cls.backend_process.wait(timeout=10)
    
    def test_plugins_endpoint(self):
        """Test /plugins endpoint"""
        response = requests.get(f"{self.base_url}/plugins")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("steps", data)
        self.assertIn("triggers", data)
        self.assertIn("sensors", data)
        self.assertIsInstance(data["steps"], list)
        self.assertIsInstance(data["triggers"], list)
        self.assertIsInstance(data["sensors"], list)
    
    def test_validate_endpoint_valid_config(self):
        """Test /validate endpoint with valid config"""
        valid_config = {
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
                    "step": {"name": "random_move", "params": {}}
                }
            }
        }
        
        response = requests.post(f"{self.base_url}/validate", json=valid_config)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get("ok", False))
    
    def test_validate_endpoint_invalid_config(self):
        """Test /validate endpoint with invalid config"""
        invalid_config = {
            "environment": {"width": 50, "height": 50},
            "behavior_tree": {
                "root": {
                    "type": "step",
                    "name": "nonexistent_step",
                    "step": {"name": "nonexistent_step", "params": {}}
                }
            }
        }
        
        response = requests.post(f"{self.base_url}/validate", json=invalid_config)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertFalse(data.get("ok", True))
        self.assertIn("missing_steps", data)
    
    def test_start_stop_simulation_workflow(self):
        """Test complete start/stop simulation workflow"""
        config = {
            "simulation": {
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
                        "step": {"name": "random_move", "params": {}}
                    }
                }
            },
            "options": {"format": "json"}
        }
        
        # Start simulation
        start_response = requests.post(f"{self.base_url}/start", json=config)
        self.assertEqual(start_response.status_code, 200)
        
        start_data = start_response.json()
        self.assertTrue(start_data.get("ok", False))
        self.assertIn("run_id", start_data)
        self.assertIn("pid", start_data)
        
        run_id = start_data["run_id"]
        
        # Check status
        status_response = requests.get(f"{self.base_url}/status/{run_id}")
        self.assertEqual(status_response.status_code, 200)
        
        status_data = status_response.json()
        self.assertIn("state", status_data)
        self.assertIn(status_data["state"], ["running", "exited"])
        
        # Stop simulation
        stop_response = requests.post(f"{self.base_url}/stop/{run_id}")
        self.assertEqual(stop_response.status_code, 200)
        
        stop_data = stop_response.json()
        self.assertTrue(stop_data.get("ok", False))
    
    def test_status_nonexistent_run(self):
        """Test status endpoint with nonexistent run_id"""
        response = requests.get(f"{self.base_url}/status/nonexistent-run-id")
        self.assertEqual(response.status_code, 404)
    
    def test_stop_nonexistent_run(self):
        """Test stop endpoint with nonexistent run_id"""
        response = requests.post(f"{self.base_url}/stop/nonexistent-run-id")
        self.assertEqual(response.status_code, 404)
    
    def test_docs_endpoint(self):
        """Test API documentation endpoint"""
        response = requests.get(f"{self.base_url}/docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
    
    def test_openapi_schema(self):
        """Test OpenAPI schema endpoint"""
        response = requests.get(f"{self.base_url}/openapi.json")
        self.assertEqual(response.status_code, 200)
        
        schema = response.json()
        self.assertIn("openapi", schema)
        self.assertIn("paths", schema)
        self.assertIn("/plugins", schema["paths"])
        self.assertIn("/start", schema["paths"])
        self.assertIn("/status/{run_id}", schema["paths"])
        self.assertIn("/stop/{run_id}", schema["paths"])

if __name__ == "__main__":
    unittest.main()
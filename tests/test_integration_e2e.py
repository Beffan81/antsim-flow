#!/usr/bin/env python3
"""
End-to-end integration tests for complete AntSim workflow
"""

import unittest
import subprocess
import time
import requests
import os
import json
import tempfile
from pathlib import Path

class TestE2EIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Setup complete environment"""
        cls.backend_url = "http://127.0.0.1:8000"
        cls.backend_process = None
        
        # Start backend
        if os.path.exists("start_backend.py"):
            cls.backend_process = subprocess.Popen(
                ["python", "start_backend.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for backend
            for _ in range(30):
                try:
                    response = requests.get(f"{cls.backend_url}/plugins", timeout=2)
                    if response.status_code == 200:
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
            else:
                raise Exception("Backend failed to start")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        if cls.backend_process:
            cls.backend_process.terminate()
            cls.backend_process.wait(timeout=10)
    
    def test_default_ant_behavior_config(self):
        """Test the default ant behavior configuration from JSON"""
        
        # Default configuration with required behavior_tree
        default_config = {
            "simulation": {
                "environment": {
                    "width": 50,
                    "height": 50,
                    "pheromone_evaporation_rate": 1,
                    "cell_size": 20,
                    "movement_directions": [[0, 1], [1, 0], [0, -1], [-1, 0]],
                    "spiral": {
                        "max_steps": 100,
                        "directions": [[1, 0], [0, -1], [-1, 0], [0, 1]],
                        "spiral_steps_before_warning": 100,
                        "spiral_distance_increment_factor_range": [1.2, 1.7],
                        "spiral_max_directions": 4
                    },
                    "search": {"max_distance": 20},
                    "entry_positions": [[25, 25]]
                },
                "behavior_tree": {
                    "root": {
                        "type": "step",
                        "name": "default_behavior",
                        "step": {"name": "random_move", "params": {}}
                    }
                },
                "queen": {
                    "position": [25, 25],
                    "energy": 100,
                    "max_energy": 200,
                    "stomach_capacity": 150,
                    "pheromone_strength": 2,
                    "energy_increase_rate": 8,
                    "egg_laying_interval": 10,
                    "hunger_threshold": 20,
                    "hunger_pheromone_strength": 2,
                    "reduction_rate": 1,
                    "initial_energy_for_laying_eggs": 100,
                    "energy_after_laying_eggs": 50,
                    "stomach_depletion_rate": 1
                },
                "brood": {
                    "energy": 50,
                    "max_energy": 100,
                    "stomach_capacity": 75,
                    "social_stomach_capacity": 0,
                    "pheromone_strength": 2,
                    "reduction_rate": 0.5,
                    "hunger_threshold": 30,
                    "hunger_pheromone_strength": 2,
                    "energy_increase_rate": 3,
                    "stomach_depletion_rate": 1
                },
                "default_ant": {
                    "energy": 100,
                    "max_energy": 100,
                    "stomach_capacity": 100,
                    "social_stomach_capacity": 100,
                    "pheromone_strength": 2,
                    "reduction_rate": 1,
                    "hunger_threshold": 50,
                    "hunger_pheromone_strength": 2,
                    "energy_increase_rate": 5,
                    "stomach_depletion_rate": 1,
                    "behavior": {
                        "max_spiral_steps": 100,
                        "search_distance": 20,
                        "spiral_max_directions": 4
                    },
                    "steps_map": {
                        "find_entry": "find_entry",
                        "move_to_entry": "move_to_entry",
                        "leave_nest": "leave_nest",
                        "enter_nest": "enter_nest"
                    },
                    "triggers_definitions": {
                        "social_hungry": {
                            "conditions": ["social_hungry"],
                            "logic": "AND"
                        },
                        "in_nest": {
                            "conditions": ["in_nest"],
                            "logic": "AND"
                        }
                    },
                    "tasks": [
                        {
                            "name": "EnterNest",
                            "priority": 3,
                            "steps": ["enter_nest"],
                            "triggers": ["not_social_hungry", "at_entry", "not_in_nest"],
                            "logic": "AND",
                            "max_retries": 3
                        }
                    ]
                },
                "ants": {"num_ants": 2},
                "food_sources": [
                    {"position": [3, 3], "amount": 1000},
                    {"position": [15, 15], "amount": 1000}
                ],
                "simulation": {
                    "screen_width": 1600,
                    "screen_height": 1200,
                    "cell_size": 20,
                    "colors": {
                        "background": [255, 255, 255],
                        "empty": [200, 200, 200],
                        "wall": [128, 128, 128],
                        "entry": [0, 255, 255],
                        "queen": [255, 0, 0],
                        "ant": [0, 0, 0],
                        "food": [0, 255, 0],
                        "pheromone": [255, 255, 0],
                        "dashboard_background": [50, 50, 50],
                        "text": [255, 255, 255]
                    }
                },
                "rates": {
                    "ant_energy_reduction_rate": 1,
                    "queen_energy_reduction_rate": 1
                }
            },
            "options": {"format": "json"}
        }
        
        # Test validation
        response = requests.post(f"{self.backend_url}/validate", 
                               json=default_config["simulation"])
        self.assertEqual(response.status_code, 200)
        
        validation_result = response.json()
        if not validation_result.get("ok", False):
            self.fail(f"Default configuration validation failed: {validation_result}")
        
        # Test simulation start
        response = requests.post(f"{self.backend_url}/start", 
                               json=default_config)
        self.assertEqual(response.status_code, 200)
        
        start_result = response.json()
        self.assertTrue(start_result.get("ok", False), 
                       f"Simulation start failed: {start_result}")
        
        run_id = start_result["run_id"]
        
        # Let simulation run for a few seconds
        time.sleep(5)
        
        # Check status
        response = requests.get(f"{self.backend_url}/status/{run_id}")
        self.assertEqual(response.status_code, 200)
        
        status_result = response.json()
        self.assertIn("state", status_result)
        
        # Stop simulation
        response = requests.post(f"{self.backend_url}/stop/{run_id}")
        self.assertEqual(response.status_code, 200)
    
    def test_minimal_simulation_workflow(self):
        """Test minimal simulation that should always work"""
        minimal_config = {
            "simulation": {
                "environment": {
                    "width": 20,
                    "height": 20,
                    "entry_positions": [[10, 10]]
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
                        "name": "simple_move",
                        "step": {"name": "random_move", "params": {}}
                    }
                }
            },
            "options": {"format": "json"}
        }
        
        # Complete workflow test
        response = requests.post(f"{self.backend_url}/start", json=minimal_config)
        self.assertEqual(response.status_code, 200)
        
        result = response.json()
        self.assertTrue(result.get("ok", False))
        
        run_id = result["run_id"]
        
        # Quick status check
        time.sleep(1)
        response = requests.get(f"{self.backend_url}/status/{run_id}")
        self.assertEqual(response.status_code, 200)
        
        # Stop
        response = requests.post(f"{self.backend_url}/stop/{run_id}")
        self.assertEqual(response.status_code, 200)
    
    def test_config_persistence(self):
        """Test that configurations are properly saved and can be reused"""
        test_config = {
            "simulation": {
                "environment": {"width": 30, "height": 30, "entry_positions": [[15, 15]]},
                "agent": {
                    "energy": 80,
                    "max_energy": 80,
                    "stomach_capacity": 40,
                    "social_stomach_capacity": 40,
                    "hunger_threshold": 25
                },
                "behavior_tree": {
                    "root": {
                        "type": "step",
                        "name": "test_behavior",
                        "step": {"name": "random_move", "params": {}}
                    }
                }
            },
            "options": {"format": "json"}
        }
        
        # Start simulation
        response = requests.post(f"{self.backend_url}/start", json=test_config)
        self.assertEqual(response.status_code, 200)
        
        result = response.json()
        run_id = result["run_id"]
        config_path = result.get("config_path")
        
        # Verify config file was created
        if config_path:
            self.assertTrue(os.path.exists(config_path), 
                           "Configuration file was not created")
        
        # Stop simulation
        requests.post(f"{self.backend_url}/stop/{run_id}")
    
    def test_multiple_simulations(self):
        """Test running multiple simulations concurrently"""
        configs = []
        for i in range(3):
            config = {
                "simulation": {
                    "environment": {
                        "width": 10 + i*5,
                        "height": 10 + i*5,
                        "entry_positions": [[5 + i*2, 5 + i*2]]
                    },
                    "agent": {
                        "energy": 50 + i*10,
                        "max_energy": 50 + i*10,
                        "stomach_capacity": 25 + i*5,
                        "social_stomach_capacity": 25 + i*5,
                        "hunger_threshold": 15 + i*5
                    },
                    "behavior_tree": {
                        "root": {
                            "type": "step",
                            "name": f"test_{i}",
                            "step": {"name": "random_move", "params": {}}
                        }
                    }
                },
                "options": {"format": "json"}
            }
            configs.append(config)
        
        run_ids = []
        
        # Start all simulations
        for config in configs:
            response = requests.post(f"{self.backend_url}/start", json=config)
            self.assertEqual(response.status_code, 200)
            
            result = response.json()
            self.assertTrue(result.get("ok", False))
            run_ids.append(result["run_id"])
        
        # Let them run briefly
        time.sleep(2)
        
        # Check all are running
        for run_id in run_ids:
            response = requests.get(f"{self.backend_url}/status/{run_id}")
            self.assertEqual(response.status_code, 200)
        
        # Stop all
        for run_id in run_ids:
            response = requests.post(f"{self.backend_url}/stop/{run_id}")
            self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
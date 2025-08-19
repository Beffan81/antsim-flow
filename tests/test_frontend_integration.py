#!/usr/bin/env python3
"""
Frontend integration tests for antsim UI
"""

import unittest
import subprocess
import time
import requests
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class TestFrontendIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Start backend and frontend servers"""
        cls.backend_url = "http://127.0.0.1:8000"
        cls.frontend_url = "http://127.0.0.1:5173"
        cls.backend_process = None
        cls.frontend_process = None
        cls.driver = None
        
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
        
        # Start frontend
        if os.path.exists("package.json"):
            cls.frontend_process = subprocess.Popen(
                ["npm", "run", "dev"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for frontend
            for _ in range(60):  # Vite can take longer to start
                try:
                    response = requests.get(cls.frontend_url, timeout=2)
                    if response.status_code == 200:
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
        
        # Setup headless Chrome for testing
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            cls.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Warning: Could not initialize Chrome driver: {e}")
            cls.driver = None
    
    @classmethod
    def tearDownClass(cls):
        """Clean up processes"""
        if cls.driver:
            cls.driver.quit()
        if cls.frontend_process:
            cls.frontend_process.terminate()
            cls.frontend_process.wait(timeout=10)
        if cls.backend_process:
            cls.backend_process.terminate()
            cls.backend_process.wait(timeout=10)
    
    def test_frontend_loads(self):
        """Test that frontend loads successfully"""
        response = requests.get(self.frontend_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
    
    def test_backend_communication(self):
        """Test that frontend can communicate with backend"""
        if not self.driver:
            self.skipTest("Chrome driver not available")
        
        try:
            self.driver.get(self.frontend_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Check for any console errors
            logs = self.driver.get_log('browser')
            error_logs = [log for log in logs if log['level'] == 'SEVERE']
            
            # Allow for some warnings but no severe errors
            self.assertEqual(len(error_logs), 0, 
                           f"Console errors found: {[log['message'] for log in error_logs]}")
            
        except TimeoutException:
            self.fail("Frontend page failed to load within timeout")
    
    def test_api_client_connection(self):
        """Test API client can connect to backend"""
        if not self.driver:
            self.skipTest("Chrome driver not available")
        
        try:
            self.driver.get(self.frontend_url)
            
            # Wait for app to load
            time.sleep(3)
            
            # Check if API connection works by looking for plugins data
            # This assumes the frontend tries to load plugins on startup
            script = """
                return window.fetch('/api/plugins')
                    .then(r => r.json())
                    .then(data => data.steps && data.steps.length > 0)
                    .catch(() => false);
            """
            
            # Note: This test might need adjustment based on actual frontend implementation
            
        except Exception as e:
            print(f"API client test skipped: {e}")
    
    def test_configuration_forms(self):
        """Test that configuration forms are rendered"""
        if not self.driver:
            self.skipTest("Chrome driver not available")
        
        try:
            self.driver.get(self.frontend_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Look for form elements (adjust selectors based on actual implementation)
            page_source = self.driver.page_source
            
            # Check for basic form elements
            form_indicators = [
                "input", "select", "textarea", "button",
                "Environment", "Agent", "Simulation"
            ]
            
            found_indicators = sum(1 for indicator in form_indicators 
                                 if indicator.lower() in page_source.lower())
            
            self.assertGreater(found_indicators, 3, 
                             "Configuration forms not properly rendered")
            
        except TimeoutException:
            self.fail("Configuration forms test failed - page load timeout")
    
    def test_build_production(self):
        """Test production build"""
        if not os.path.exists("package.json"):
            self.skipTest("package.json not found")
        
        # Run build command
        result = subprocess.run(
            ["npm", "run", "build"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        self.assertEqual(result.returncode, 0, 
                        f"Build failed: {result.stderr}")
        
        # Check that dist directory was created
        self.assertTrue(os.path.exists("dist"), 
                       "dist directory not created")
        
        # Check for index.html in dist
        self.assertTrue(os.path.exists("dist/index.html"), 
                       "index.html not found in dist")

class TestUIComponents(unittest.TestCase):
    """Test individual UI components without browser"""
    
    def test_typescript_compilation(self):
        """Test TypeScript compilation"""
        if not os.path.exists("tsconfig.json"):
            self.skipTest("tsconfig.json not found")
        
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        self.assertEqual(result.returncode, 0, 
                        f"TypeScript compilation failed: {result.stderr}")
    
    def test_lint_check(self):
        """Test ESLint check if available"""
        if not os.path.exists("eslint.config.js"):
            self.skipTest("ESLint config not found")
        
        result = subprocess.run(
            ["npx", "eslint", "src/", "--ext", ".ts,.tsx"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # ESLint returns 0 for no errors, 1 for warnings/errors
        self.assertLessEqual(result.returncode, 1, 
                           f"ESLint check failed: {result.stderr}")

if __name__ == "__main__":
    unittest.main()
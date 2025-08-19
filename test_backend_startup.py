#!/usr/bin/env python3
"""
Simple test to debug backend startup issues
"""
import sys
import os
import traceback

print("Testing backend startup...")

# Test 1: Basic imports
try:
    print("1. Testing basic imports...")
    import uvicorn
    print("   ✓ uvicorn imported")
    
    import fastapi
    print("   ✓ fastapi imported")
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    print("2. Testing antsim imports...")
    import antsim
    print("   ✓ antsim imported")
    
    from antsim.registry.manager import PluginManager
    print("   ✓ PluginManager imported")
    
    print("3. Testing backend imports...")
    from antsim_backend import run_manager
    print("   ✓ run_manager imported")
    
    from antsim_backend import api
    print("   ✓ api module imported")
    
    print("4. Testing plugin manager...")
    pm = PluginManager(dev_mode=True)
    pm.discover_and_register()
    print("   ✓ PluginManager initialized and plugins discovered")
    
    print("5. Testing FastAPI app...")
    app = api.app
    print("   ✓ FastAPI app accessible")
    
    print("\n✅ All imports successful! Backend should be able to start.")
    
except Exception as e:
    print(f"\n❌ Error during import: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
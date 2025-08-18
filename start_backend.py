#!/usr/bin/env python3
"""
Startup script for antsim backend API server.
"""
import uvicorn
import sys
import os

# Add current directory to Python path to ensure antsim modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    uvicorn.run(
        "antsim_backend.api:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
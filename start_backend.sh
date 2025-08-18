#!/bin/bash
# Startup script for antsim backend
echo "Starting antsim backend API server..."
echo "Make sure you have installed dependencies: pip install -r requirements.txt"
echo "Server will be available at: http://127.0.0.1:8000"
echo "API docs will be available at: http://127.0.0.1:8000/docs"
echo ""

python start_backend.py
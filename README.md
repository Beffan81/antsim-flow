# AntSim - Ant Colony Simulation Framework

A modern, plugin-based ant colony simulation framework with React web interface.

## Features

- **Ant Colony Simulation**: Plugin-based simulation engine with behavior trees
- **Web Interface**: React frontend for configuration and visualization  
- **Real-time Control**: Start/stop simulations via REST API
- **Extensible**: Plugin system for custom behaviors, sensors, and triggers

## Quick Start

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.8+ (for simulation engine)

### Installation
```bash
# Install dependencies
npm install
pip install -r requirements.txt

# Setup antsim simulation
python setup_antsim.py
```

### Running

**Frontend & Backend:**
```bash
# Start frontend (port 5173)
npm run dev

# Start backend API (port 8000)  
python start_backend.py
```

**Simulation Only:**
```bash
# Run with default behavior tree
python -m antsim

# Run with custom config
python -m antsim --bt config/examples/forage_gradient.yaml

# Run tests
python antsim_test_runner.py
```

## API Endpoints

- `POST /start` - Start simulation
- `GET /status` - Get simulation status  
- `POST /stop` - Stop simulation
- `GET /plugins` - List available plugins

API docs: http://localhost:8000/docs

## Architecture

- **antsim/**: Core simulation engine
- **antsim_backend/**: FastAPI REST backend
- **src/**: React frontend
- **config/**: Example behavior configurations
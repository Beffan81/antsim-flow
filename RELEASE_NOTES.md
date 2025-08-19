# AntSim v0.2.0 - First Release 🐜

## Overview

We're excited to announce the first release of **AntSim** - a modern, plugin-based ant colony simulation framework with a React web interface. This release provides a complete foundation for creating, configuring, and running ant colony simulations.

## 🚀 Key Features

### Core Simulation Engine
- **Plugin Architecture**: Extensible system for custom behaviors, sensors, and triggers
- **Behavior Trees**: YAML/JSON configuration for complex ant behaviors
- **Real-time Simulation**: High-performance simulation engine with blackboard pattern
- **Pheromone System**: Advanced pheromone trail simulation with gradient navigation

### Web Interface
- **React Frontend**: Modern, responsive web interface for simulation control
- **Real-time Control**: Start, stop, and monitor simulations via web UI
- **Configuration Editor**: Visual forms for environment and agent setup
- **Behavior Tree Editor**: Interface for creating and editing behavior trees

### REST API
- **FastAPI Backend**: RESTful API for programmatic control
- **Plugin Discovery**: Automatic detection and listing of available plugins
- **Config Validation**: Real-time validation of simulation configurations
- **Run Management**: Complete lifecycle management of simulation runs

## 📦 What's Included

### Simulation Components
- **23 Built-in Steps**: Including food collection, navigation, feeding behaviors
- **19 Trigger Types**: Conditional logic for behavior activation
- **10 Sensor Types**: Environmental and internal state detection
- **Example Configurations**: Ready-to-use behavior tree examples

### Development Tools
- **Setup Script**: Automated dependency installation and verification
- **Test Suite**: Comprehensive testing framework for all components
- **Development Mode**: Hot-reload and debugging capabilities
- **Documentation**: Complete API documentation via OpenAPI/Swagger

## 🛠 Installation & Usage

### Quick Start
```bash
# Install dependencies
npm install
pip install -r requirements.txt

# Setup simulation engine
python setup_antsim.py

# Start web interface
npm run dev

# Start backend API
python start_backend.py
```

### Command Line Usage
```bash
# Run simulation with default config
python -m antsim

# Run with custom behavior tree
python -m antsim --bt config/examples/forage_gradient.yaml

# Run tests
python antsim_test_runner.py
```

## 🌟 Highlights

- **Zero-Config Setup**: Works out of the box with sensible defaults
- **Extensible Design**: Easy to add custom behaviors via plugin system
- **Cross-Platform**: Runs on Windows, macOS, and Linux
- **Modern Stack**: React + TypeScript frontend, FastAPI + Python backend
- **Production Ready**: Comprehensive error handling and logging

## 📋 API Endpoints

- `GET /` - API information and endpoints
- `GET /plugins` - List available plugins
- `POST /validate` - Validate simulation configurations
- `POST /start` - Start new simulation
- `GET /status/{run_id}` - Get simulation status
- `POST /stop/{run_id}` - Stop running simulation

## 🔧 Technical Details

- **Frontend**: React 18, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, Python 3.8+, Pydantic, Pluggy
- **Architecture**: Plugin-based, microservices-ready
- **Config Format**: YAML/JSON behavior tree configurations

## 🐛 Known Issues

- Simulation visualization is currently limited to basic status display
- Some advanced pheromone features require additional configuration
- Branch switching support is experimental
- 3 moderate npm audit vulnerabilities in development dependencies (esbuild/vite) - development-only impact

## 🚧 What's Next

- Enhanced visualization with real-time ant movement display
- Advanced analytics and performance metrics
- Extended plugin marketplace
- Mobile-responsive improvements
- Docker containerization

## 📚 Documentation

- API Documentation: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`
- Example Configs: `/config/examples/`

## 🤝 Contributing

This is an early release - feedback and contributions are welcome! Please check the documentation for setup instructions and contribution guidelines.

---

**Full Changelog**: Initial release

**Download**: Use `git clone` or download ZIP from the repository

**Requirements**: Node.js 18+, Python 3.8+
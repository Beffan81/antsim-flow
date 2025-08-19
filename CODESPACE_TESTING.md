# AntSim GitHub Codespaces Testing Guide

## Quick Start

### Automated Health Check
```bash
# Run complete health check
python codespace_health_check.py

# If health check passes, you're ready to develop!
```

### Manual Verification
```bash
# 1. Start backend (Terminal 1)
python start_backend.py

# 2. Start frontend (Terminal 2) 
npm run dev

# 3. Run specific tests (Terminal 3)
python -m unittest tests.test_backend_api
python -m unittest tests.test_frontend_integration
python -m unittest tests.test_integration_e2e
```

## Test Structure

### 1. System Health Check (`codespace_health_check.py`)
- **Purpose**: Comprehensive environment verification
- **Checks**: System requirements, dependencies, core functionality, API endpoints, simulation workflow
- **Usage**: `python codespace_health_check.py`
- **Output**: Pass/fail report with specific error details

### 2. Backend API Tests (`tests/test_backend_api.py`)
- **Purpose**: Verify all FastAPI endpoints work correctly
- **Tests**:
  - `/plugins` - Plugin discovery
  - `/validate` - Configuration validation
  - `/start` - Simulation startup
  - `/status/{run_id}` - Status monitoring
  - `/stop/{run_id}` - Simulation termination
  - `/docs` - API documentation
- **Usage**: `python -m unittest tests.test_backend_api`

### 3. Frontend Integration Tests (`tests/test_frontend_integration.py`)
- **Purpose**: Verify React frontend works with backend
- **Tests**:
  - Frontend loads successfully
  - Backend communication works
  - Configuration forms render
  - Production build succeeds
  - TypeScript compilation
  - ESLint checks (if configured)
- **Usage**: `python -m unittest tests.test_frontend_integration`
- **Requirements**: Chrome/Chromium for Selenium tests

### 4. End-to-End Tests (`tests/test_integration_e2e.py`)
- **Purpose**: Complete workflow verification
- **Tests**:
  - Default ant behavior configuration
  - Minimal simulation workflow
  - Configuration persistence
  - Multiple concurrent simulations
- **Usage**: `python -m unittest tests.test_integration_e2e`

## Codespaces-Specific Features

### Port Forwarding Verification
The health check automatically detects if running in Codespaces and tests:
- Backend port 8000 accessibility
- Frontend port 5173 accessibility  
- Public URL generation and access
- HTTPS handling

### Environment Variables
Codespaces sets these environment variables:
- `CODESPACES=true`
- `CODESPACE_NAME=<unique-name>`
- `GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN=<domain>`

### Performance Considerations
- Memory limit: Usually 4GB in free tier
- CPU limit: 2 cores
- Storage: Persistent across sessions
- Network: Generally fast, but latency varies

## Expected Results

### ✅ Healthy Environment
```
🔍 AntSim GitHub Codespaces Health Check
==================================================

=== 1. System Requirements ===
✓ Python Version: Python 3.11
✓ Node.js: v18.17.0
✓ pip: pip available
✓ npm: npm available
✓ Write Permissions: Temporary file creation works

=== 2. Dependencies ===
✓ Python Dependencies: requirements.txt installed
✓ Node Dependencies: package.json installed

=== 3. AntSim Core ===
✓ AntSim Import: antsim module imported
✓ AntSim Core Tests: All core tests passed

=== 4. Backend API ===
✓ Backend Start: Backend running on port 8000
✓ Plugin Discovery: Status 200
✓ API Documentation: Status 200

=== 5. Simulation Workflow ===
✓ Config Validation: Config is valid
✓ Simulation Start: Started with run_id abc123
✓ Status Check: Status endpoint working
✓ Simulation Stop: Simulation stopped

=== 6. Frontend Build ===
✓ Frontend Build: Build successful
✓ Frontend Dev Server: Dev server can start

=== 7. Codespaces Integration ===
ℹ Codespaces Environment: Running in Codespaces
✓ Public Port Access: Backend accessible via https://...

==================================================
HEALTH CHECK SUMMARY
==================================================
Total Tests: 15
Passed: 15 ✓
Failed: 0 ✗
Warnings: 0 ⚠

🎉 ALL CRITICAL TESTS PASSED! Project is ready for development.
```

### ❌ Common Issues

#### Backend Start Failure
```
✗ Backend Start: Backend failed to start within 30s
```
**Solutions**:
- Check Python dependencies: `pip install -r requirements.txt`
- Verify antsim core: `python antsim_test_runner.py`
- Check port 8000 availability: `lsof -i :8000`

#### Frontend Build Failure
```
✗ Frontend Build: npm ERR! peer dep missing
```
**Solutions**:
- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node.js version: `node --version` (should be 18+)
- Try alternative registry: `npm install --registry https://registry.npmjs.org/`

#### Plugin Discovery Issues
```
✗ Plugin Discovery: Status 500
⚠ No steps available - this might cause start failures
```
**Solutions**:
- Verify antsim plugins: `python -c "import antsim.plugins; print('OK')"`
- Check plugin manager: `python -c "from antsim.registry.manager import PluginManager; pm = PluginManager(); pm.discover_plugins(); print(pm.list_steps())"`

#### Port Forwarding Issues
```
⚠ Public Port Access: Cannot test public access
```
**Solutions**:
- Check Codespaces port settings in GitHub UI
- Ensure ports are set to "Public" not "Private"
- Try accessing via browser: `https://<codespace>-8000.app.github.dev`

## Troubleshooting Commands

### Backend Debugging
```bash
# Check backend logs
python start_backend.py

# Test antsim directly
python -m antsim --help

# Verify plugins
python -c "from antsim_backend.api import app; print(app.routes)"
```

### Frontend Debugging
```bash
# Check build output
npm run build 2>&1 | grep -i error

# Check TypeScript issues
npx tsc --noEmit

# Verify Vite config
npx vite --help
```

### Network Debugging
```bash
# Check port usage
ss -tulpn | grep :8000
ss -tulpn | grep :5173

# Test API directly
curl http://127.0.0.1:8000/plugins
curl http://127.0.0.1:8000/docs
```

## Continuous Integration

### Pre-commit Checks
```bash
# Run before committing
python codespace_health_check.py
npm run build
python -m unittest discover tests/
```

### Development Workflow
1. Start with health check: `python codespace_health_check.py`
2. If issues found, fix them before proceeding
3. Start development servers
4. Make changes
5. Run relevant tests before committing
6. Use GitHub Codespaces port forwarding for external testing

## Performance Optimization

### Backend
- Use minimal configurations for development
- Stop unused simulations promptly
- Monitor memory usage: `ps aux | grep python`

### Frontend
- Use `npm run dev` for development (faster than build)
- Enable hot-reload for quick iteration
- Monitor bundle size: `npm run build -- --analyze`

### Simulations
- Start with small environments (10x10 grid)
- Use fewer ants for testing (1-5 ants)
- Shorter simulation durations for development

## Security Considerations

### Port Exposure
- Backend (8000) and Frontend (5173) are exposed publicly in Codespaces
- No authentication by default - add if needed for production
- CORS is configured for development

### Data Persistence
- Temporary simulation files are created in `/tmp`
- Configuration files may contain sensitive data
- Clean up after testing: simulation files are auto-cleaned

## Support

If tests fail consistently:
1. Check GitHub Codespaces status page
2. Try restarting the Codespace
3. Review recent changes to codebase
4. Check for conflicting processes on required ports
5. Consider Codespaces resource limits (memory/CPU)

For specific AntSim issues:
1. Review `antsim_test_runner.py` output
2. Check plugin registration and discovery
3. Verify behavior tree configurations
4. Test with minimal simulation configs first
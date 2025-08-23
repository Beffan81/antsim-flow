# Release Notes

## Version 1.2.0 - Enhanced Foraging & Display Management (Aktuell)

### 🎉 Neue Features
- **Comprehensive Foraging Behavior**: Vollständiges Social Foraging System mit intelligenter Nahrungssuche
- **Pygame Display Management**: Automatisches Headless-Mode Fallback für Codespaces und Container
- **Social Stomach System**: Realistische Nahrungsaufnahme, -speicherung und -verteilung zwischen Ameisen
- **Advanced Pheromone Trails**: Intelligente Trail-Deposition beim Rückweg zum Nest mit Nahrung
- **Spiral Search Algorithm**: Systematische Exploration in Spiralmustern um das Nest herum
- **Display Diagnostic Tools**: `test_pygame_display.py` für umfassende Rendering-Problembehebung

### 🔧 Verbesserungen
- **Robustes Display Handling**: Automatische Erkennung von Display-Verfügbarkeit und SDL-Treiber-Auswahl
- **Erweiterte Plugin-Architektur**: 24 neue Foraging-spezifische Funktionen (Sensoren, Triggers, Steps)
- **Environment Variable Support**: `SDL_VIDEODRIVER`, `ANTSIM_WINDOW_HOLD`, erweiterte Logging-Optionen
- **Codespaces Kompatibilität**: Nahtlose Headless-Mode-Integration für Container-Umgebungen
- **Enhanced Error Reporting**: Detaillierte Pygame- und Display-spezifische Fehlermeldungen

### 🐜 Erweiterte Ameisen-Verhaltensweisen
- **Social Foraging Sequence**: Nest verlassen → Spiral-Suche → Nahrung sammeln → Trail-Deposition → Rückkehr
- **Pheromone Trail Following**: Intelligente Pfadfindung zu bekannten, hochwertigen Nahrungsquellen
- **Spiral Search Pattern**: Mathematisch optimierte Spiralen für systematische Umgebungsexploration
- **Social Stomach Management**: Realistische Hunger-Sättigung-Zyklen mit sozialer Nahrungsverteilung
- **Nest Entry/Exit Logic**: Intelligente Navigation zu den nächstgelegenen Nest-Ein-/Ausgängen

### 🛠️ Technische Erweiterungen
- **10 neue Sensor-Funktionen**: `spiral_search_sensor`, `food_source_sensor`, `nest_distance_sensor`, `foraging_state_sensor`
- **10 neue Trigger-Funktionen**: `social_stomach_full/empty`, `outside_nest`, `near_nest_entry`, `food_available_nearby`, etc.
- **6 neue Step-Funktionen**: `leave_nest_step`, `spiral_search_step`, `move_to_food_step`, `collect_and_eat_step`, etc.
- **Erweiterte Blackboard-Integration**: 15+ neue Schlüssel für Foraging-States, Position-Tracking, Spiral-Parameter
- **Enhanced Subprocess Management**: Bessere Environment-Variable-Behandlung in `run_manager.py`

### 🎮 Display & Rendering
- **Automatisches Headless Fallback**: `SDL_VIDEODRIVER=dummy` wird automatisch gesetzt wenn kein DISPLAY verfügbar ist
- **Display Detection Logic**: Robuste Erkennung von X11/Wayland/Container-Umgebungen
- **Window Hold Configuration**: Konfigurierbare Anzeigedauer für Debugging und Demonstration
- **Pygame Error Recovery**: Graceful Fallback wenn Display-Initialisierung fehlschlägt
- **Diagnostic Test Script**: Umfassende Display-Kompatibilitätsprüfung mit Empfehlungen

---

## Version 1.1.0 - Comprehensive Testing Framework

### 🎉 Neue Features
- **Umfassende Test-Suite**: Automatisierte Tests für alle Komponenten
- **GitHub Codespaces Unterstützung**: Vollständig konfiguriert für Cloud-Entwicklung
- **Standard-Ameisen-Verhalten**: Komplexe vorkonfigurierte Verhaltenslogik
- **Health Check System**: Automatische Umgebungsprüfung (`codespace_health_check.py`)
- **Master Test Runner**: Einheitlicher Test-Workflow (`run_all_tests.py`)
- **API-Integration**: Vollständige Backend-Frontend-Kommunikation
- **TypeScript Unterstützung**: Typsichere API-Clients und Komponenten

### 🔧 Verbesserungen
- **Erweiterte Konfiguration**: Unterstützung für komplexe Ameisen-Verhalten
- **Plugin-System**: Dynamische Ladung von Steps, Triggers und Sensors
- **Error Handling**: Robuste Fehlerbehandlung in allen Schichten
- **Performance**: Optimierte Simulation-Workflows
- **Dokumentation**: Umfassende Anleitungen und Tests

## 🧪 Test-Framework

### Neu hinzugefügte Tests
1. **Environment Health Check** (`codespace_health_check.py`)
   - System Requirements Verification
   - Dependency Installation Check
   - Port Accessibility Testing
   - Codespaces Integration Verification

2. **Backend API Tests** (`tests/test_backend_api.py`)
   - Endpoint Functionality Testing
   - Configuration Validation
   - Simulation Lifecycle Management
   - Error Response Handling

3. **Frontend Integration Tests** (`tests/test_frontend_integration.py`)
   - React Component Rendering
   - Backend Communication
   - Build Process Verification
   - TypeScript Compilation

4. **End-to-End Tests** (`tests/test_integration_e2e.py`)
   - Complete Workflow Testing
   - Default Configuration Validation
   - Multiple Simulation Management
   - Configuration Persistence

### Test-Ausführungsreihenfolge
```bash
# 1. Ersteinrichtung (einmalig)
python codespace_health_check.py

# 2. Nach Verhaltensanpassungen (Standard)
python antsim_test_runner.py
python -m unittest tests.test_backend_api
python -m unittest tests.test_integration_e2e

# 3. Nach UI-Änderungen
npm run build
python -m unittest tests.test_frontend_integration

# 4. Vollständiger Test (vor Commits)
python run_all_tests.py
```

## 🐜 Standard-Ameisen-Konfiguration

### Implementierte Verhaltensweisen
- **Soziales Verhalten**: Fütterung von Nachbarn und Königin
- **Futtersuche**: Intelligente Suchstrategien mit Pheromonen
- **Nest-Navigation**: Entry/Exit-Management
- **Task-Prioritäten**: 15 verschiedene Aufgaben mit Prioritätssystem
- **Trigger-System**: 9 Verhaltensauslöser (hungry, in_nest, food_detected, etc.)

### Konfigurierbare Parameter
- **Environment**: 50x50 Gitter, Pheromone-Verdunstung, Bewegungsrichtungen
- **Queen**: Position, Energie, Eierlegen, Pheromone-Stärke
- **Arbeiterinnen**: Energie, Magen-Kapazität, Hunger-Schwellwerte
- **Brood**: Entwicklungsstadien und Fütterungslogik

### Beispiel-Tasks (Auszug)
```yaml
Tasks:
- FeedNeighbor (Priorität 1)
- EnterNest (Priorität 3)
- CollectFood (Priorität 4)
- FindFood (Priorität 5)
- LeaveNest (Priorität 6)
- ExploreNest (Priorität 99)
```

## 🚀 Deployment & CI/CD

### GitHub Codespaces Integration
- **Automatische Einrichtung**: Sofort einsatzbereit nach dem Start
- **Port-Forwarding**: Backend (8000) und Frontend (5173) automatisch verfügbar
- **Environment Variables**: Automatische Erkennung und Konfiguration
- **Performance-Optimierung**: Memory und CPU-Usage-Monitoring

### Continuous Integration
- **Pre-commit Hooks**: Automatische Tests vor jedem Commit
- **Build Verification**: TypeScript-Compilation und Bundle-Build
- **API Testing**: Vollständige Backend-Endpoint-Verifikation
- **Cross-Component Testing**: Frontend-Backend-Integration

## 🔒 Sicherheitsverbesserungen
### Bekannte Vulnerabilities (Development Only)
- **esbuild <=0.24.2** (moderate severity)
  - Auswirkung: Nur Entwicklungsserver, nicht Production
  - Status: Akzeptabel für Development-Dependencies
- **vite 0.11.0 - 6.1.6** (moderate severity)
  - Auswirkung: Nur Build-Tool, nicht Runtime
  - Status: Wird in kommenden Updates adressiert

### Sicherheitsmaßnahmen
- **CORS-Konfiguration**: Sichere Cross-Origin-Requests
- **Input-Validation**: Robuste API-Parameter-Validierung
- **Port-Management**: Kontrollierte Exposition in Codespaces

## 🐛 Behobene Issues
- **Port-Konflikte**: Automatische Port-Erkennung und -Verwaltung
- **Module-Import-Fehler**: Korrekte Python-Path-Konfiguration
- **TypeScript-Kompilierung**: Alle Type-Definitionen vollständig
- **API-Kommunikation**: Zuverlässige Backend-Frontend-Verbindung
- **Simulation-Lifecycle**: Korrekte Start/Stop/Status-Workflows

## 📋 Technische Schulden

### Gelöst in dieser Version
- ✅ Error Handling in allen Komponenten implementiert
- ✅ API Client mit Retry-Logic erweitert
- ✅ UI Components mit Loading States ausgestattet
- ✅ Comprehensive Testing Framework etabliert
- ✅ Documentation und Setup-Guides erstellt

### Noch ausstehend
- 🔄 Behavior Tree Visualisierung (geplant für v1.2)
- 🔄 Real-time Simulation Rendering (geplant für v1.2)
- 🔄 Advanced Plugin-Editor (geplant für v1.3)
- 🔄 Performance-Profiling-Tools (geplant für v1.3)

## 🎯 Empfohlener Workflow

### Für neue Entwickler
1. `python codespace_health_check.py` - Umgebung prüfen
2. `python run_all_tests.py` - Volltest durchführen
3. `python start_backend.py` & `npm run dev` - Server starten
4. Browser öffnen: Frontend (5173) und API Docs (8000/docs)

### Für Verhaltensanpassungen
1. Konfiguration in Frontend bearbeiten
2. `python test_step2.py` - Schnelltest
3. `python -m unittest tests.test_integration_e2e` - E2E Test
4. `python run_all_tests.py` - Vollvalidierung

### Für Code-Änderungen
1. `python antsim_test_runner.py` - Core-Tests
2. Entsprechende Unit-Tests ausführen
3. `npm run build` - Build-Test (bei Frontend-Änderungen)
4. `python run_all_tests.py` - Finale Validierung

## 🔮 Ausblick Version 1.2
- Real-time Simulation Visualization
- Interactive Behavior Tree Editor
- Advanced Pheromone Visualization
- Performance Analytics Dashboard
- Plugin Development Tools

---

## Version 1.0.0 - Initial Release

### Features
- Initial release of AntSim Flow web interface
- React-based frontend with TypeScript
- FastAPI backend integration
- Basic simulation controls and configuration
- Plugin-based simulation engine with behavior trees
- REST API for programmatic control

### Core Components
- **23 Built-in Steps**: Including food collection, navigation, feeding behaviors
- **19 Trigger Types**: Conditional logic for behavior activation
- **10 Sensor Types**: Environmental and internal state detection
- **Example Configurations**: Ready-to-use behavior tree examples

### Known Issues (Resolved in v1.1.0)
- ✅ Backend API integration completed
- ✅ Simulation rendering implemented
- ✅ Configuration validation enhanced
- ✅ Error handling improved
- ✅ API client retry logic added
- ✅ UI loading states implemented
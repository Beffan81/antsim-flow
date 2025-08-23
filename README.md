# AntSim Flow - Ant Colony Simulation Framework

Eine webbasierte Benutzeroberfläche für das AntSim Ameisenkolonie-Simulationssystem mit umfassendem Test-Framework für GitHub Codespaces.

## 🚀 Schnellstart (GitHub Codespaces)

### 1. Einmalige Ersteinrichtung
```bash
# Schritt 1: Dependencies installieren (zwingend erforderlich)
pip install -r requirements.txt
npm install

# Schritt 2: Vollständige Umgebungs- und Funktionsprüfung
python run_all_tests.py
```

### 2. Entwicklungsserver starten
```bash
# Terminal 1: Backend starten
python start_backend.py

# Terminal 2: Frontend starten  
npm run dev
```

### 3. Zugriff auf die Anwendung
- **Backend API**: http://127.0.0.1:8000
- **Frontend UI**: http://127.0.0.1:8080
- **API Dokumentation**: http://127.0.0.1:8000/docs

## 🧪 Test-Workflows

### Ersteinrichtung (einmalig, nach Git-Clone)
```bash
# 1. KRITISCH: Dependencies zuerst installieren
pip install -r requirements.txt
npm install

# 2. Kompletter Systemtest (inkludiert alle anderen Tests)
python run_all_tests.py
```

### Entwicklungsworkflow

#### Nach Code-Änderungen (Schnelltest)
```bash
# Nur die relevanten Tests ausführen:
python antsim_test_runner.py              # Bei Core-Änderungen
python -m unittest tests.test_backend_api # Bei API-Änderungen  
python test_step2.py                      # Schnelle API-Validierung
```

#### Nach größeren Änderungen
```bash
# Vollständige Validierung vor Commit
python run_all_tests.py
```

#### Frontend-spezifische Tests
```bash
npx tsc --noEmit                          # TypeScript-Validierung
npm run build                             # Build-Test
python -m unittest tests.test_frontend_integration  # UI-Tests
```

### Problemdiagnose (bei Fehlern)
```bash
# 1. Isolierte Umgebungsprüfung (ohne Installation)
python codespace_health_check.py

# 2. Einzelne Test-Komponenten
python antsim_test_runner.py              # Core-System
python test_step2.py                      # API-Kommunikation
python -m unittest tests.test_integration_e2e  # End-to-End
```

## 📁 Projekt-Struktur

```
antsim-flow/
├── antsim/                    # Core Simulation Engine
│   ├── core/                  # Grundfunktionen (Environment, Worker, etc.)
│   ├── plugins/               # Verhaltens-Plugins (Steps, Triggers, Sensors)
│   └── behavior/              # Behavior Tree Engine
├── antsim_backend/            # FastAPI Backend
│   ├── api.py                 # REST API Endpoints
│   └── run_manager.py         # Simulation Management
├── src/                       # React Frontend
│   ├── components/            # UI Komponenten
│   ├── hooks/                 # React Hooks für API
│   └── lib/                   # API Client & Utilities
├── tests/                     # Umfassende Test-Suite
│   ├── test_backend_api.py    # Backend API Tests
│   ├── test_frontend_integration.py  # Frontend Tests
│   └── test_integration_e2e.py       # End-to-End Tests
├── config/examples/           # Beispiel-Konfigurationen
├── codespace_health_check.py  # Umgebungsprüfung
├── run_all_tests.py          # Master Test Runner
├── antsim_test_runner.py     # Core Funktionalitätstests
└── test_step2.py             # API Schnelltests
```

## 🐜 Standard-Ameisen-Verhalten

Das Projekt enthält mehrere vorkonfigurierte, komplexe Ameisen-Verhaltenslogiken:

### **Comprehensive Foraging Behavior** (Neu in v1.2.0)
- **Social Stomach System**: Realistische Nahrungsaufnahme und -verteilung
- **Spiral Search Algorithm**: Systematische Nahrungssuche um das Nest
- **Pheromone Trail System**: Intelligente Pfadfindung zu bekannten Nahrungsquellen
- **Nest Navigation**: Automatisches Entry/Exit-Management
- **Social Foraging Sequence**: Verlassen → Suchen → Sammeln → Rückkehr

### **Standard-Verhalten** (Basis-Konfiguration)
- **Umgebung**: 50x50 Gitter mit Nest-Eingängen
- **Königin**: Zentrale Steuerung mit Pheromonen
- **Arbeiterinnen**: Komplexe Aufgabenverteilung (15 Tasks)
- **Futtersuche**: Intelligente Suchstrategien
- **Sozialverhalten**: Fütterung und Kommunikation

### **Behavior Tree Templates**
1. **Default**: Basis-Verhalten für Entwicklung und Tests
2. **Hunger Signaling MVP**: Minimale soziale Interaktion
3. **Comprehensive Foraging**: Vollständiges Social Foraging System

### Verhalten anpassen
1. Template im Behavior Tree Editor auswählen
2. Konfiguration in `src/components/antsim-app.tsx` bearbeiten
3. Tests ausführen: `python -m unittest tests.test_integration_e2e`
4. Simulation testen: `python test_step2.py`
5. Volltest: `python run_all_tests.py`

## 🎮 Display & Rendering

### **Pygame Display Management** (Neu in v1.2.0)
- **Automatisches Headless-Mode Fallback**: Für Codespaces und Container-Umgebungen
- **Display-Verfügbarkeit-Erkennung**: Automatische Prüfung von DISPLAY-Variablen
- **SDL-Treiber-Auswahl**: Flexible Rendering-Backend-Auswahl
- **Window Hold Configuration**: Konfigurierbare Anzeigedauer

### **Environment Variables für Display-Control**
```bash
export SDL_VIDEODRIVER=dummy           # Für headless pygame
export ANTSIM_WINDOW_HOLD=10.0        # Fenster-Anzeigedauer (Sekunden)
export ANTSIM_LOG_LEVEL=DEBUG         # Erweiterte Display-Logs
```

### **Display-Diagnose**
```bash
# Display-Verfügbarkeit prüfen
python test_pygame_display.py

# Display-Environment testen
echo $DISPLAY && xdpyinfo

# Pygame-Initialisierung testen
python -c "import pygame; pygame.init(); print('OK')"
```

## 🔧 Technologien

- **Frontend**: React, TypeScript, Tailwind CSS, Vite
- **Backend**: Python, FastAPI, Uvicorn
- **Simulation**: AntSim Engine mit Plugin-System
- **Rendering**: Pygame mit SDL, Headless-Mode Support
- **Testing**: unittest, Selenium, Requests
- **Deployment**: GitHub Codespaces, Docker-ready

## 🧩 API-Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/plugins` | GET | Verfügbare Plugins auflisten |
| `/validate` | POST | Konfiguration validieren |
| `/start` | POST | Simulation starten |
| `/status/{run_id}` | GET | Simulationsstatus abfragen |
| `/stop/{run_id}` | POST | Simulation beenden |
| `/docs` | GET | API Dokumentation |

## 🔍 Fehlerbehebung

### Backend startet nicht
```bash
# Abhängigkeiten prüfen
pip install -r requirements.txt

# Core-Module testen
python antsim_test_runner.py

# Port prüfen
lsof -i :8000
```

### Frontend Build-Fehler
```bash
# Node-Module neu installieren
rm -rf node_modules
npm install

# TypeScript-Fehler prüfen
npx tsc --noEmit
```

### Simulation startet nicht
```bash
# Plugins prüfen
curl http://127.0.0.1:8000/plugins

# Minimale Konfiguration testen
python test_step2.py

# Logs prüfen
python start_backend.py  # Ausgabe beobachten
```

### **Pygame Display Issues** (Neu in v1.2.0)
```bash
# 1. Display-Diagnose ausführen
python test_pygame_display.py

# 2. Headless-Mode aktivieren
export SDL_VIDEODRIVER=dummy
export ANTSIM_WINDOW_HOLD=5.0

# 3. Display-Environment prüfen
echo $DISPLAY
xdpyinfo  # Sollte Display-Info zeigen

# 4. Pygame-Initialisierung testen
python -c "import pygame; pygame.init(); screen = pygame.display.set_mode((400,300)); print('Display OK')"

# 5. Extended Logging aktivieren
export ANTSIM_LOG_LEVEL=DEBUG
python start_backend.py  # Pygame-spezifische Logs beobachten
```

### Codespaces Port-Probleme
1. Ports auf "Public" setzen (nicht "Private")
2. Browser-Cache leeren
3. Neue Terminal-Sitzung starten

### **Codespaces Display-Unterstützung**
```bash
# Für grafische Ausgabe in Codespaces (optional)
sudo apt-get update
sudo apt-get install -y xvfb x11-utils

# Virtual Display starten
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 &

# Oder einfach headless verwenden (empfohlen)
export SDL_VIDEODRIVER=dummy
```

## 📊 Performance-Tipps

### Entwicklung
- Kleine Umgebungen verwenden (10x10 Gitter)
- Weniger Ameisen für Tests (1-5 Ameisen)
- Kurze Simulationsdauern

### Produktion
- Umgebungsgröße schrittweise erhöhen
- Memory-Usage überwachen: `ps aux | grep python`
- Simulation-Logs regelmäßig bereinigen

## 🤝 Entwicklungs-Workflow

### Neue Features
1. Feature-Branch erstellen
2. `python codespace_health_check.py` ausführen
3. Änderungen implementieren
4. Tests ausführen: `python run_all_tests.py`
5. Pull Request erstellen

### Verhaltens-Debugging
1. Minimale Konfiguration verwenden
2. Einzelne Schritte testen
3. Pheromone/Sensoren einzeln prüfen
4. Behavior Tree visualisieren (geplant)

## 📚 Weitere Dokumentation

- [Codespace Testing Guide](CODESPACE_TESTING.md)
- [Step 2 Testing](STEP2_TEST.md)
- [Release Notes](RELEASE_NOTES.md)
- [AntSim Review](ANTSIM_REVIEW.md)

## 🚀 Erweiterte Nutzung

### Kommandozeilen-Simulation
```bash
# Standard-Verhalten ausführen
python -m antsim

# Mit eigener Konfiguration
python -m antsim --bt config/examples/forage_gradient.yaml

# Plugins testen
python setup_antsim.py
```

### Continuous Integration
```bash
# Pre-commit Hook (empfohlen)
python run_all_tests.py && git commit

# GitHub Actions (vorbereitet)
# .github/workflows/test.yml wird automatisch erkannt
```

### Docker-Deployment (vorbereitet)
```bash
# Backend Container
docker build -t antsim-backend -f Dockerfile.backend .

# Frontend Container  
docker build -t antsim-frontend -f Dockerfile.frontend .
```

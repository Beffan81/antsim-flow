# Konfigurationssystem für Antsim

## Übersicht

Das neue Konfigurationssystem macht alle wichtigen Parameter konfigurierbar und eliminiert hardcodierte Werte aus dem Code.

## Konfigurationsdateien

### Standard-Konfiguration
- `config/defaults/simulation_defaults.yaml` - Enthält alle konfigurierbaren Parameter mit sensiblen Default-Werten

### Test-Konfiguration
- `config/examples/test_new_config.yaml` - Beispiel-Konfiguration mit angepassten Parametern

## Konfigurierbare Parameter

### Umgebung (`environment`)
- `width`, `height` - Umgebungsmaße
- `nest_type` - Nesttyp ("standard", "custom", "none")
- `center_nest` - Nest zentrieren

### Kolonie (`colony`)
- `queen_count`, `worker_count` - Anzahl der Agenten
- `entry_positions` - Startpositionen für Worker

### Emergentes Verhalten (`emergent_behavior`)
- `hunger_pheromone_detection_range` - Erkennungsradius für Hunger-Pheromone
- `trail_success_multiplier` - Verstärkungsfaktor bei erfolgreichem Pfad
- `trail_failure_multiplier` - Schwächungsfaktor bei gescheitertem Pfad
- `hunger_detection_threshold` - Hunger-Erkennungsschwelle
- `direct_feeding_range` - Reichweite für direktes Füttern

### Pheromone (`pheromones`)
- `evaporation_rate` - Verdunstungsrate pro Tick
- `diffusion_alpha` - Diffusionsgewicht zu 4-Nachbarn
- `types` - Verfügbare Pheromontypen
- `allow_dynamic_types` - Dynamische Typerstellung erlauben

### Simulation (`simulation`)
- `max_cycles` - Maximale Anzahl Simulationszyklen
- `tick_interval_ms` - Millisekunden zwischen Ticks
- `dashboard_update_frequency` - Dashboard-Update-Frequenz (alle N Ticks)

### Standard-Futterquellen (`default_food_sources`)
- `enabled` - Standard-Futterquellen aktivieren
- `sources` - Liste der Futterquellen mit Position und Menge

### Agenten-Konfiguration (`agent`)
- `queen_config` - Queen-spezifische Parameter (Energie, Sozialmagen, etc.)
- `worker_config` - Worker-spezifische Parameter

### Brood-Konfiguration (`brood`)
- `maturation_time` - Reifungszeit in Ticks
- `energy_conversion_rate` - Energieumwandlungsrate
- Weitere Lifecycle-Parameter

### Navigation-Konfiguration (`navigation`) - NEU in v1.3.0
- `breadcrumb_strength` - Initiale Stärke der Breadcrumb-Pheromone
- `breadcrumb_decay` - Abbaurate pro Tick (< 1.0 für Verfall)
- `path_blocked_threshold` - Anzahl blockierter Versuche vor Strategie-Wechsel
- `emergency_center_bias` - Gewichtung der Zentral-Tendenz bei Notfall-Navigation (0.0 - 1.0)

## Verwendung

### CLI
```bash
# Mit spezifischer Konfiguration
python -m antsim --bt config/examples/test_new_config.yaml

# Mit Umgebungsvariable
export ANTSIM_BT=config/examples/test_new_config.yaml
python -m antsim
```

### Standard-Verhalten
Ohne externe Konfiguration wird automatisch `config/defaults/simulation_defaults.yaml` geladen.

## Rückwärtskompatibilität

Bestehende YAML-Konfigurationsdateien funktionieren weiterhin. Fehlende Parameter werden durch Default-Werte ergänzt.

## Implementierungsdetails

### Plugin-Konfiguration
Emergente Verhaltensparameter werden über `emergent_sensors.set_emergent_config()` an die Plugins übertragen.

### Pheromone-Konfiguration
Das PheromoneField wird mit `PheromoneField.from_config()` aus der Konfiguration erstellt.

### Agent-Factory
Die AgentFactory erhält Konfigurationsparameter für Queen- und Worker-Erstellung.

## Validierung

Alle Parameter werden über Pydantic-Schemas validiert:
- Typsicherheit
- Wertebereichsprüfung
- Automatische Konvertierung
- Klare Fehlermeldungen

### Programmatischer Zugriff
```python
from antsim.io.config_loader import load_configuration

# Konfiguration laden
config = load_configuration("config/my_simulation.yaml")

# Parameter zugreifen
print(f"Worker count: {config.colony.worker_count}")
print(f"Trail multiplier: {config.emergent_behavior.trail_success_multiplier}")
print(f"Breadcrumb strength: {config.navigation.breadcrumb_strength}")

# Validierung erfolgt automatisch
try:
    config = load_configuration("invalid.yaml")
except ValidationError as e:
    print(f"Configuration error: {e}")
```

### Erweiterte Szenarien

#### Performance-Optimierung
```yaml
# Für große Umgebungen (100x100+)
simulation:
  tick_interval_ms: 50  # Schnellere Ticks
  dashboard_update_frequency: 10  # Weniger Rendering

navigation:
  breadcrumb_strength: 3.0  # Stärkere Trails für größere Distanzen
  emergency_center_bias: 0.5  # Höhere Zentral-Tendenz
```

#### Forschungs-Experimente
```yaml
# A/B-Testing: Trail-Verstärkung
emergent_behavior:
  trail_success_multiplier: 1.5  # Variante A: Konservativ
  # trail_success_multiplier: 3.0  # Variante B: Aggressiv

# Parameter-Sweeps für Optimierung
pheromones:
  evaporation_rate: 0.005  # Langsame Verdunstung
  # evaporation_rate: 0.02  # Schnelle Verdunstung
```

#### Debugging & Entwicklung
```yaml
# Minimale Simulation für schnelles Testing
environment:
  width: 20
  height: 20

colony:
  worker_count: 3

simulation:
  max_cycles: 100
  dashboard_update_frequency: 1  # Jeder Tick sichtbar
```

## Erweiterung

Neue konfigurierbare Parameter können einfach hinzugefügt werden:

1. Schema in `antsim/io/config_loader.py` erweitern
2. Default-Werte in `config/defaults/simulation_defaults.yaml` hinzufügen
3. Parameter in entsprechenden Modulen verwenden
4. Konfigurationsverteilung in `antsim/app/main.py` ergänzen

## Vollständige Parameter-Referenz

### Environment
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `width` | int | 40 | Breite der Umgebung (Zellen) |
| `height` | int | 30 | Höhe der Umgebung (Zellen) |
| `nest_type` | str | "standard" | Nesttyp ("standard", "custom", "none") |
| `center_nest` | bool | true | Nest zentrieren |

### Colony
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `queen_count` | int | 1 | Anzahl der Königinnen |
| `worker_count` | int | 5 | Anzahl der Arbeiterinnen |
| `entry_positions` | list | [[10,10], ...] | Startpositionen |

### Emergent Behavior
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `hunger_pheromone_detection_range` | int | 3 | Erkennungsradius (Zellen) |
| `trail_success_multiplier` | float | 2.0 | Verstärkung bei Erfolg |
| `trail_failure_multiplier` | float | 0.5 | Abschwächung bei Fehlschlag |
| `hunger_detection_threshold` | float | 1.1 | Hunger-Erkennungsschwelle |
| `direct_feeding_range` | int | 1 | Fütterungs-Reichweite |

### Pheromones
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `evaporation_rate` | float | 0.01 | Verdunstungsrate pro Tick |
| `diffusion_alpha` | float | 0.1 | Diffusionsgewicht |
| `types` | list | ["trail", "hunger", ...] | Verfügbare Typen |
| `allow_dynamic_types` | bool | true | Dynamische Typen erlauben |

### Navigation (NEU in v1.3.0)
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `breadcrumb_strength` | float | 2.0 | Initiale Breadcrumb-Stärke |
| `breadcrumb_decay` | float | 0.95 | Abbaurate pro Tick |
| `path_blocked_threshold` | int | 3 | Versuche vor Fallback |
| `emergency_center_bias` | float | 0.3 | Notfall-Zentral-Tendenz |

### Simulation
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `max_cycles` | int | 1000 | Maximale Zyklen |
| `tick_interval_ms` | int | 100 | Millisekunden pro Tick |
| `dashboard_update_frequency` | int | 3 | Update alle N Ticks |

### Agent (Queen/Worker)
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `energy` | int | 200/100 | Initiale Energie |
| `max_energy` | int | 200/100 | Maximale Energie |
| `social_stomach_capacity` | int | 150/100 | Sozialmagen-Kapazität |
| `hunger_threshold` | int | 75/50 | Hunger-Schwellwert |

### Brood
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `maturation_time` | int | 50 | Reifungszeit (Ticks) |
| `energy_conversion_rate` | int | 5 | Energie pro Fütterung |
| `hunger_pheromone_strength` | int | 2 | Pheromone-Stärke |

### Default Food Sources
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `enabled` | bool | true | Standard-Quellen aktivieren |
| `sources` | list | [...] | Liste mit Position/Menge |
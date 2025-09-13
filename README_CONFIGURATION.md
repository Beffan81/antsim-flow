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

## Erweiterung

Neue konfigurierbare Parameter können einfach hinzugefügt werden:

1. Schema in `antsim/io/config_loader.py` erweitern
2. Default-Werte in `config/defaults/simulation_defaults.yaml` hinzufügen
3. Parameter in entsprechenden Modulen verwenden
4. Konfigurationsverteilung in `antsim/app/main.py` ergänzen
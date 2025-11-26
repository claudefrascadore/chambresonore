# Synthèse Chambre Sonore

## 1. Plan de maintenance du code
### 1.1 Structure actuelle
- src/main.py – point d’entrée
- src/orbbec_depth_pipeline.py – pipeline Orbbec
- src/orbbec_view_depth.py – visualisation profondeur
- src/grid_ui.py – interface de contrôle (PyQt6)
- src/zone_detector.py – logique 6×6
- src/cell_config.py – JSON matrices
- config/cells.json – matrice active
- src/dmx_controller_ola.py – DMX OLA
- src/audio_player.py – audio pygame

### 1.2 Maintenance hebdomadaire
- Vérification pipeline, grille, DMX, audio.
- Vérification dépréciations Python.

### 1.3 Maintenance mensuelle
- OLA stable, PyQt6 mineur, pyorbbecsdk2, documentation.

### 1.4 Maintenance annuelle
- Nouveau venv, pip freeze.

### 1.5 Points sensibles
- OLA stable seulement.
- PyQt6/QMenu.
- Version SDK Orbbec.
- Threads PyQt6/pygame.

## 2. Plan DMX v2
### 2.1 Objectif
DMX unifié, stable, testable.

### 2.2 Architecture
- dmx_controller.py
- API: set_rgb, set_intensity, blackout

### 2.3 Règles DMX
- Universe 1
- Mapping DMX dans config/cells.json

### 2.4 Couleurs
- RGB dans JSON
- cell_id → canal_debut (R, G, B)

### 2.5 Indépendance pipeline/DMX
- ZoneDetector → événements
- dmx_controller → actions

### 2.6 Tests DMX
- test_dmx.py

## 3. Schéma global (pipeline)
```
Caméra Orbbec
     |
PipelineOrbbec
     |
ZoneDetector
   /   \
DMX     Audio
 |       |
Lumière  Son
     |
grid_ui.py (tablette)
```

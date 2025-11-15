## Projet : Chambre sonore — Résumé complet

### 1. Définition et description du projet
**Chambre sonore** est une installation interactive développée par Claude Frascadore. Elle associe **mouvement, lumière et son** dans un espace réactif organisé en une matrice **6 × 6**. Chaque cellule correspond à une zone spatiale captée par une caméra 3D Orbbec Gemini 2. Lorsqu’un corps ou un mouvement est détecté dans une cellule, le système déclenche simultanément :
- une **émission lumineuse DMX** via OLA ;
- un **événement sonore** via `pygame.mixer` ;
- une **mise à jour graphique** de la cellule dans une interface visuelle (UI).

L’objectif artistique est de transformer l’espace en un instrument collectif et sensible, où le déplacement d’un individu génère un dialogue entre lumière, son et présence. Tout le système fonctionne **localement** sous **Linux (Ubuntu MATE)**, sans dépendance cloud ni télémétrie externe.

### 2. Architecture générale
| Composant | Rôle principal | Modules concernés |
|------------|----------------|-------------------|
| **Caméra Orbbec Gemini 2** | Détection du mouvement et de la profondeur | `orbbec_input.py`, `test_orbbec_*` |
| **Analyse et filtrage** | Extraction des zones actives (6×6) | `matrice.py`, `tracker.py` |
| **Pont DMX + Audio** | Synchronisation lumière/son | `dmx_audio_bridge.py`, `dmx.py`, `audio.py`, `sound_manager.py` |
| **Interface visuelle (UI)** | Représentation graphique de la matrice, interaction et diagnostic | `grid_ui.py`, `gui.py` |
| **Application principale** | Orchestration complète, démarrage et gestion des threads | `main.py` |

---

### 3. Composants détaillés
#### a) Capture et capteur Orbbec
- SDK Python : **pyorbbecsdk 2.0.15 (Linux x86_64)** — version confirmée et testée.
- Profil actif : **1280 × 800 Y14 @ 10 fps**.
- Profondeur moyenne : ~2150 mm.
- Seuil recommandé : **2500 mm**.
- Lecture de frames stable et cohérente.

#### b) Traitement et matrice de zones
- `matrice.py` définit la grille logique (6×6) et la cartographie entre coordonnées 3D et zones.
- `tracker.py` gère le suivi temporel et la stabilisation des activations.
- La détection binaire (présence si distance < seuil) est validée pour intégration directe.

#### c) Pont DMX et audio (`dmx_audio_bridge.py`)
- Interface OLA stable, testée sur Enttec DMX USB Pro.
- Conversion `array.array('B')` validée.
- Repli automatique en mode simulation après 10 erreurs.
- Audio via `pygame.mixer` : 12 voix, gain ajustable, support complet des `.wav` (testé sur Tascam iXR).
- Grille 6×6 affichée en console avec mise à jour en temps réel.

#### d) Interface visuelle (`grid_ui.py`, `gui.py`)
- `grid_ui.py` : gère le rendu graphique des 36 cellules (états actifs/inactifs).
- `gui.py` : fenêtre interactive (pygame) affichant la matrice et les activations.
- Options de calibration visuelle (profondeur moyenne, intensité lumineuse virtuelle).
- Testée avec succès sur Linux ; adaptable à une interface tactile Android.

#### e) Modules de tests et outils
- `test_orbbec_depth.py`, `test_orbbec_fps.py`, `test_orbbec_fps_distance.py` : tests de fréquence et de latence.
- `test_orbbec_filtered.py` : filtrage expérimental.
- `dmx_controller.py` : test manuel DMX.
- `sound_manager.py` : préchargement et gestion de volume.

---

### 4. Travail complété à ce jour
- Installation et compilation du SDK Orbbec réussies (version 2.0.15 confirmée).
- Pont DMX + Audio + Capture intégré et fonctionnel.
- Données de profondeur valides (frames stables et valeurs cohérentes).
- Interface `grid_ui` pleinement opérationnelle.
- Tests audio et DMX concluants (synchronisation stable).
- Structure du projet consolidée sous `src/orbbec/`.
- Gestion des signaux d’arrêt stable.

---

### 5. Prochaines étapes (Phase 4)
1. **Calibration spatiale** : adapter la grille 6×6 aux distances réelles du capteur.
2. **Intégration temps réel** : connecter la sortie du capteur à l’interface visuelle.
3. **Affinement audio** : ajouter des transitions fluides et éviter la redondance sonore.
4. **Validation DMX** : vérifier synchronisation et canaux pour fixtures réels.
5. **Création du module principal** : `chambre_sonore_app.py` — application unifiée combinant `gui`, `bridge`, et `tracker`.

---

### 6. Commandes de référence
```bash
# Test caméra
PYTHONPATH=src python3 src/orbbec/test_depth_matrix.py

# Pont audio/lumière
PYTHONPATH=src python3 -m orbbec.dmx_audio_bridge --sensor gemini2 --fps 10 --depth-threshold 2500 --show-grid

# Interface graphique
PYTHONPATH=src python3 src/orbbec/gui.py
```

---

### 7. État du projet
Le système est **fonctionnel dans toutes ses composantes principales** (capture, traitement, DMX, audio, interface). 
Il reste à synchroniser la détection spatiale avec la représentation graphique et à calibrer les seuils de profondeur pour une interaction fluide.

➡️ Prochaine phase : **Interaction complète et calibration scénique (Phase 4)**.


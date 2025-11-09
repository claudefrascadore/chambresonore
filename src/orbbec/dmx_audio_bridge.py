# template_orbbec_dmx_audio_bridge.py
"""
Modèle Codex — orbbec.dmx_audio_bridge
Phase 3 : Chambre sonore
----------------------------------------
Pont DMX + Audio pour la matrice 6×6.
Structure :
 - Lecture capteur (orbbec.depth_test)
 - Détection des cellules actives
 - Sortie DMX (OLA ou simulation)
 - Déclenchement audio (pygame ou simulation)
 - Config JSON : mapping lumière/son
"""

TEMPLATE = {
    "module": "orbbec.dmx_audio_bridge",
    "phase": "3",
    "description": "Pont DMX+Audio 6x6 (OLA/Pygame) pour Chambre sonore",
    "version": "1.0.0",
    "dependencies": [
        "pygame>=2.5.0",
        "python-ola>=0.10.8"
    ],
    "source": "src/orbbec/dmx_audio_bridge.py",
    "config": "config/chambre_sonore_map.json",
    "notes": [
        "Simule le capteur si Orbbec n’est pas connecté.",
        "Active DMX si OLA est détecté, sinon journalise les canaux.",
        "Active audio si pygame est dispo, sinon journalise les événements sonores."
    ]
}


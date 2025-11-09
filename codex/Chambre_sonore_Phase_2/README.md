# Chambre Sonore – Captation Orbbec

Ce dépôt contient les scripts de test, de calibration et de capture utilisés pour le projet **Chambre Sonore**.  
L’environnement de développement est basé sur **Ubuntu MATE** avec le SDK **Orbbec v2.0.15** et **Python 3.12**.

---

## 🎯 Objectif

Ce module assure la captation vidéo et de profondeur avec une caméra **Orbbec Gemini 2**,  
dans le cadre d’un système interactif de **sonification spatiale**.  
Il sert à :
- tester la synchronisation des flux RGB et profondeur ;
- mesurer la stabilité des distances ;
- capturer des scènes de calibration pour les algorithmes de spatialisation.

---

## ⚙️ Environnement requis

- Ubuntu / Linux 64 bits  
- Python ≥ 3.12  
- SDK Orbbec 2.0.15 (`pyorbbecsdk-2.0.15-cp312-linux_x86_64.whl`)  
- OpenCV ≥ 4.12  
- NumPy ≥ 2.2  

### Installation de l’environnement virtuel
```bash
cd ~/Projets/Orbbec/TestPython
python3 -m venv venv
source venv/bin/activate
pip install pyorbbecsdk-2.0.15-cp312-cp312-linux_x86_64.whl opencv-python numpy
# chambresonore

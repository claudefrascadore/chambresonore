# 📘 GUIDE COMPLET – Chambre Sonore (Ubuntu MATE)

Ce guide décrit l’installation, le lancement et la maintenance du module de captation **Orbbec Gemini 2** pour le projet *Chambre Sonore*.

Auteur : **Claude Frascadore**  
Plateforme : **Ubuntu MATE / Python 3.12 / SDK Orbbec 2.0.15**

---

## 🧩 INSTALLATION INITIALE

### 1. Préparer le dossier du projet

Créer les dossiers de travail :

```bash
mkdir -p ~/Projets/Orbbec
cd ~/Projets/Orbbec
```

Cloner ton dépôt GitHub :

```bash
git clone https://github.com/claudefrascadore/chambresonore.git .
```

---

### 2. Installer Git et Python

```bash
sudo apt update
sudo apt install git python3 python3-venv -y
```

---

### 3. Ajouter le SDK Orbbec

Télécharger le fichier :
```
pyorbbecsdk-2.0.15-cp312-cp312-linux_x86_64.whl
```
et le placer dans :
```
~/Projets/Orbbec/TestPython/
```

---

### 4. Créer et installer l’environnement virtuel

Exécuter le script automatique :
```bash
cd ~/Projets/Orbbec/TestPython
./install_orbbec_env.sh
```

Ce script :
- crée le venv (`venv/`) ;
- installe le SDK Orbbec, NumPy, OpenCV ;
- teste l’importation du SDK.

---

## 🎬 LANCEMENT DU MODULE

Pour démarrer la session de test :

```bash
cd ~/Projets/Orbbec/TestPython
./run_chambre_sonore.sh
```

### Fonctionnement de la fenêtre :
- **Gauche** : flux couleur RGB  
- **Droite** : flux de profondeur colorisé  
- **En haut** : résolution et FPS  
- **Curseur (moitié droite)** : distance mesurée en mm

### Commandes :
- **Espace** → capture RGB + Depth + matrice brute  
- **Échap** → quitter proprement

Les fichiers sont enregistrés dans :
```
~/Projets/Orbbec/TestPython/captures/
```

---

## 💾 CAPTURE AUTOMATIQUE

Chaque pression sur **Espace** enregistre trois fichiers horodatés :

- `rgb_YYYYMMDD_HHMMSS.png`  
- `depth_YYYYMMDD_HHMMSS.png`  
- `depth_raw_YYYYMMDD_HHMMSS.npy`

Tous sont sauvegardés dans le dossier `captures/`.

---

## 🔄 MISE À JOUR DU CODE

### Mettre à jour ton dépôt depuis GitHub :
```bash
cd ~/Projets/Orbbec
git pull
```

### Sauvegarder une nouvelle version :
```bash
git add .
git commit -m "Mise à jour du module Orbbec"
git push
```

---

## 🧹 ENTRETIEN DU SYSTÈME

### Supprimer l’environnement virtuel :
```bash
rm -rf ~/Projets/Orbbec/TestPython/venv
```

### Le recréer :
```bash
cd ~/Projets/Orbbec/TestPython
./install_orbbec_env.sh
```

---

## 📘 STRUCTURE DU PROJET

```
~/Projets/Orbbec/
├── .git/
├── .gitignore
├── README.md
└── TestPython/
    ├── test_orbbec_final.py
    ├── install_orbbec_env.sh
    ├── run_chambre_sonore.sh
    ├── requirements.txt
    ├── README_LINUX.md
    ├── venv/
    └── captures/
```

---

## 🧠 INFOS TECHNIQUES

| Élément | Version |
|----------|----------|
| Python | 3.12 |
| Orbbec SDK | 2.0.15 |
| OpenCV | 4.12.0.88 |
| NumPy | 2.2.0 |
| OS | Ubuntu MATE 25.10 |
| Caméra | Orbbec Gemini 2 |

---

## 🧩 COMMANDES RAPIDES

| Action | Commande |
|--------|-----------|
| Installer l’environnement | `./install_orbbec_env.sh` |
| Lancer la capture | `./run_chambre_sonore.sh` |
| Quitter | `Échap` |
| Capture instantanée | `Espace` |
| Mise à jour Git | `git add . && git commit -m "Maj" && git push` |

---

## 🪶 AUTEUR ET LICENCE

Projet artistique expérimental  
**Chambre Sonore** — Claude Frascadore  
Tous droits réservés — usage personnel et recherche-création

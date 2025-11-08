#!/bin/bash
# Script d’installation pour Chambre sonore – Prototype v1
# Configure automatiquement l’environnement virtuel Python et installe les dépendances.

echo "=== Installation de l’environnement Chambre sonore ==="

# Aller dans le dossier du script
cd "$(dirname "$0")" || exit 1

# Créer l’environnement virtuel
if [ ! -d "venv" ]; then
    echo "Création de l’environnement virtuel..."
    python3 -m venv venv
else
    echo "Environnement virtuel déjà présent."
fi

# Activer le venv
source venv/bin/activate

# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances
echo "Installation des dépendances Python..."
pip install -r requirements.txt

# Vérifier OLA
if systemctl is-active --quiet olad; then
    echo "OLA est actif."
else
    echo "⚠️  OLA n’est pas actif. Lance-le avec : sudo systemctl start olad"
fi

echo "Installation terminée."
echo "Pour lancer l’application :"
echo "source venv/bin/activate && python src/main.py"

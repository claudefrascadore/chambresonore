#!/bin/bash
# Script : rebuild_venv.sh
# Projet : Chambre Sonore
# Rôle   : Récrée l'environnement virtuel Python (.venv)
#          et restaure les dépendances nécessaires à Codex et Orbbec.

echo "⚙️  Reconstruction de l'environnement virtuel (.venv)..."

# Aller dans le dossier du projet
cd "$(dirname "$0")" || exit 1

# Supprimer l'ancien venv s'il existe
if [ -d ".venv" ]; then
    echo "🧹 Suppression de l'ancien environnement..."
    rm -rf .venv
fi

# Créer le nouvel environnement
python3 -m venv .venv
source .venv/bin/activate

# Mise à jour de pip et installation des dépendances de base
pip install --upgrade pip wheel setuptools

# Paquets de base nécessaires au projet Chambre sonore
pip install pygame python-ola numpy pyqt6

# Ajout du dossier src au PYTHONPATH
if ! grep -q "PYTHONPATH" .venv/bin/activate; then
    echo "export PYTHONPATH=\$PYTHONPATH:$(pwd)/src" >> .venv/bin/activate
fi

echo "✅ Environnement virtuel prêt. Pour l’activer :"
echo "   source .venv/bin/activate"


#!/usr/bin/env bash
# ============================================================
#  Script d’installation de l’environnement Orbbec (Chambre Sonore)
#  Auteur : Claude Frascadore
#  Plateforme : Ubuntu MATE / Python 3.12
# ============================================================

set -e  # arrêt en cas d'erreur

echo "📦 Préparation de l'environnement virtuel Orbbec..."
cd "$(dirname "$0")"

# Création du venv s'il n'existe pas déjà
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Environnement virtuel créé."
else
    echo "ℹ️ Environnement virtuel déjà présent."
fi

# Activation du venv
source venv/bin/activate

echo "📂 Installation des dépendances Python..."
if [ -f "pyorbbecsdk-2.0.15-cp312-cp312-linux_x86_64.whl" ]; then
    pip install pyorbbecsdk-2.0.15-cp312-cp312-linux_x86_64.whl
else
    echo "⚠️  Le fichier .whl du SDK Orbbec est introuvable."
    echo "   Télécharge-le dans ce dossier avant d'exécuter ce script."
    deactivate
    exit 1
fi

pip install -r requirements.txt
echo "✅ Installation terminée."

# Vérification du module
echo "🧩 Vérification de l'import du SDK..."
python3 - <<'PYCODE'
import pyorbbecsdk
print(f"Orbbec SDK chargé, version {pyorbbecsdk.__version__ if hasattr(pyorbbecsdk,'__version__') else 'ok'}")
PYCODE

echo "🎉 L'environnement Orbbec est prêt à l'emploi."

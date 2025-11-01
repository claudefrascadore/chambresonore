#!/usr/bin/env bash
# ============================================================
#  Lancement du module Orbbec – Chambre Sonore
#  Auteur : Claude Frascadore
# ============================================================

cd "$(dirname "$0")"

# Vérifie la présence du venv
if [ ! -d "venv" ]; then
    echo "⚠️  Aucun environnement virtuel détecté."
    echo "   Exécute d'abord : ./install_orbbec_env.sh"
    exit 1
fi

# Active le venv
source venv/bin/activate

# Exécute le script principal en mode silencieux
echo "🎬 Lancement de la capture Orbbec..."
python3 test_orbbec_final.py 2>/dev/null

# Désactive le venv proprement
deactivate
echo "✅ Fin de la session Orbbec."

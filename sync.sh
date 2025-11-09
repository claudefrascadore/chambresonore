#!/bin/bash
# ------------------------------------------------------------
# sync.sh — Synchronisation quotidienne du projet Chambre sonore
# ------------------------------------------------------------
# 1. Met à jour le Codex local (transfert des fichiers)
# 2. Ajoute toutes les modifications à Git
# 3. Crée un commit avec message automatique horodaté
# 4. Pousse les changements vers GitHub
# ------------------------------------------------------------

# Empêche l’exécution si un script échoue
set -e

# Se place toujours dans le répertoire du script
cd "$(dirname "$0")"

# Couleur pour affichage
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m' # reset

echo -e "${CYAN}--- Étape 1 : Synchronisation du Codex ---${NC}"
python3 codex_sync.py

echo -e "${CYAN}--- Étape 2 : Ajout des fichiers modifiés ---${NC}"
git add -A

# Horodatage automatique pour le message de commit
DATE=$(date +"%Y-%m-%d %H:%M:%S")
MESSAGE="docs(codex): sync quotidienne - $DATE"

echo -e "${CYAN}--- Étape 3 : Commit ---${NC}"
git commit -m "$MESSAGE" || echo "Aucun changement à valider."

echo -e "${CYAN}--- Étape 4 : Push vers GitHub ---${NC}"
git push

echo -e "${GREEN}✓ Synchronisation terminée avec succès.${NC}"


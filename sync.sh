#!/bin/bash
# ------------------------------------------------------------
# sync.sh — Synchronisation complète du projet Chambre sonore
# ------------------------------------------------------------
# Étapes :
# 1. Incrémente automatiquement la phase dans codex/project.json
# 2. Exécute codex_sync.py pour transférer les fichiers
# 3. Ajoute toutes les modifications à Git
# 4. Committe avec message horodaté
# 5. Pousse vers GitHub
# ------------------------------------------------------------

set -e
cd "$(dirname "$0")"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

# Vérifie que bump_phase.py existe
if [[ ! -f bump_phase.py ]]; then
  echo -e "${CYAN}Création du script bump_phase.py...${NC}"
  cat > bump_phase.py << 'EOF'
#!/usr/bin/env python3
# bump_phase.py — Incrémente la phase et synchronise le Codex

import json, subprocess
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parent
meta = root / "codex" / "project.json"

def main():
    info = json.loads(meta.read_text(encoding="utf-8"))
    try:
        cur = int(info.get("phase", "1"))
    except ValueError:
        raise ValueError("Le champ 'phase' doit être numérique (ex.: \"1\").")
    info["phase"] = str(cur + 1)
    info["updated"] = datetime.now().strftime("%Y-%m-%d")
    meta.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Phase → {info['phase']}")
    subprocess.run(["python3", "codex_sync.py"], check=True)

if __name__ == "__main__":
    main()
EOF
  chmod +x bump_phase.py
fi

# --- Étape 1 : Incrémentation de la phase ---
echo -e "${CYAN}--- Étape 1 : Incrémentation de phase ---${NC}"
python3 bump_phase.py

# --- Étape 2 : Ajout Git ---
echo -e "${CYAN}--- Étape 2 : Ajout des fichiers modifiés ---${NC}"
git add -A

# --- Étape 3 : Commit avec date/heure ---
DATE=$(date +"%Y-%m-%d %H:%M:%S")
MESSAGE="docs(codex): sync quotidienne - Phase auto - $DATE"
echo -e "${CYAN}--- Étape 3 : Commit ---${NC}"
git commit -m "$MESSAGE" || echo "Aucun changement à valider."

# --- Étape 4 : Push vers GitHub ---
echo -e "${CYAN}--- Étape 4 : Push vers GitHub ---${NC}"
git push

echo -e "${GREEN}✓ Synchronisation et phase terminées avec succès.${NC}"


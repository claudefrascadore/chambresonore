#!/bin/bash
# ------------------------------------------------------------
# sync.sh — Synchronisation complète du projet Chambre sonore
# ------------------------------------------------------------
# Usage :
#   ./sync.sh          → Incrémente automatiquement la phase
#   ./sync.sh --manual → Conserve la phase actuelle (mode manuel)
# ------------------------------------------------------------

set -e
cd "$(dirname "$0")"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

MODE="auto"
[[ "$1" == "--manual" ]] && MODE="manual"

# Vérifie l’existence du bump_phase.py, le crée au besoin
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

# ------------------------------------------------------------
# Étape 1 — Synchronisation
# ------------------------------------------------------------
if [[ "$MODE" == "auto" ]]; then
  echo -e "${CYAN}--- Étape 1 : Incrémentation de la phase ---${NC}"
  python3 bump_phase.py
else
  echo -e "${CYAN}--- Étape 1 : Synchronisation manuelle ---${NC}"
  python3 codex_sync.py
fi

# ------------------------------------------------------------
# Étape 2 — Commit et push
# ------------------------------------------------------------
echo -e "${CYAN}--- Étape 2 : Préparation Git ---${NC}"
git add -A
DATE=$(date +"%Y-%m-%d %H:%M:%S")
if [[ "$MODE" == "auto" ]]; then
  MESSAGE="docs(codex): sync quotidienne (auto-phase) - $DATE"
else
  MESSAGE="docs(codex): sync quotidienne (manuel) - $DATE"
fi

git commit -m "$MESSAGE" || echo "Aucun changement à valider."
git push

echo -e "${GREEN}✓ Synchronisation terminée (${MODE}).${NC}"


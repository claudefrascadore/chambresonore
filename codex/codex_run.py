#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
codex_run.py — Générateur de modules pour Chambre Sonore
Phase 3 — Codex

Ce script automatise la création, le transfert et la mise à jour des modules Python
dans le dossier src/, à partir de modèles situés dans codex/templates/.
Chaque génération est enregistrée dans codex/Chambre_sonore_Phase_3/transfer_log.json.

Arguments principaux :
  --module <nom>        Nom complet du module à générer (ex: orbbec.dmx_audio_bridge)
  --phase <nom|num>     Phase du projet (ex: 3 ou Chambre_sonore_Phase_3)
  --keep                Conserver les fichiers existants sans les écraser
  --list-templates      Afficher la liste des modèles disponibles et quitter

Auteur : Claude Frascadore / Ève
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
import subprocess

# =====================================================================
#  Répertoires de base
# =====================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
CODEX_DIR = BASE_DIR / "codex"
SRC_DIR = BASE_DIR / "src"
LOG_DIR = CODEX_DIR / "Chambre_sonore_Phase_3"
LOG_FILE = LOG_DIR / "transfer_log.json"

# =====================================================================
#  Chargement automatique de tous les templates
#  Exemple : "template_orbbec_depth_test.py" → module "orbbec.depth_test"
# =====================================================================

TEMPLATES_DIR = CODEX_DIR / "templates"
TEMPLATE_FILES = {}

for tpl_file in TEMPLATES_DIR.glob("template_*.py"):
    # Conversion du nom de fichier vers nom de module
    # Exemple : template_orbbec_dmx_audio_bridge.py → orbbec.dmx_audio_bridge
    module_name = tpl_file.stem.replace("template_", "", 1)
    module_name = module_name.replace("_", ".", 1)
    TEMPLATE_FILES[module_name] = tpl_file.name

# =====================================================================
#  Analyse des arguments
# =====================================================================

parser = argparse.ArgumentParser(description="Générateur Codex — Chambre sonore (Phase 3)")
parser.add_argument("--module", help="Nom complet du module à générer (ex: orbbec.dmx_audio_bridge)")
parser.add_argument("--phase", default="3", help="Nom ou numéro de la phase (par défaut: 3)")
parser.add_argument("--keep", action="store_true", help="Conserver les fichiers existants")
parser.add_argument("--list-templates", action="store_true", help="Afficher la liste des modèles disponibles et quitter")
args = parser.parse_args()

# =====================================================================
#  Liste des templates disponibles
# =====================================================================

if args.list_templates:
    print("📁 Modèles disponibles :")
    for name, tpl in sorted(TEMPLATE_FILES.items()):
        print(f" - {name:35s} → {tpl}")
    sys.exit(0)

# =====================================================================
#  Vérification du module demandé
# =====================================================================

if not args.module:
    print("❌ Aucun module spécifié. Utilise --module <nom_du_module>")
    sys.exit(1)

module_name = args.module.strip()
template_name = TEMPLATE_FILES.get(module_name)

if not template_name:
    print(f"❌ Aucun modèle défini pour : {module_name}")
    print("   Utilise --list-templates pour voir les modèles disponibles.")
    sys.exit(1)

template_path = TEMPLATES_DIR / template_name
if not template_path.exists():
    print(f"❌ Modèle introuvable : {template_path}")
    sys.exit(1)

# =====================================================================
#  Préparation du chemin cible
# =====================================================================

target_file = SRC_DIR / Path(module_name.replace(".", "/") + ".py")
target_file.parent.mkdir(parents=True, exist_ok=True)

# =====================================================================
#  Copie du modèle vers le module cible
# =====================================================================

print(f"⚙️  Génération du module {module_name}…")

if target_file.exists() and args.keep:
    print(f"⏩ Fichier conservé : {target_file}")
else:
    with open(template_path, "r", encoding="utf-8") as src, open(target_file, "w", encoding="utf-8") as dst:
        shutil.copyfileobj(src, dst)
    print(f"✅ Module créé : {target_file}")

# =====================================================================
#  Journalisation de la génération
# =====================================================================

LOG_DIR.mkdir(parents=True, exist_ok=True)
if not LOG_FILE.exists():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2, ensure_ascii=False)

with open(LOG_FILE, "r", encoding="utf-8") as f:
    entries = json.load(f)

entries.append({
    "module": module_name,
    "template": template_name,
    "phase": args.phase,
    "timestamp": datetime.now().isoformat(timespec="seconds"),
    "status": "generated"
})

with open(LOG_FILE, "w", encoding="utf-8") as f:
    json.dump(entries, f, indent=2, ensure_ascii=False)

# =====================================================================
#  Git : ajout, commit et push automatique
# =====================================================================

try:
    subprocess.run(["git", "add", str(target_file), str(LOG_FILE)], check=True)
    commit_msg = f"feat(phase{args.phase}): ajout module {target_file.name}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=False)
    subprocess.run(["git", "push", "origin", "main"], check=False)
    print("🎯 Opération terminée. Module prêt :", target_file)
except Exception as e:
    print(f"⚠️  Erreur Git (non bloquante) : {e}")
    print("   Module généré localement mais non poussé.")



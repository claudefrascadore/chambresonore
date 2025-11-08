#!/usr/bin/env python3
# codex_sync.py — Modèle Machine Orchestre adapté à "Chambre sonore"
# ---------------------------------------------------------------
# Fonction : transfert et archivage local des fichiers du projet vers un Codex versionné.
# Usage :    python3 codex_sync.py
# ---------------------------------------------------------------

import json, shutil
from datetime import datetime
from pathlib import Path

# Détection du répertoire racine et du codex
root = Path(__file__).resolve().parent
codex = root / "codex"
meta_file = codex / "project.json"

# Extensions autorisées à copier (ajoute-en si nécessaire)
VALID_EXT = {".py", ".md", ".txt", ".json", ".ini", ".pas", ".pp", ".cfg"}

def sync_codex():
    # Lecture de la définition du projet
    if not meta_file.exists():
        raise FileNotFoundError(f"Fichier manquant : {meta_file}")
    info = json.loads(meta_file.read_text(encoding="utf-8"))

    project_name = info["project_name"].replace(" ", "_")
    phase = info["phase"]
    outdir = codex / f"{project_name}_Phase_{phase}"
    outdir.mkdir(parents=True, exist_ok=True)

    copied = []
    for f in root.iterdir():
        if f.is_file() and f.suffix.lower() in VALID_EXT and f.name != "codex_sync.py":
            shutil.copy2(f, outdir / f.name)
            copied.append(f.name)

    log = {
        "project": info["project_name"],
        "phase": info["phase"],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": copied
    }

    (outdir / "transfer_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"Codex mis à jour : {info['project_name']} – Phase {info['phase']} ({len(copied)} fichiers).")

if __name__ == "__main__":
    sync_codex()


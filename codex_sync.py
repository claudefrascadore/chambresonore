#!/usr/bin/env python3
# codex_sync.py — Version étendue pour "Chambre sonore"
# ---------------------------------------------------------------
# Fonction :
#  - Synchronise les fichiers principaux du projet
#  - Copie automatiquement les sources (src/, config/) vers la phase courante du Codex
#  - Archive chaque phase dans codex/Chambre_sonore_Phase_X/
# ---------------------------------------------------------------

import json, shutil
from datetime import datetime
from pathlib import Path

# Détection des chemins
root = Path(__file__).resolve().parent
codex = root / "codex"
meta_file = codex / "project.json"

# Extensions autorisées à copier (fichiers racine)
VALID_EXT = {".py", ".md", ".txt", ".json", ".ini", ".pas", ".pp", ".cfg"}

def copytree(src: Path, dst: Path):
    """Copie récursive simple sans écraser les dossiers existants."""
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            target.mkdir(exist_ok=True)
            copytree(item, target)
        else:
            shutil.copy2(item, target)

def sync_codex():
    if not meta_file.exists():
        raise FileNotFoundError(f"Fichier manquant : {meta_file}")
    info = json.loads(meta_file.read_text(encoding="utf-8"))

    project_name = info["project_name"].replace(" ", "_")
    phase = info["phase"]
    outdir = codex / f"{project_name}_Phase_{phase}"
    outdir.mkdir(parents=True, exist_ok=True)

    copied = []
    # Copie des fichiers à la racine
    for f in root.iterdir():
        if f.is_file() and f.suffix.lower() in VALID_EXT and f.name not in {"codex_sync.py", "sync.sh"}:
            shutil.copy2(f, outdir / f.name)
            copied.append(f.name)

    # Copie des dossiers importants
    for dname in ["src", "config"]:
        d = root / dname
        if d.exists() and d.is_dir():
            print(f"→ Copie du dossier {dname}/")
            dst = outdir / dname
            dst.mkdir(exist_ok=True)
            copytree(d, dst)
            copied.append(f"{dname}/")

    # Journalisation
    log = {
        "project": info["project_name"],
        "phase": info["phase"],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files_copied": copied
    }
    (outdir / "transfer_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"Codex mis à jour : {info['project_name']} – Phase {info['phase']} ({len(copied)} éléments).")

if __name__ == "__main__":
    sync_codex()


#!/usr/bin/env python3
# codex_sync.py — Version avec option --keep et journal global
# ---------------------------------------------------------------
# Fonction :
#  - Synchronise les fichiers principaux du projet
#  - Copie automatiquement src/ et config/ vers la phase courante
#  - Archive les phases précédentes dans codex/archive/
#  - Permet de garder certaines phases (--keep)
#  - Met à jour un journal global (codex/transfer_history.json)
# ---------------------------------------------------------------

import json, shutil, zipfile, sys
from datetime import datetime
from pathlib import Path

# Chemins de base
root = Path(__file__).resolve().parent
codex = root / "codex"
meta_file = codex / "project.json"
archive_dir = codex / "archive"
history_file = codex / "transfer_history.json"

# Extensions valides à copier
VALID_EXT = {".py", ".md", ".txt", ".json", ".ini", ".pas", ".pp", ".cfg"}

def copytree(src: Path, dst: Path):
    """Copie récursive sans écrasement des sous-dossiers existants."""
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            target.mkdir(exist_ok=True)
            copytree(item, target)
        else:
            shutil.copy2(item, target)

def archive_old_phases(current_phase: str, project_name: str, keep_phases=None):
    """Archive toutes les phases sauf celles à garder."""
    archive_dir.mkdir(exist_ok=True)
    for phase_dir in codex.glob(f"{project_name}_Phase_*"):
        if not phase_dir.is_dir():
            continue
        phase_num = phase_dir.name.split("_")[-1].replace("Phase", "").strip()
        if phase_dir.name.endswith(f"Phase_{current_phase}"):
            continue
        if keep_phases and phase_num in keep_phases:
            print(f"⏸ Phase {phase_num} conservée (option --keep)")
            continue
        zip_name = archive_dir / f"{phase_dir.name}.zip"
        print(f"→ Archivage de {phase_dir.name} → {zip_name.name}")
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in phase_dir.rglob("*"):
                zipf.write(file, file.relative_to(codex))
        shutil.rmtree(phase_dir)
        print(f"   ✓ {phase_dir.name} archivée et supprimée.")

def update_history(info: dict, copied: list):
    """Met à jour codex/transfer_history.json."""
    entry = {
        "phase": info["phase"],
        "project": info["project_name"],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": copied
    }
    history = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
        except Exception:
            history = []
    history.append(entry)
    history_file.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

def sync_codex(keep_phases=None):
    if not meta_file.exists():
        raise FileNotFoundError(f"Fichier manquant : {meta_file}")
    info = json.loads(meta_file.read_text(encoding="utf-8"))

    project_name = info["project_name"].replace(" ", "_")
    phase = info["phase"]
    outdir = codex / f"{project_name}_Phase_{phase}"
    outdir.mkdir(parents=True, exist_ok=True)

    copied = []
    # Copie des fichiers racine
    for f in root.iterdir():
        if f.is_file() and f.suffix.lower() in VALID_EXT and f.name not in {"codex_sync.py", "sync.sh"}:
            shutil.copy2(f, outdir / f.name)
            copied.append(f.name)

    # Copie des dossiers src/ et config/
    for dname in ["src", "config"]:
        d = root / dname
        if d.exists() and d.is_dir():
            print(f"→ Copie du dossier {dname}/")
            dst = outdir / dname
            dst.mkdir(exist_ok=True)
            copytree(d, dst)
            copied.append(f"{dname}/")

    # Journal local de la phase
    log = {
        "project": info["project_name"],
        "phase": info["phase"],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files_copied": copied
    }
    (outdir / "transfer_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"Codex mis à jour : {info['project_name']} – Phase {info['phase']} ({len(copied)} éléments).")

    # Journal global
    update_history(info, copied)

    # Archivage
    archive_old_phases(phase, project_name, keep_phases)

# --- Entrée principale ---
if __name__ == "__main__":
    keep_list = []
    if "--keep" in sys.argv:
        idx = sys.argv.index("--keep")
        if len(sys.argv) > idx + 1:
            keep_list = [p.strip() for p in sys.argv[idx + 1].split(",") if p.strip()]
            print(f"Option --keep détectée : conservation des phases {keep_list}")
    sync_codex(keep_list)


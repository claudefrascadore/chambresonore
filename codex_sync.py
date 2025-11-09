#!/usr/bin/env python3
# codex_sync.py — Version finale avec option --keep, journal global et résumé coloré
# ---------------------------------------------------------------------
# Fonction :
#  - Synchronise les fichiers du projet
#  - Copie src/ et config/ vers la phase courante
#  - Archive automatiquement les anciennes phases
#  - Permet de conserver certaines phases (--keep)
#  - Met à jour un journal global codex/transfer_history.json
#  - Affiche un résumé coloré en fin d’exécution
# ---------------------------------------------------------------------

import json, shutil, zipfile, sys
from datetime import datetime
from pathlib import Path

# Couleurs console
CYAN = "\033[0;36m"
YELLOW = "\033[1;33m"
GREEN = "\033[0;32m"
RESET = "\033[0m"

# Chemins de base
root = Path(__file__).resolve().parent
codex = root / "codex"
meta_file = codex / "project.json"
archive_dir = codex / "archive"
history_file = codex / "transfer_history.json"

# Extensions valides à copier
VALID_EXT = {".py", ".md", ".txt", ".json", ".ini", ".pas", ".pp", ".cfg"}

archived_list = []
kept_list = []

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
            print(f"{YELLOW}⏸ Phase {phase_num} conservée (option --keep){RESET}")
            kept_list.append(phase_num)
            continue
        zip_name = archive_dir / f"{phase_dir.name}.zip"
        print(f"{CYAN}→ Archivage de {phase_dir.name} → {zip_name.name}{RESET}")
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in phase_dir.rglob("*"):
                zipf.write(file, file.relative_to(codex))
        shutil.rmtree(phase_dir)
        print(f"{GREEN}   ✓ {phase_dir.name} archivée et supprimée.{RESET}")
        archived_list.append(phase_num)

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
def generate_html_index():
    """Génère un index HTML listant les phases et archives."""
    html_path = codex / "index.html"
    history = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
        except Exception:
            history = []

    # Génération du contenu HTML
    html = [
        "<!DOCTYPE html>",
        "<html lang='fr'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>Index du Codex – Chambre sonore</title>",
        "<style>",
        "body { font-family: sans-serif; background: #fdfdfd; color: #222; margin: 2em; }",
        "h1 { color: #444; }",
        "table { border-collapse: collapse; width: 100%; margin-top: 1em; }",
        "th, td { border: 1px solid #ccc; padding: 0.5em; text-align: left; }",
        "th { background: #eee; }",
        "a { color: #0066cc; text-decoration: none; }",
        "a:hover { text-decoration: underline; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Index du Codex – Chambre sonore</h1>",
        "<h2>Phases disponibles</h2>",
        "<table>",
        "<tr><th>Phase</th><th>Date</th><th>Fichiers copiés</th><th>Accès</th></tr>"
    ]

    for entry in reversed(history):
        phase = entry.get("phase")
        date = entry.get("date")
        files = len(entry.get("files", []))
        folder = f"Chambre_sonore_Phase_{phase}"
        archive = f"archive/{folder}.zip"
        link = ""
        if (codex / folder).exists():
            link = f"<a href='{folder}/'>Dossier</a>"
        elif (codex / archive).exists():
            link = f"<a href='{archive}'>Archive</a>"
        else:
            link = "(non disponible)"
        html.append(f"<tr><td>{phase}</td><td>{date}</td><td>{files}</td><td>{link}</td></tr>")

    html += [
        "</table>",
        "<p><a href='transfer_history.json'>Historique complet (JSON)</a></p>",
        "<p style='margin-top:2em;font-size:small;color:#666;'>Généré automatiquement le "
        + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "</p>",
        "</body></html>"
    ]

    html_path.write_text("\n".join(html), encoding="utf-8")
    print(f"{GREEN}✓ Index HTML mis à jour : {html_path}{RESET}")

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

    # Journal local
    log = {
        "project": info["project_name"],
        "phase": info["phase"],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files_copied": copied
    }
    (outdir / "transfer_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"{GREEN}Codex mis à jour : {info['project_name']} – Phase {info['phase']} ({len(copied)} éléments).{RESET}")

    # Journal global
    update_history(info, copied)

    # Archivage
    archive_old_phases(phase, project_name, keep_phases)

    # Résumé
    kept_display = sorted(set(kept_list) | set(keep_phases or []))
    print("\n--- Résumé ---")
    generate_html_index()

    print(f"{GREEN}Phase active : {phase}{RESET}")
    if kept_display:
        print(f"{YELLOW}Phases conservées : {', '.join(kept_display)}{RESET}")
    else:
        print(f"{YELLOW}Phases conservées : aucune{RESET}")
    if archived_list:
        print(f"{CYAN}Phases archivées : {', '.join(sorted(archived_list))}{RESET}")
    else:
        print(f"{CYAN}Phases archivées : aucune{RESET}")
    print(f"{GREEN}✓ Opération complétée avec succès.{RESET}\n")

# --- Entrée principale ---
if __name__ == "__main__":
    keep_list = []
    if "--keep" in sys.argv:
        idx = sys.argv.index("--keep")
        if len(sys.argv) > idx + 1:
            keep_list = [p.strip() for p in sys.argv[idx + 1].split(",") if p.strip()]
            print(f"{YELLOW}Option --keep détectée : conservation des phases {keep_list}{RESET}")
    sync_codex(keep_list)


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

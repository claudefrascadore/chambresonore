#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codex Register — Chambre sonore Phase 3
Enregistre un module, sa phase et sa description dans le registre Codex.
"""

import argparse
import json
from pathlib import Path
import sys

CODEX_DIR = Path(__file__).resolve().parent
REGISTRY = CODEX_DIR / "Chambre_sonore_Phase_3" / "transfer_log.json"

def main():
    p = argparse.ArgumentParser(description="Enregistre un module Codex")
    p.add_argument("--module", required=True)
    p.add_argument("--phase", required=True)
    p.add_argument("--desc", required=True)
    args = p.parse_args()

    entry = {
        "module": args.module,
        "phase": args.phase,
        "description": args.desc
    }

    REGISTRY.parent.mkdir(parents=True, exist_ok=True)

    data = []
    if REGISTRY.exists():
        try:
            data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        except Exception:
            data = []

    # éviter les doublons
    data = [e for e in data if e.get("module") != args.module]
    data.append(entry)

    REGISTRY.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Module enregistré : {args.module}")
    print(f"📁 Fichier de log : {REGISTRY}")

if __name__ == "__main__":
    sys.exit(main())


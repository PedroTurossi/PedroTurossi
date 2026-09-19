#!/usr/bin/env python3
"""
Step 1 of the workflow: collects GitHub telemetry for `username` in config.json
and saves it to data/telemetry.json.

    python scripts/telemetry.py

Uses GH_TOKEN (or GITHUB_TOKEN) when available. No third-party packages.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from terminal.config import load_config  # noqa: E402
from terminal.fmt import warn  # noqa: E402
from terminal.telemetry import collect  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "telemetry.json"


def main():
    cfg, _ = load_config(ROOT)
    prev = None
    if STATE.exists():
        try:
            prev = json.loads(STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            warn("data/telemetry.json is corrupted and will be recreated.")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    state = collect(cfg, prev, token, "views" in cfg["neofetch"]["fields"])

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    stats = state["stats"]
    print(f'[ok] data/telemetry.json for {cfg["username"]}')
    print(f'     repos {state["repos"]} | commits {stats["commits"]} | followers {stats["followers"]} | views {stats["views"]}')
    langs = ", ".join(f'{l["name"]} {l["percent"]:.1f}%' for l in state["languages"])
    print(f'     top {cfg["languages"]["count"]} of {state["languageCount"]}: {langs or "no languages"}')


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Step 2 of the workflow: draws assets/terminal.svg from config.json and
data/telemetry.json.

    python scripts/render.py          uses data/telemetry.json
    python scripts/render.py --demo   sample data, no network (to preview config changes)

No third-party packages.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from terminal.config import load_config  # noqa: E402
from terminal.fmt import fail  # noqa: E402
from terminal.render import render  # noqa: E402
from terminal.telemetry import demo_state  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "telemetry.json"
OUTPUT = ROOT / "assets" / "terminal.svg"


def main():
    cfg, S = load_config(ROOT)
    if "--demo" in sys.argv[1:]:
        state, mode = demo_state(cfg), "demo"
    else:
        if not STATE.exists():
            fail("data/telemetry.json not found. Run `python scripts/telemetry.py` first, or use --demo.")
        try:
            state, mode = json.loads(STATE.read_text(encoding="utf-8")), "telemetry"
        except json.JSONDecodeError:
            fail("data/telemetry.json is corrupted. Run `python scripts/telemetry.py` again.")

    svg = render(cfg, state, S, ROOT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"[ok] assets/terminal.svg ({len(svg) / 1024:.1f} KB, {mode})")


if __name__ == "__main__":
    main()

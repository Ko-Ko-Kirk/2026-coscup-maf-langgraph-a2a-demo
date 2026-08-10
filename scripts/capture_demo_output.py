#!/usr/bin/env python3
"""Run the real offline demo and save its stdout for the README screenshot."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "demo-output.txt"


def main() -> None:
    command = [
        sys.executable,
        str(ROOT / "01_coscup_inventory_demo.py"),
        "--product",
        "火雞肉飯",
        "--quantity",
        "20",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    OUTPUT.write_text(completed.stdout, encoding="utf-8")
    print(completed.stdout, end="")
    print(f"\ncaptured {OUTPUT}")


if __name__ == "__main__":
    main()

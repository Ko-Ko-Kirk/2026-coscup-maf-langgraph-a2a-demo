#!/usr/bin/env python3
"""Render the captured demo transcript as a GitHub-friendly terminal PNG."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT = ROOT / "assets" / "demo-output.txt"
OUTPUT = ROOT / "assets" / "demo-success.png"
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"


def clean_transcript(raw: str) -> list[str]:
    clean = raw.replace("\r", "").replace("^D\x08\x08", "").replace("\x04\x08\x08", "")
    clean = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", clean)
    clean = "\n".join(line.rstrip() for line in clean.splitlines()).strip()

    lines = [
        "$ uv run --locked python 01_coscup_inventory_demo.py --product 火雞肉飯 --quantity 20",
        "",
        *clean.splitlines(),
    ]
    wrapped: list[str] = []
    for line in lines:
        if len(line) <= 104:
            wrapped.append(line)
            continue
        indent = len(line) - len(line.lstrip())
        wrapped.extend(
            textwrap.wrap(
                line,
                width=104,
                subsequent_indent=" " * indent,
                replace_whitespace=False,
                drop_whitespace=False,
            )
        )
    return wrapped


def color_for(line: str) -> str:
    if line.startswith("$"):
        return "#F8FAFC"
    if line.startswith("["):
        return "#67E8F9"
    if line.startswith("DEMO PASSED"):
        return "#86EFAC"
    if '"status": "sufficient"' in line or "CONTINUE WITH CONTROLS" in line:
        return "#A7F3D0"
    if "A2A update:" in line or line.startswith("##"):
        return "#C4B5FD"
    if line.lstrip().startswith(('"', "```", "{", "}")):
        return "#CBD5E1"
    return "#E2E8F0"


def main() -> None:
    lines = clean_transcript(TRANSCRIPT.read_text(encoding="utf-8", errors="replace"))
    width = 1800
    line_height = 34
    top = 112
    bottom = 58
    height = top + bottom + line_height * len(lines)

    image = Image.new("RGB", (width, height), "#0B1120")
    draw = ImageDraw.Draw(image)
    body_font = ImageFont.truetype(FONT, 24)
    title_font = ImageFont.truetype(FONT, 22)
    meta_font = ImageFont.truetype(FONT, 18)

    draw.rounded_rectangle(
        (18, 18, width - 18, height - 18),
        radius=24,
        fill="#111827",
        outline="#334155",
        width=2,
    )
    for x, color in [(54, "#FB7185"), (84, "#FBBF24"), (114, "#4ADE80")]:
        draw.ellipse((x - 10, 43, x + 10, 63), fill=color)
    draw.text((150, 40), "COSCUP 2026 · real offline A2A run", font=title_font, fill="#F8FAFC")
    meta = "captured 2026-08-10 · fixture is labelled in output"
    meta_box = draw.textbbox((0, 0), meta, font=meta_font)
    draw.text((width - 54 - (meta_box[2] - meta_box[0]), 43), meta, font=meta_font, fill="#94A3B8")
    draw.line((36, 82, width - 36, 82), fill="#334155", width=2)

    y = top
    for line in lines:
        draw.text((56, y), line, font=body_font, fill=color_for(line))
        y += line_height

    image.save(OUTPUT, optimize=True)
    print(f"rendered {OUTPUT} ({width}x{height})")


if __name__ == "__main__":
    main()

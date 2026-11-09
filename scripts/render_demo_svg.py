#!/usr/bin/env python3
"""Render the real CLI output into an SVG card for the README.

No mock-up: the text comes from `decide(examples/demo_contract.json)` at build
time, so the image cannot show a result the tool no longer produces. The project
self-check re-renders it and fails on drift, which is the same discipline as the
README number lock — a screenshot that outlives its code is a lie.

Usage:
    python scripts/render_demo_svg.py
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_contract.engine import decide, load_contract  # noqa: E402
from release_contract.report import render_text  # noqa: E402

DEMO = ROOT / "examples" / "demo_contract.json"
OUT = ROOT / "assets" / "demo.svg"

FONT_SIZE = 13
LINE_HEIGHT = 19
PAD = 22
CHAR_WIDTH = 7.8

BG = "#0f172a"
CARD = "#111c33"
BORDER = "#24324d"
TEXT = "#dbe4f0"
DIM = "#8fa3c0"
ACCENT = {
    "AUTO": "#5eead4",
    "FENCE": "#fca5a5",
    "HOLD": "#fcd34d",
}


def build() -> str:
    body = render_text(decide(load_contract(DEMO))).splitlines()
    width = int(max(len(line) for line in body) * CHAR_WIDTH) + PAD * 2
    width = max(width, 560)
    height = len(body) * LINE_HEIGHT + PAD * 2 + 24

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" role="img" '
        'aria-label="release-contract deciding a demo contract">'
        % (width, height, width, height),
        "<style>"
        "text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
        "font-size:%dpx;white-space:pre}"
        "</style>" % FONT_SIZE,
        '<rect width="%d" height="%d" rx="12" fill="%s"/>' % (width, height, BG),
        '<rect x="1" y="1" width="%d" height="%d" rx="11" fill="%s" stroke="%s"/>'
        % (width - 2, height - 2, CARD, BORDER),
        '<circle cx="%d" cy="16" r="4" fill="#475569"/>' % (PAD + 4),
        '<circle cx="%d" cy="16" r="4" fill="#475569"/>' % (PAD + 18),
        '<circle cx="%d" cy="16" r="4" fill="#475569"/>' % (PAD + 32),
        '<text x="%d" y="21" fill="%s">release-contract decide</text>'
        % (PAD + 52, DIM),
    ]
    y = PAD + 30
    for line in body:
        colour = TEXT
        for token, c in ACCENT.items():
            if token in line:
                colour = c
                break
        if line and not line.startswith(" "):
            colour = DIM
        parts.append(
            '<text x="%d" y="%d" fill="%s">%s</text>'
            % (PAD, y, colour, html.escape(line) if line else " ")
        )
        y += LINE_HEIGHT
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    svg = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8", newline="\n")
    print("wrote %s (%d bytes)" % (OUT.relative_to(ROOT), len(svg.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

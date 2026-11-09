#!/usr/bin/env python3
"""Render the real CLI output into an animated GIF for the README.

Honesty note: this is a rendering of the actual stdout, not a screen capture.
The frames are produced from `decide(examples/demo_contract.json)` at build
time, and a sidecar records the SHA-256 of that text so a stale image can be
detected without re-running Pillow. If the engine output changes, the project
self-check fails until this script is re-run.

Usage:
    python scripts/render_demo_gif.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_contract.engine import decide, load_contract  # noqa: E402
from release_contract.report import render_text  # noqa: E402

DEMO = ROOT / "examples" / "demo_contract.json"
OUT = ROOT / "assets" / "demo.gif"
SIDECAR = ROOT / "assets" / "demo.gif.json"

FONT_CANDIDATES = (
    "C:/Windows/Fonts/consola.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
)
FONT_SIZE = 15
LINE_HEIGHT = 21
PAD = 20
BG = (15, 23, 42)
CARD = (17, 28, 51)
CHROME = (71, 85, 105)
TEXT = (219, 228, 240)
DIM = (143, 163, 192)
ACCENT = {"AUTO": (94, 234, 212), "FENCE": (252, 165, 165), "HOLD": (252, 211, 77)}
HOLD_MS = 2600


def _font():
    from PIL import ImageFont

    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, FONT_SIZE)
    raise SystemExit("no monospace font found; install DejaVu Sans Mono")


def _source() -> str:
    return render_text(decide(load_contract(DEMO)))


def build() -> tuple[bytes, dict]:
    from PIL import Image, ImageDraw

    text = _source()
    lines = text.splitlines()
    font = _font()
    char_w = font.getbbox("M")[2]
    width = max(len(line) for line in lines) * char_w + PAD * 2
    height = (len(lines) + 1) * LINE_HEIGHT + PAD * 2

    def frame(visible: int):
        img = Image.new("RGB", (width, height), BG)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([1, 1, width - 2, height - 2], 12, fill=CARD)
        for i, cx in enumerate((PAD + 6, PAD + 20, PAD + 34)):
            d.ellipse([cx - 4, 12, cx + 4, 20], fill=CHROME)
        d.text((PAD + 52, 8), "release-contract decide", font=font, fill=DIM)
        y = PAD + 22
        for line in lines[:visible]:
            colour = TEXT
            for token, c in ACCENT.items():
                if token in line:
                    colour = c
                    break
            if line and not line.startswith(" "):
                colour = DIM
            d.text((PAD, y), line, font=font, fill=colour)
            y += LINE_HEIGHT
        return img

    frames = [frame(n) for n in range(1, len(lines) + 1)]
    durations = [70] * len(frames)
    durations[-1] = HOLD_MS

    import io

    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    meta = {
        "source": DEMO.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "rendered_with": "scripts/render_demo_gif.py",
        "note": "Rendered from real CLI stdout; not a screen capture.",
        "frames": len(frames),
        "bytes": len(buf.getvalue()),
    }
    return buf.getvalue(), meta


def main() -> int:
    data, meta = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    SIDECAR.write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "wrote %s (%d frames, %.1f KB)"
        % (OUT.relative_to(ROOT), meta["frames"], meta["bytes"] / 1024)
    )
    print("source sha256: %s" % meta["source_sha256"][:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Run the four-step flow with pauses, so a screen recording needs no editing.

Everything it prints is real CLI output; nothing is scripted prose. Files it
writes go to `.local/demo/` (gitignored), never to the repository root.

Usage:
    python scripts/demo.py            # 1.2s between steps
    python scripts/demo.py --pace 0   # no pauses (used by the tests)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".local" / "demo"

STEPS = (
    ("python -m release_contract.cli --version", None),
    (
        "python -m release_contract.cli import examples/counts.example.csv "
        "--product \"SYNTHETIC demo: checkout-assistant v7\" -o .local/demo/contract.json",
        None,
    ),
    ("python -m release_contract.cli validate .local/demo/contract.json", None),
    ("python -m release_contract.cli decide .local/demo/contract.json", None),
    (
        "python -m release_contract.cli decide .local/demo/contract.json --fail-on FENCE",
        "exit code 2 = a gate the caller opted into was hit",
    ),
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pace", type=float, default=1.2, help="seconds between steps")
    ap.add_argument("--quiet", action="store_true", help="hide the command echo")
    args = ap.parse_args()

    # Start clean: a leftover contract would make `import` print
    # "refusing to overwrite", which is correct behaviour but ruins a recording.
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)
    # Unbuffered, so a recording shows the command before its output instead of
    # stderr jumping the queue.
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    for command, note in STEPS:
        if not args.quiet:
            print("\n$ " + command)
            sys.stdout.flush()
        proc = subprocess.run(
            command,
            cwd=str(ROOT),
            shell=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        sys.stdout.write(proc.stdout or "")
        if proc.stderr.strip():
            sys.stdout.write(proc.stderr)
        if note:
            print("# %s" % note)
        sys.stdout.flush()
        if args.pace > 0:
            time.sleep(args.pace)
    return 0


if __name__ == "__main__":
    sys.exit(main())

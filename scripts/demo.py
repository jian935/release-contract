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

# Steps are written with `{py}` and expanded to `sys.executable`. Never put a
# bare `python` here: on Windows a launcher stub can shadow it, exit 0 and
# print nothing, which makes a recording look like the tool did nothing.
STEPS = (
    (
        "{py} -m release_contract.cli import examples/counts.example.csv "
        "--product \"SYNTHETIC demo: checkout-assistant v7\" -o .local/demo/contract.json",
        None,
        True,
    ),
    ("{py} -m release_contract.cli validate .local/demo/contract.json", None, True),
    ("{py} -m release_contract.cli decide .local/demo/contract.json", None, True),
    # The report is identical to the previous step, so printing it twice would
    # scroll the verdict table out of view. Report the real exit code instead.
    (
        "{py} -m release_contract.cli decide .local/demo/contract.json --fail-on FENCE",
        "a gate the caller opted into was hit",
        False,
    ),
)


def expand(template: str) -> str:
    """Fill `{py}` with the running interpreter, quoted for a shell."""
    return template.replace("{py}", '"%s"' % sys.executable)


def for_display(command: str) -> str:
    """Shorten only the interpreter path, so a long line still fits a screen.

    The executed command keeps the absolute path; this is a display alias, not
    a different invocation.
    """
    return command.replace('"%s"' % sys.executable, "python")


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
    for template, note, show_output in STEPS:
        command = expand(template)
        if not args.quiet:
            print("\n$ " + for_display(command))
            sys.stdout.flush()
        proc = subprocess.run(
            command,
            cwd=str(ROOT),
            shell=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if show_output:
            sys.stdout.write(output)
            # A step that "succeeds" while printing nothing means the interpreter
            # never ran. Say so loudly instead of recording a blank screen.
            if not output.strip() and proc.returncode == 0:
                sys.stdout.write(
                    "# WARNING: this step printed nothing. The interpreter probably "
                    "did not run (a launcher stub can exit 0 silently).\n"
                )
        else:
            print("# exit code %d: %s" % (proc.returncode, note or "done"))
        if note and show_output:
            print("# %s" % note)
        sys.stdout.flush()
        if args.pace > 0:
            time.sleep(args.pace)
    return 0


if __name__ == "__main__":
    sys.exit(main())

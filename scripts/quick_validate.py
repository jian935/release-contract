#!/usr/bin/env python3
"""Run everything a release needs: unit tests, eval suites, project locks.

Usage: python scripts/quick_validate.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_contract.evalset import render as render_eval, run_suite  # noqa: E402
from release_contract.selfcheck import render as render_checks, run_checks  # noqa: E402


def main() -> int:
    print("== unit tests ==")
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=str(ROOT),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    # unittest writes its -v report to stderr, so print both streams.
    print((proc.stdout or "")[-6000:])
    print((proc.stderr or "")[-6000:])
    if proc.returncode != 0:
        print("UNIT TESTS FAILED")
        return 1

    print("")
    print("== eval suites ==")
    for which in ("dev", "holdout"):
        print(render_eval(run_suite(which)))
        print("")

    print("== project self-checks ==")
    checks = run_checks()
    print(render_checks(checks))
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())

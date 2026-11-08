#!/usr/bin/env python3
"""Standalone entry point: python eval/run_eval.py

The scoring logic itself lives in release_contract.evalset so the CLI and this
script cannot drift apart.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from release_contract.evalset import render, run_suite  # noqa: E402


def main() -> int:
    for which in ("dev", "holdout"):
        print(render(run_suite(which)))
        print("")
    print("Synthetic sets written by the rule author; see eval/README.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

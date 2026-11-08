#!/usr/bin/env python3
"""Run golden-label-free property checks over a fixed-seed parameter scan.

Usage: python scripts/property_scan.py [--trials N] [--seed N]
Exit code 1 on any invariant violation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_contract.properties import (  # noqa: E402
    DEFAULT_SEED,
    DEFAULT_TRIALS,
    render,
    scan,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args()
    result = scan(seed=args.seed, trials=args.trials)
    print(render(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

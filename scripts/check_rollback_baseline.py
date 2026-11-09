#!/usr/bin/env python3
"""Did any AUTO segment breach the baseline the contract recorded for it?

`decide` writes a rollback trigger per AUTO segment before launch. This reads the
launch's own logs and checks that promise against them, window by window.

Usage:
    python scripts/check_rollback_baseline.py examples/demo_contract.json \\
        examples/launch/run_log.jsonl --window-size 100

Exit codes: 0 no trigger (or no --fail-on-trigger), 2 a trigger fired under
--fail-on-trigger, 3 the input could not be read.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_contract.engine import ContractError, decide, load_contract  # noqa: E402
from release_contract.launch import LaunchError, evaluate, render  # noqa: E402

EXIT_OK = 0
EXIT_GATE = 2
EXIT_INPUT = 3


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("contract", help="contract JSON (the one that was shipped)")
    ap.add_argument("log", help="JSONL of {segment, ok} from the running product")
    ap.add_argument(
        "--window-size",
        type=int,
        default=200,
        dest="window_size",
        help="observations per window (default 200); a partial window never triggers",
    )
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--fail-on-trigger",
        action="store_true",
        dest="fail_on_trigger",
        help="exit 2 if any AUTO segment breached its baseline",
    )
    args = ap.parse_args()

    try:
        contract = load_contract(args.contract)
        decision = decide(contract)
        text = Path(args.log).read_text(encoding="utf-8-sig")
        result = evaluate(decision, text, args.window_size)
    except (ContractError, LaunchError, OSError) as exc:
        print("invalid input: %s" % exc, file=sys.stderr)
        return EXIT_INPUT

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render(result))

    if args.fail_on_trigger and result["triggered"]:
        return EXIT_GATE
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

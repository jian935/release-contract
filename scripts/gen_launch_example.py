#!/usr/bin/env python3
"""Regenerate the synthetic launch log used by the baseline-check example.

The numbers are chosen, not sampled: `routine_faq` clears the recorded baseline
for two windows and then misses it for two consecutive windows, which is the
smallest interesting case. A self-check compares the shipped file against this
generator so the example cannot drift away from what it claims to show.

Usage:
    python scripts/gen_launch_example.py            # rewrite the file
    python scripts/gen_launch_example.py --print    # show it instead
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "launch" / "run_log.jsonl"

# routine_faq is the only AUTO segment in examples/demo_contract.json.
# Four windows of 100 labelled cases; the last two are below its 0.9483 baseline.
ROUTINE_WINDOWS = (98, 97, 90, 92)

# A segment the contract did not clear: logged anyway, to show that non-AUTO
# segments are reported without any baseline claim.
BILLING_WINDOWS = (72, 70)

# Cases with no boolean outcome must be skipped, never counted as failures.
UNLABELLED_BILLING = 3


def _rows(segment: str, windows: tuple[int, ...], size: int = 100) -> list[dict]:
    out: list[dict] = []
    for successes in windows:
        out.extend({"segment": segment, "ok": True} for _ in range(successes))
        out.extend({"segment": segment, "ok": False} for _ in range(size - successes))
    return out


def build() -> str:
    rows = _rows("routine_faq", ROUTINE_WINDOWS)
    rows += _rows("billing_dispute", BILLING_WINDOWS)
    for _ in range(UNLABELLED_BILLING):
        rows.append({"segment": "billing_dispute"})
    # contract_redline exists in the contract but never appears in the log:
    # "no observations" must be visible, not silently treated as healthy.
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--print", action="store_true", dest="to_stdout")
    args = ap.parse_args()
    text = build()
    if args.to_stdout:
        sys.stdout.write(text)
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d lines)" % (OUT.relative_to(ROOT), len(text.splitlines())))
    return 0


if __name__ == "__main__":
    sys.exit(main())

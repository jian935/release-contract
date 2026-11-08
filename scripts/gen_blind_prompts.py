#!/usr/bin/env python3
"""Generate answer-free blind-evaluation prompts from the eval suites.

Single source of truth: eval/dev.jsonl + eval/holdout.jsonl. Never hand-edit
prompts.jsonl -- run this script instead, so the blind set cannot drift from
the scored set.

Deliberately omitted from every prompt: expected, why, kind. The `kind` field
would leak which gate is being exercised, and expected/why would leak the
answer. An annotator must see only the contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_contract.evalset import load_cases  # noqa: E402

OUT = ROOT / "eval" / "blind" / "prompts.jsonl"
LEAK_KEYS = ("expected", "why", "kind")


def build_rows() -> list[dict]:
    rows: list[dict] = []
    for which in ("dev", "holdout"):
        for case in load_cases(which):
            contract = {
                "product": "blind-evaluation-case",
                "guardrails": case["guardrails"],
                "segments": case["segments"],
            }
            row = {"id": case["id"], "suite": which, "contract": contract}
            for key in LEAK_KEYS:
                if key in row or key in contract:
                    raise RuntimeError("answer leaked into blind prompt: %s" % key)
            rows.append(row)
    return rows


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    text = "\n".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
    ) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print("wrote %d answer-free prompts to %s" % (len(rows), OUT.relative_to(ROOT)))
    print("omitted fields: %s" % ", ".join(LEAK_KEYS))
    return 0


if __name__ == "__main__":
    sys.exit(main())

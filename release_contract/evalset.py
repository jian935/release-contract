"""Evaluation harness for the built-in synthetic eval sets.

Scoring unit is the *per-segment verdict*, not the case. The denominator is
therefore the total number of declared segments across all cases, and it is
always printed alongside the score.

Evidence-risk flags are intentionally NOT scored. They are advisory; claiming
an accuracy for them would be an unmeasured number.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, FrozenSet

from .engine import contract_from_dict, decide, wilson_interval

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"
SUITES: dict[str, Path] = {
    "dev": EVAL_DIR / "dev.jsonl",
    "holdout": EVAL_DIR / "holdout.jsonl",
}


def load_cases(which: str) -> list[dict[str, Any]]:
    path = SUITES[which]
    cases: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        for key in ("id", "kind", "segments", "guardrails", "expected", "why"):
            if key not in case:
                raise ValueError("%s:%d missing %s" % (path.name, lineno, key))
        cases.append(case)
    if not cases:
        raise ValueError("%s is empty" % path.name)
    return cases


def case_contract(case: dict[str, Any]):
    """Build the Contract used by both scoring and ablation tests."""
    return contract_from_dict(
        {
            "product": case["id"],
            "segments": case["segments"],
            "guardrails": case["guardrails"],
        }
    )


def run_suite(
    which: str, disabled: FrozenSet[str] = frozenset()
) -> dict[str, Any]:
    """Score a suite. ``disabled`` exists only to support ablation tests."""
    cases = load_cases(which)
    total = 0
    correct = 0
    per_kind: dict[str, dict[str, int]] = {}
    mismatches: list[dict[str, str]] = []

    for case in cases:
        decision = decide(case_contract(case), disabled)
        got = {s.id: s.verdict for s in decision.segments}
        kind = case["kind"]
        bucket = per_kind.setdefault(kind, {"correct": 0, "total": 0})
        for seg_id, expected in case["expected"].items():
            total += 1
            bucket["total"] += 1
            actual = got.get(seg_id)
            if actual == expected:
                correct += 1
                bucket["correct"] += 1
            else:
                mismatches.append(
                    {
                        "case": case["id"],
                        "segment": seg_id,
                        "expected": expected,
                        "got": str(actual),
                    }
                )

    ci = None
    if total >= 8:
        lo, hi = wilson_interval(correct, total)
        ci = [round(lo, 4), round(hi, 4)]

    return {
        "suite": which,
        "cases": len(cases),
        "scored_segments": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "wilson95_ci": ci,
        "per_kind": per_kind,
        "mismatches": mismatches,
        "scored_unit": "per-segment verdict",
        "unscored": ["evidence_risk flags", "real-world launch outcomes"],
    }


def render(result: dict[str, Any]) -> str:
    lines = [
        "%s: %d cases / %d scored segments"
        % (result["suite"], result["cases"], result["scored_segments"]),
        "  correct     : %d" % result["correct"],
        "  accuracy    : %.4f" % result["accuracy"],
        "  wilson95 CI : %s"
        % (result["wilson95_ci"] if result["wilson95_ci"] else "n<8, no interval"),
        "  scored unit : %s" % result["scored_unit"],
        "  by structural kind:",
    ]
    for kind, b in sorted(result["per_kind"].items()):
        lines.append("    %-20s %d/%d" % (kind, b["correct"], b["total"]))
    if result["mismatches"]:
        lines.append("  mismatches:")
        for m in result["mismatches"]:
            lines.append(
                "    %s/%s expected=%s got=%s"
                % (m["case"], m["segment"], m["expected"], m["got"])
            )
    lines.append(
        "  unscored (no number claimed): %s" % ", ".join(result["unscored"])
    )
    return "\n".join(lines)

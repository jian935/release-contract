#!/usr/bin/env python3
"""What would the two open rule questions cost, in verdicts?

`DESIGN.md` records two disagreements from blind round 2 that were deliberately
not patched into the engine. Deciding them needs a number, not an opinion, so
this script re-scores the shipped blind cases under each candidate rule and
reports exactly which segments would change verdict.

    python scripts/whatif_rules.py

Scenario A — a configured fallback lowers effective harm by one rank.
Scenario B — a hard gate violation outranks G1, so a violated ceiling reads
             FENCE instead of HOLD when evidence is also thin.

Both are hypotheticals. Nothing here changes the engine, and nothing printed by
this script is a claim about the tool as shipped.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_contract.engine import (  # noqa: E402
    AUTO,
    FENCE,
    HARM_RANK,
    HOLD,
    contract_from_dict,
    decide,
    wilson_lower,
)

PROMPTS = ROOT / "eval" / "blind" / "prompts.jsonl"


def _cases() -> list[dict]:
    return [json.loads(line) for line in PROMPTS.read_text(encoding="utf-8").splitlines() if line.strip()]


def scenario_a(case: dict, verdict: str, seg, guardrails) -> str | None:
    """Fallback relaxes the ceiling by one severity rank."""
    effective = HARM_RANK[seg.harm_if_wrong]
    if seg.fallback != "none" and effective > 0:
        effective -= 1
    contained = not (seg.harm_if_wrong in ("high", "critical") and seg.fallback == "none")
    passes = (
        effective <= HARM_RANK[guardrails.max_harm]
        and seg.n >= guardrails.min_sample_size
        and wilson_lower(seg.successes, seg.n, guardrails.z) >= guardrails.min_success_rate
        and seg.loaded_cost <= guardrails.max_cost_per_case
        and contained
    )
    proposed = AUTO if passes else FENCE
    if verdict == HOLD or proposed == verdict:
        return None
    return proposed


def scenario_b(verdict: str, seg, guardrails) -> str | None:
    """A hard violation outranks the sample-size gate."""
    hard = (
        HARM_RANK[seg.harm_if_wrong] > HARM_RANK[guardrails.max_harm]
        or (seg.harm_if_wrong in ("high", "critical") and seg.fallback == "none")
        or seg.loaded_cost > guardrails.max_cost_per_case
    )
    if verdict == HOLD and hard:
        return FENCE
    return None


def run() -> dict:
    rows: list[dict] = []
    for case in _cases():
        contract = contract_from_dict(case["contract"])
        decision = decide(contract)
        for seg, sd in zip(contract.segments, decision.segments):
            a = scenario_a(case, sd.verdict, seg, contract.guardrails)
            b = scenario_b(sd.verdict, seg, contract.guardrails)
            if a or b:
                rows.append(
                    {
                        "case": case["id"],
                        "segment": seg.id,
                        "current": sd.verdict,
                        "scenario_a": a,
                        "scenario_b": b,
                    }
                )
    total = sum(len(json.loads(line)["contract"]["segments"]) for line in PROMPTS.read_text(encoding="utf-8").splitlines() if line.strip())
    return {
        "segments": total,
        "flip_a": [r for r in rows if r["scenario_a"]],
        "flip_b": [r for r in rows if r["scenario_b"]],
    }


def render(result: dict) -> str:
    lines = [
        "what-if rules over the %d published blind segments" % result["segments"],
        "",
        "A) a configured fallback lowers effective harm by one rank",
    ]
    if result["flip_a"]:
        for row in result["flip_a"]:
            lines.append(
                "   %-8s %-18s %s -> %s" % (row["case"], row["segment"], row["current"], row["scenario_a"])
            )
    else:
        lines.append("   no verdict would change")
    lines.append(
        "   total: %d of %d segments" % (len(result["flip_a"]), result["segments"])
    )
    lines.append("")
    lines.append("B) a hard gate violation outranks G1 (HOLD -> FENCE)")
    if result["flip_b"]:
        for row in result["flip_b"]:
            lines.append(
                "   %-8s %-18s %s -> %s" % (row["case"], row["segment"], row["current"], row["scenario_b"])
            )
    else:
        lines.append("   no verdict would change")
    lines.append(
        "   total: %d of %d segments" % (len(result["flip_b"]), result["segments"])
    )
    lines.append("")
    lines.append("Neither scenario is implemented. Both are inputs to DESIGN.md.")
    return "\n".join(lines)


def main() -> int:
    print(render(run()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

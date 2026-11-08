"""Property checks that do NOT depend on any hand-written golden label.

A golden label can only tell us whether the engine agrees with its author.
These checks instead scan a parameter space and assert invariants that must
hold for every contract. A violation is a real bug, not a disagreeing opinion.

Fixed seed -> reproducible. No third-party dependencies.
"""

from __future__ import annotations

import random
from typing import Any

from .engine import (
    AUTO,
    SEGMENT_GATES,
    Contract,
    ContractError,
    Guardrails,
    Segment,
    contract_from_dict,
    decide,
    wilson_lower,
)
from .report import to_json

DEFAULT_SEED = 20261108
DEFAULT_TRIALS = 400


def _random_contract(rng: random.Random) -> Contract:
    count = rng.randint(1, 4)
    shares = [rng.random() for _ in range(count)]
    total = sum(shares)
    # Deliberately under-cover some contracts: the accounting must still work.
    # Keep a hair below full coverage: rounding each share could otherwise
    # push the declared sum over 1.0 and trip the loader before any property
    # is checked. That would be a scanner bug, not a product finding.
    scale = (rng.choice((0.7, 0.9, 1.0)) - 1e-4) / total if total else 0.0
    segs = []
    for i in range(count):
        n = rng.choice((5, 30, 60, 99, 100, 150, 250, 400, 1000))
        successes = rng.randint(0, n)
        segs.append(
            Segment(
                id="seg_%d" % i,
                volume_share=round(shares[i] * scale, 6) if total else 0.0,
                n=n,
                successes=successes,
                harm_if_wrong=rng.choice(("low", "medium", "high", "critical")),
                fallback=rng.choice(("none", "human", "degrade", "rollback")),
                cost_per_case=round(rng.uniform(0.0, 1.0), 4),
                human_review_cost=round(rng.uniform(0.0, 1.0), 4),
            )
        )
    return Contract(
        product="property-scan",
        segments=tuple(segs),
        guardrails=Guardrails(
            min_sample_size=rng.choice((30, 50, 100)),
            min_success_rate=rng.choice((0.85, 0.9, 0.95)),
            max_harm=rng.choice(("low", "medium", "high", "critical")),
            max_cost_per_case=rng.choice((0.3, 0.5, 1.0)),
        ),
    )


def scan(seed: int = DEFAULT_SEED, trials: int = DEFAULT_TRIALS) -> dict[str, Any]:
    rng = random.Random(seed)
    violations: list[str] = []
    checked = {name: 0 for name in (
        "P1_traffic_accounting",
        "P2_deterministic_replay",
        "P3_wilson_monotonic",
        "P4_ablation_monotonic",
        "P5_invalid_input_rejected",
    )}

    for i in range(trials):
        c = _random_contract(rng)
        d = decide(c)

        # P1: four buckets always account for the full traffic.
        buckets = ("auto", "fence", "hold", "uncovered")
        if abs(sum(d.traffic[k] for k in buckets) - 1.0) > 1e-6:
            violations.append("trial %d: traffic buckets do not sum to 1.0" % i)
        checked["P1_traffic_accounting"] += 1

        # P2: rebuilding the same contract from a dict replays byte-identically.
        raw = {
            "product": c.product,
            "guardrails": dict(c.guardrails.__dict__),
            "segments": [dict(s.__dict__) for s in c.segments],
        }
        a = to_json(decide(contract_from_dict(raw)))
        b = to_json(decide(contract_from_dict(raw)))
        if a != b:
            violations.append("trial %d: replay is not byte-identical" % i)
        checked["P2_deterministic_replay"] += 1

        # P3: at a fixed rate, a larger sample cannot lower the Wilson bound.
        p = 0.95
        prev = -1.0
        for n in (30, 60, 100, 250, 500, 1000):
            k = int(round(p * n))
            low = wilson_lower(k, n)
            if low + 1e-12 < prev:
                violations.append("trial %d: Wilson bound decreased at n=%d" % (i, n))
            prev = low
        checked["P3_wilson_monotonic"] += 1

        # P4: disabling a gate can only make the decision more permissive.
        base_auto = sum(1 for s in d.segments if s.verdict == AUTO)
        for gate in SEGMENT_GATES:
            ablated = decide(c, frozenset({gate}))
            abl_auto = sum(1 for s in ablated.segments if s.verdict == AUTO)
            if abl_auto < base_auto:
                violations.append(
                    "trial %d: disabling %s reduced AUTO segments" % (i, gate)
                )
        checked["P4_ablation_monotonic"] += 1

        # P5: structurally invalid inputs must be rejected, never coerced.
        bad = {
            "product": "invalid",
            "guardrails": {},
            "segments": [{"id": "x", "volume_share": 0.5, "n": 10,
                          "successes": 11, "harm_if_wrong": "low",
                          "fallback": "none", "cost_per_case": 0.1}],
        }
        try:
            contract_from_dict(bad)
            violations.append("trial %d: successes > n was accepted" % i)
        except ContractError:
            pass
        checked["P5_invalid_input_rejected"] += 1

    return {
        "seed": seed,
        "trials": trials,
        "checked": checked,
        "violations": violations,
        "passed": not violations,
    }


def render(result: dict[str, Any]) -> str:
    lines = [
        "property scan (no golden labels involved)",
        "  seed    : %d" % result["seed"],
        "  trials  : %d" % result["trials"],
    ]
    for name, n in result["checked"].items():
        lines.append("  %-30s %d contracts" % (name, n))
    lines.append("  violations: %s" % (result["violations"] if result["violations"] else "none"))
    lines.append("  verdict   : %s" % ("PASS" if result["passed"] else "FAIL"))
    return "\n".join(lines)

"""Rendering helpers. Kept separate from the engine so the decision stays pure."""

from __future__ import annotations

import json
from typing import Any

from .engine import Decision, GateHit


def _gate_dict(hit: GateHit) -> dict[str, str]:
    return {"gate": hit.gate, "verdict": hit.verdict, "detail": hit.detail}


def to_dict(decision: Decision) -> dict[str, Any]:
    """JSON-serialisable, stable key order -- suitable for golden diffs in CI."""
    return {
        "product": decision.product,
        "guardrails": dict(decision.guardrails),
        "segments": [
            {
                "id": s.id,
                "verdict": s.verdict,
                "primary_gate": s.primary_gate,
                "volume_share": round(s.volume_share, 6),
                "observed_rate": round(s.observed_rate, 6),
                "wilson_lower": round(s.wilson_lower, 6),
                "loaded_cost": round(s.loaded_cost, 6),
                "gates": [_gate_dict(g) for g in s.gates],
            }
            for s in decision.segments
        ],
        "traffic": decision.traffic,
        "coverage_gate": _gate_dict(decision.coverage_gate)
        if decision.coverage_gate
        else None,
        "evidence_risks": list(decision.risks),
        "rollback_triggers": list(decision.rollbacks),
    }


def to_json(decision: Decision) -> str:
    return json.dumps(to_dict(decision), ensure_ascii=False, indent=2, sort_keys=True)


def render_text(decision: Decision) -> str:
    lines: list[str] = []
    lines.append("release-contract: %s" % decision.product)
    lines.append("=" * 60)
    lines.append("")
    lines.append("SEGMENTS")
    for s in decision.segments:
        lines.append(
            "  %-22s %-5s  share=%5.1f%%  observed=%.3f  wilson_lower=%.3f  cost=%.3f"
            % (
                s.id,
                s.verdict,
                s.volume_share * 100,
                s.observed_rate,
                s.wilson_lower,
                s.loaded_cost,
            )
        )
        for g in s.gates:
            lines.append("      [%s %s] %s" % (g.gate, g.verdict, g.detail))
        if not s.gates:
            lines.append("      [NONE] all per-segment gates passed")
    lines.append("")
    lines.append("TRAFFIC (denominator = full traffic 1.0, not a chosen subset)")
    t = decision.traffic
    for key in ("auto", "fence", "hold", "uncovered"):
        lines.append("  %-10s %6.1f%%" % (key, t[key] * 100))
    lines.append("  %-10s %6.1f%%" % ("total", sum(t[k] for k in ("auto", "fence", "hold", "uncovered")) * 100))
    lines.append("")
    if decision.coverage_gate:
        lines.append("GLOBAL GATE: %s -- %s" % (decision.coverage_gate.gate, decision.coverage_gate.detail))
        lines.append("")
    lines.append("EVIDENCE RISKS (advisory; never change a verdict)")
    if decision.risks:
        for r in decision.risks:
            lines.append("  - %s" % r)
    else:
        lines.append("  (none flagged)")
    lines.append("")
    lines.append("ROLLBACK TRIGGERS")
    if decision.rollbacks:
        for rb in decision.rollbacks:
            lines.append("  %s: %s" % (rb["segment"], rb["trigger"]))
            lines.append("      -> %s" % rb["action"])
    else:
        lines.append("  (no AUTO segment; nothing to roll back)")
    lines.append("")
    lines.append("Deterministic replay: same contract JSON in, byte-identical decision out.")
    return "\n".join(lines)

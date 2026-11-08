"""Compare two release decisions: which segments got better or worse.

A model swap, a prompt rewrite or a new eval run should be answerable with
"these segments regressed, these improved", not with one averaged score.
"""

from __future__ import annotations

from typing import Any

from .engine import AUTO, FENCE, HOLD, Contract, Decision, decide

RANK: dict[str, int] = {AUTO: 0, FENCE: 1, HOLD: 2}
TRAFFIC_KEYS = ("auto", "fence", "hold", "uncovered")


def _compare(before: str | None, after: str | None) -> str:
    if before is None:
        return "added"
    if after is None:
        return "removed"
    if before == after:
        return "unchanged"
    return "regression" if RANK[after] > RANK[before] else "improvement"


def diff_decisions(old: Decision, new: Decision) -> dict[str, Any]:
    a = {s.id: s.verdict for s in old.segments}
    b = {s.id: s.verdict for s in new.segments}
    rows = []
    for seg_id in sorted(set(a) | set(b)):
        before, after = a.get(seg_id), b.get(seg_id)
        rows.append(
            {
                "id": seg_id,
                "before": before,
                "after": after,
                "change": _compare(before, after),
            }
        )
    summary = {
        kind: sum(1 for r in rows if r["change"] == kind)
        for kind in ("regression", "improvement", "unchanged", "added", "removed")
    }
    return {
        "product": new.product,
        "segments": rows,
        "summary": summary,
        "traffic_delta": {
            k: round(new.traffic[k] - old.traffic[k], 6) for k in TRAFFIC_KEYS
        },
        "traffic_before": {k: old.traffic[k] for k in TRAFFIC_KEYS},
        "traffic_after": {k: new.traffic[k] for k in TRAFFIC_KEYS},
    }


def diff_contracts(old: Contract, new: Contract) -> dict[str, Any]:
    return diff_decisions(decide(old), decide(new))


def render(result: dict[str, Any]) -> str:
    lines = ["release-contract diff: %s" % result["product"], ""]
    for r in result["segments"]:
        lines.append(
            "  %-24s %-6s -> %-6s  %s"
            % (r["id"], r["before"] or "-", r["after"] or "-", r["change"])
        )
    lines.append("")
    s = result["summary"]
    lines.append(
        "  regressions=%d improvements=%d unchanged=%d added=%d removed=%d"
        % (s["regression"], s["improvement"], s["unchanged"], s["added"], s["removed"])
    )
    lines.append("  traffic before: %s" % result["traffic_before"])
    lines.append("  traffic after : %s" % result["traffic_after"])
    lines.append("  delta         : %s" % result["traffic_delta"])
    return "\n".join(lines)

"""Compare a launch's first observation windows against the recorded baselines.

`decide` promises a rollback trigger for every `AUTO` segment: "observed success
rate below <wilson lower bound> for 2 consecutive windows". This module is the
other half of that promise — it takes the logs from the running product and says
whether any trigger actually fired.

Three rules keep it honest:

1. Windows are fixed *counts* of observations, not time slices. A success rate
   needs a denominator, and a clock does not provide one.
2. A window with fewer than `window_size` observations is reported but can never
   fire a trigger. Half a window is not evidence.
3. A segment with no observations is reported as such. Silence is never treated
   as success, which is the failure mode that makes a launch look healthy.

Nothing here decides what to ship. It reports drift against a baseline that was
fixed before the launch, so the comparison cannot be retro-fitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .engine import AUTO, ROLLBACK_CONSECUTIVE_WINDOWS, Decision


class LaunchError(ValueError):
    """The log cannot be read without inventing an outcome."""


@dataclass(frozen=True)
class Window:
    index: int
    n: int
    successes: int
    complete: bool

    @property
    def rate(self) -> float:
        return self.successes / self.n if self.n else 0.0


def read_records(text: str) -> tuple[dict[str, list[bool]], int]:
    """Parse `{"segment": ..., "ok": ...}` lines in order.

    Returns per-segment outcomes in log order and the number of cases that had
    no boolean outcome (excluded from every window, never counted as failure).
    """
    import json

    per_segment: dict[str, list[bool]] = {}
    unlabelled = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LaunchError("line %d is not JSON: %s" % (line_no, exc)) from None
        if not isinstance(record, dict):
            raise LaunchError("line %d is not an object" % line_no)
        segment = str(record.get("segment", "")).strip()
        if not segment:
            raise LaunchError("line %d has no segment" % line_no)
        ok = record.get("ok")
        if ok is None:
            unlabelled += 1
            continue
        if not isinstance(ok, bool):
            raise LaunchError("line %d: ok must be true/false, got %r" % (line_no, ok))
        per_segment.setdefault(segment, []).append(ok)
    return per_segment, unlabelled


def windows(outcomes: list[bool], size: int) -> list[Window]:
    if size <= 0:
        raise LaunchError("window size must be positive, got %d" % size)
    out: list[Window] = []
    for start in range(0, len(outcomes), size):
        chunk = outcomes[start : start + size]
        out.append(
            Window(
                index=len(out) + 1,
                n=len(chunk),
                successes=sum(1 for ok in chunk if ok),
                complete=len(chunk) == size,
            )
        )
    return out


def _first_sustained_breach(
    wins: list[Window], baseline: float, required: int
) -> int | None:
    """Index of the window where `required` consecutive complete breaches end."""
    run = 0
    for win in wins:
        if not win.complete:
            run = 0
            continue
        if win.rate < baseline:
            run += 1
            if run >= required:
                return win.index
        else:
            run = 0
    return None


def evaluate(
    decision: Decision,
    text: str,
    window_size: int,
    required_windows: int = ROLLBACK_CONSECUTIVE_WINDOWS,
) -> dict[str, Any]:
    per_segment, unlabelled = read_records(text)
    baselines = {rb["segment"]: rb for rb in decision.rollbacks}
    known = {seg.id for seg in decision.segments}
    unknown = sorted(set(per_segment) - known)

    rows: list[dict[str, Any]] = []
    triggered: list[str] = []
    for seg in decision.segments:
        outcomes = per_segment.get(seg.id, [])
        wins = windows(outcomes, window_size)
        row: dict[str, Any] = {
            "segment": seg.id,
            "verdict": seg.verdict,
            "observations": len(outcomes),
            "windows": [
                {
                    "index": w.index,
                    "n": w.n,
                    "successes": w.successes,
                    "rate": round(w.rate, 4),
                    "complete": w.complete,
                }
                for w in wins
            ],
        }
        baseline = baselines.get(seg.id)
        if baseline is None:
            # Not an AUTO segment: observed behaviour is reported, but there is
            # no pre-registered baseline to drift away from.
            row["status"] = "not auto" if seg.verdict != AUTO else "no baseline"
            if not outcomes:
                row["status"] = "not auto; no observations"
            rows.append(row)
            continue

        row["baseline_wilson_lower"] = baseline["baseline_wilson_lower"]
        row["required_consecutive_windows"] = required_windows
        complete = [w for w in wins if w.complete]
        hit = _first_sustained_breach(
            wins, baseline["baseline_wilson_lower"], required_windows
        )
        if not outcomes:
            row["status"] = "no observations"
        elif hit is not None:
            row["status"] = "triggered"
            row["triggered_at_window"] = hit
            triggered.append(seg.id)
        elif len(complete) < required_windows:
            row["status"] = "not enough windows yet"
        else:
            row["status"] = "held"
        rows.append(row)

    return {
        "window_size": window_size,
        "required_consecutive_windows": required_windows,
        "total_cases": sum(len(v) for v in per_segment.values()),
        "unlabelled": unlabelled,
        "unknown_segments": unknown,
        "triggered": triggered,
        "segments": rows,
    }


def render(result: dict[str, Any]) -> str:
    lines = [
        "rollback baseline check",
        "  window size: %d cases   required consecutive breaches: %d"
        % (result["window_size"], result["required_consecutive_windows"]),
        "  cases: %d   without an outcome (skipped, not guessed): %d"
        % (result["total_cases"], result["unlabelled"]),
    ]
    if result["unknown_segments"]:
        lines.append(
            "  NOTE: logs contain segments absent from the contract: %s"
            % ", ".join(result["unknown_segments"])
        )
    lines.append("")
    for row in result["segments"]:
        lines.append(
            "  %-22s %-6s %-24s observations=%d"
            % (row["segment"], row["verdict"], row["status"], row["observations"])
        )
        if "baseline_wilson_lower" in row:
            lines.append(
                "      baseline=%.4f" % row["baseline_wilson_lower"]
            )
        for w in row["windows"]:
            mark = "" if w["complete"] else "  (partial, cannot trigger)"
            lines.append(
                "      window %d: %d/%d = %.4f%s"
                % (w["index"], w["successes"], w["n"], w["rate"], mark)
            )
    lines.append("")
    if result["triggered"]:
        lines.append(
            "  TRIGGERED: %s — route to the recorded fallback and re-open its evidence review"
            % ", ".join(result["triggered"])
        )
    else:
        lines.append("  no segment breached its baseline for the required window count")
    return "\n".join(lines)

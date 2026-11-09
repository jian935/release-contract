"""Build a contract from a CSV of raw counts.

The point of this module is to remove the last hand-typed step between an eval
run and a release decision, without ever accepting a caller-chosen rate: the
CSV must carry `n` and `successes`. A `success_rate` column is rejected on
purpose, because a rate without its denominator is the thing this project
refuses.

Column names are case-insensitive. Unknown columns are an error, not a silent
drop: a typo like `sucesses` must not become a default of 0.
"""

from __future__ import annotations

import csv
import io
import math
from typing import Any

REQUIRED = ("id", "n", "successes")
OPTIONAL = (
    "volume_share",
    "harm_if_wrong",
    "fallback",
    "cost_per_case",
    "human_review_cost",
)
REJECTED_WITH_REASON = {
    "success_rate": (
        "a rate without its denominator cannot be audited; export n and "
        "successes instead"
    ),
    "accuracy": "this is a release decision input, not a quality score; export n and successes",
}

DEFAULTS: dict[str, Any] = {
    "volume_share": 0.0,
    "harm_if_wrong": "low",
    "fallback": "none",
    "cost_per_case": 0.0,
    "human_review_cost": 0.0,
}


class CountsError(ValueError):
    """Raised when the CSV cannot be turned into a contract honestly."""


def _normalise_header(field: str | None) -> str:
    return (field or "").lstrip("\ufeff").strip().lower().replace(" ", "_")


def build(
    text: str,
    product: str,
    min_sample_size: int = 100,
    min_success_rate: float = 0.9,
    max_harm: str = "medium",
    max_cost_per_case: float = 0.5,
    z: float = 1.96,
) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise CountsError("CSV has no header row")

    header = [_normalise_header(f) for f in reader.fieldnames]
    unknown = [h for h in header if h not in REQUIRED + OPTIONAL + tuple(REJECTED_WITH_REASON)]
    if unknown:
        raise CountsError(
            "unknown column(s): %s; allowed: %s"
            % (sorted(unknown), sorted(REQUIRED + OPTIONAL))
        )
    refused = [h for h in header if h in REJECTED_WITH_REASON]
    if refused:
        raise CountsError(
            "%s: %s" % (refused[0], REJECTED_WITH_REASON[refused[0]])
        )
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        raise CountsError("missing required column(s): %s" % missing)

    segments: list[dict[str, Any]] = []
    for line_no, row in enumerate(reader, start=2):
        clean = {_normalise_header(k): (v or "").strip() for k, v in row.items() if k}

        def _num(key: str, default: Any, integer: bool = False) -> Any:
            raw = clean.get(key, "")
            if raw == "":
                return default
            try:
                value = float(raw)
            except ValueError:
                raise CountsError(
                    "row %d: %s=%r is not a number" % (line_no, key, raw)
                ) from None
            if not math.isfinite(value):
                # "inf" and "nan" parse as floats. NaN would sail through every
                # threshold comparison and turn a broken row into a released
                # segment, so it is refused at the edge.
                raise CountsError(
                    "row %d: %s=%r must be a finite number" % (line_no, key, raw)
                )
            if integer:
                if value != int(value):
                    raise CountsError(
                        "row %d: %s=%r must be a whole number" % (line_no, key, raw)
                    )
                return int(value)
            return value

        seg_id = clean.get("id", "")
        if not seg_id:
            raise CountsError("row %d: id is empty" % line_no)
        n = _num("n", None, integer=True)
        successes = _num("successes", None, integer=True)
        if n is None or successes is None:
            raise CountsError("row %d: n and successes are both required" % line_no)
        segments.append(
            {
                "id": seg_id,
                "volume_share": _num("volume_share", DEFAULTS["volume_share"]),
                "n": n,
                "successes": successes,
                "harm_if_wrong": clean.get("harm_if_wrong") or DEFAULTS["harm_if_wrong"],
                "fallback": clean.get("fallback") or DEFAULTS["fallback"],
                "cost_per_case": _num("cost_per_case", DEFAULTS["cost_per_case"]),
                "human_review_cost": _num(
                    "human_review_cost", DEFAULTS["human_review_cost"]
                ),
            }
        )

    if not segments:
        raise CountsError("CSV has no data rows")
    return {
        "product": product,
        "guardrails": {
            "min_sample_size": min_sample_size,
            "min_success_rate": min_success_rate,
            "max_harm": max_harm,
            "max_cost_per_case": max_cost_per_case,
            "z": z,
        },
        "segments": segments,
    }

"""Deterministic release-contract decision engine (zero dependencies).

Design rules -- deliberate, do not "simplify" them away:

* Raw counts, not rates. A segment reports ``successes`` and ``n`` so the
  caller cannot pick a flattering denominator.
* Wilson lower bound, not the point estimate. A tiny sample with a shiny
  average must not be released.
* Verdicts come only from the gates. Evidence-risk flags are advisory and
  NEVER change a verdict, otherwise the tool could be tuned to look good.
* No LLM, no network, no randomness. Same JSON in, byte-identical JSON out.

``disabled`` exists for *ablation*, not for shipping: it lets a reviewer ask
"what would change if we ignored this gate?" and lets the test suite prove
that every gate is load-bearing. The default is no gate disabled.

This is a *release decision* tool, not an eval framework and not a deploy
audit. It does not measure quality; it decides which traffic segments the
existing offline evidence is strong enough to cover.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, FrozenSet, Iterable

HARM_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}
FALLBACKS: tuple[str, ...] = ("none", "human", "degrade", "rollback")

AUTO = "AUTO"
FENCE = "FENCE"
HOLD = "HOLD"
_STRICTNESS: dict[str, int] = {AUTO: 0, FENCE: 1, HOLD: 2}

# How many consecutive observation windows must fall below the recorded baseline
# before an AUTO segment is considered to have drifted. Single source of truth:
# the report text and `release_contract.launch` both read it from here.
ROLLBACK_CONSECUTIVE_WINDOWS = 2


def _require_int(field: str, value: Any) -> None:
    """Integers must be integers: `True` and 200.0 are not counts.

    Without this, `n: "200"` surfaced as `'<' not supported between instances of
    'str' and 'int'` — exit 3, but an implementation leak instead of a readable
    error a caller can act on.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(
            "%s must be an integer, got %r" % (field, value)
        )


def _require_number(field: str, value: Any) -> None:
    """Numbers must be real numbers.

    NaN is the dangerous one: `NaN >= 0` is False, so a range check written as
    `if value < 0` lets it through, and `NaN > limit` is also False, so a NaN
    cost silently passes gate G5 and releases the segment. Reject it here.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError("%s must be a number, got %r" % (field, value))
    if not math.isfinite(float(value)):
        raise ContractError("%s must be finite, got %r" % (field, value))

# Five per-segment gates plus one global coverage gate.
SEGMENT_GATES: tuple[str, ...] = (
    "G1_SAMPLE",
    "G2_WILSON",
    "G3_HARM",
    "G4_FALLBACK",
    "G5_COST",
)
GLOBAL_GATES: tuple[str, ...] = ("G6_COVERAGE",)
ALL_GATES: tuple[str, ...] = SEGMENT_GATES + GLOBAL_GATES

NO_GATES: FrozenSet[str] = frozenset()


class ContractError(ValueError):
    """Raised when a contract is structurally invalid or self-serving."""


@dataclass(frozen=True)
class Guardrails:
    min_sample_size: int = 100
    min_success_rate: float = 0.90
    max_harm: str = "medium"
    max_cost_per_case: float = 0.50
    z: float = 1.96

    def __post_init__(self) -> None:
        _require_int("min_sample_size", self.min_sample_size)
        _require_number("min_success_rate", self.min_success_rate)
        _require_number("max_cost_per_case", self.max_cost_per_case)
        _require_number("z", self.z)
        if self.min_sample_size < 1:
            raise ContractError("min_sample_size must be >= 1")
        if not 0.0 <= self.min_success_rate <= 1.0:
            raise ContractError("min_success_rate must be within [0, 1]")
        if not isinstance(self.max_harm, str) or self.max_harm not in HARM_RANK:
            raise ContractError("max_harm must be one of %s" % (tuple(HARM_RANK),))
        if self.max_cost_per_case < 0:
            raise ContractError("max_cost_per_case must be >= 0")
        if self.z <= 0:
            raise ContractError("z must be > 0")


@dataclass(frozen=True)
class Segment:
    id: str
    volume_share: float
    n: int
    successes: int
    harm_if_wrong: str
    fallback: str
    cost_per_case: float
    human_review_cost: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise ContractError("segment id must be a string, got %r" % (self.id,))
        _require_number("volume_share", self.volume_share)
        _require_int("n", self.n)
        _require_int("successes", self.successes)
        _require_number("cost_per_case", self.cost_per_case)
        _require_number("human_review_cost", self.human_review_cost)
        if not self.id:
            raise ContractError("segment id must be non-empty")
        if not 0.0 <= self.volume_share <= 1.0:
            raise ContractError("volume_share must be within [0, 1]: %s" % self.id)
        if self.n < 0:
            raise ContractError("n must be >= 0: %s" % self.id)
        if not 0 <= self.successes <= self.n:
            raise ContractError("successes must be within [0, n]: %s" % self.id)
        if self.harm_if_wrong not in HARM_RANK:
            raise ContractError("unknown harm_if_wrong: %s" % self.harm_if_wrong)
        if self.fallback not in FALLBACKS:
            raise ContractError("unknown fallback: %s" % self.fallback)
        if self.cost_per_case < 0 or self.human_review_cost < 0:
            raise ContractError("costs must be >= 0: %s" % self.id)

    @property
    def observed_rate(self) -> float:
        return self.successes / self.n if self.n else 0.0

    @property
    def loaded_cost(self) -> float:
        """Per-case cost including the human fallback it would actually need."""
        return self.cost_per_case + (
            self.human_review_cost if self.fallback == "human" else 0.0
        )


@dataclass(frozen=True)
class Contract:
    product: str
    segments: tuple[Segment, ...]
    guardrails: Guardrails = Guardrails()

    def __post_init__(self) -> None:
        if not self.product:
            raise ContractError("product must be non-empty")
        if not self.segments:
            raise ContractError("contract must declare at least one segment")
        ids = [s.id for s in self.segments]
        if len(ids) != len(set(ids)):
            raise ContractError("segment ids must be unique")
        covered = sum(s.volume_share for s in self.segments)
        # A contract may *under*-cover traffic (that is reported), but never
        # claim more than 100% of it. The denominator is fixed at 1.0.
        if covered > 1.0 + 1e-9:
            raise ContractError(
                "declared volume_share sums to %.6f > 1.0; the denominator is "
                "the full traffic, not a chosen subset" % covered
            )

    @property
    def covered_traffic(self) -> float:
        return sum(s.volume_share for s in self.segments)

    @property
    def uncovered_traffic(self) -> float:
        return max(0.0, 1.0 - self.covered_traffic)


@dataclass(frozen=True)
class GateHit:
    gate: str
    verdict: str
    detail: str


@dataclass(frozen=True)
class SegmentDecision:
    id: str
    verdict: str
    volume_share: float
    observed_rate: float
    wilson_lower: float
    loaded_cost: float
    gates: tuple[GateHit, ...]

    @property
    def primary_gate(self) -> str:
        return self.gates[0].gate if self.gates else "NONE"


@dataclass(frozen=True)
class Decision:
    product: str
    segments: tuple[SegmentDecision, ...]
    traffic: dict[str, float]
    risks: tuple[str, ...]
    rollbacks: tuple[dict[str, Any], ...]
    coverage_gate: GateHit | None
    # Echoed so a decision records the thresholds it was made under. Without it,
    # omitting `guardrails` silently applied defaults nobody could see.
    guardrails: dict[str, Any]


def _check_disabled(disabled: FrozenSet[str]) -> None:
    unknown = set(disabled) - set(ALL_GATES)
    if unknown:
        raise ContractError("unknown gates in ablation: %s" % sorted(unknown))


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. Returns (lower, upper), clamped to [0, 1].

    The argument order is (successes, n), matching Segment. Passing it
    backwards would otherwise produce a negative variance under the root.
    """
    if not 0 <= successes <= n:
        raise ValueError(
            "wilson_interval expects (successes, n) with 0 <= successes <= n"
        )
    if n == 0:
        return 0.0, 1.0
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1.0 - p) / n + z2 / (4 * n * n)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def wilson_lower(successes: int, n: int, z: float = 1.96) -> float:
    return wilson_interval(successes, n, z)[0]


def evaluate_segment(
    seg: Segment, gr: Guardrails, disabled: FrozenSet[str] = NO_GATES
) -> SegmentDecision:
    """Apply the five per-segment gates; every triggered gate is reported."""
    _check_disabled(disabled)
    lower, _ = wilson_interval(seg.successes, seg.n, gr.z)
    hits: list[GateHit] = []

    if "G1_SAMPLE" not in disabled and seg.n < gr.min_sample_size:
        hits.append(
            GateHit(
                "G1_SAMPLE",
                HOLD,
                "n=%d below min_sample_size=%d; evidence is missing, not negative"
                % (seg.n, gr.min_sample_size),
            )
        )
    if "G2_WILSON" not in disabled and lower < gr.min_success_rate:
        hits.append(
            GateHit(
                "G2_WILSON",
                FENCE,
                "Wilson lower bound %.4f below min_success_rate=%.4f "
                "(observed rate %.4f is not sufficient evidence)"
                % (lower, gr.min_success_rate, seg.observed_rate),
            )
        )
    if (
        "G3_HARM" not in disabled
        and HARM_RANK[seg.harm_if_wrong] > HARM_RANK[gr.max_harm]
    ):
        hits.append(
            GateHit(
                "G3_HARM",
                FENCE,
                "harm_if_wrong=%s exceeds allowed max_harm=%s"
                % (seg.harm_if_wrong, gr.max_harm),
            )
        )
    if (
        "G4_FALLBACK" not in disabled
        and HARM_RANK[seg.harm_if_wrong] >= HARM_RANK["high"]
        and seg.fallback == "none"
    ):
        hits.append(
            GateHit(
                "G4_FALLBACK",
                FENCE,
                "high-harm segment declares fallback=none; no contained damage path",
            )
        )
    if "G5_COST" not in disabled and seg.loaded_cost > gr.max_cost_per_case:
        hits.append(
            GateHit(
                "G5_COST",
                FENCE,
                "loaded cost %.4f (incl. human fallback) above max_cost_per_case=%.4f"
                % (seg.loaded_cost, gr.max_cost_per_case),
            )
        )

    verdict = max(
        (h.verdict for h in hits), key=lambda v: _STRICTNESS[v], default=AUTO
    )
    return SegmentDecision(
        id=seg.id,
        verdict=verdict,
        volume_share=seg.volume_share,
        observed_rate=seg.observed_rate,
        wilson_lower=lower,
        loaded_cost=seg.loaded_cost,
        gates=tuple(hits),
    )


def _evidence_risks(
    contract: Contract, decisions: Iterable[SegmentDecision]
) -> tuple[str, ...]:
    """Advisory Goodhart / provenance flags. These NEVER change a verdict."""
    segs = contract.segments
    gr = contract.guardrails
    risks: set[str] = set()

    if contract.uncovered_traffic > 1e-9:
        risks.add("uncovered_traffic")
    auto_lowers = [
        wilson_lower(s.successes, s.n, gr.z)
        for s, d in zip(segs, decisions)
        if d.verdict == AUTO
    ]
    if auto_lowers and all(
        0.0 <= low - gr.min_success_rate < 0.01 for low in auto_lowers
    ):
        risks.add("threshold_hugging")
    if any(s.successes == s.n for s in segs):
        risks.add("no_failure_observed")
    if len(segs) > 1 and len({s.n for s in segs}) == 1:
        risks.add("uniform_sample_sizes")
    if all(s.cost_per_case == 0 for s in segs):
        risks.add("zero_cost")
    if gr.min_success_rate == 0.0:
        # A zero floor makes gate G2 vacuous: every segment passes it, including
        # one that failed every case. The contract is still honoured (it is the
        # caller's stated policy), but the decision says so out loud.
        risks.add("success_floor_is_zero")
    return tuple(sorted(risks))


def _rollback_triggers(
    contract: Contract, decisions: Iterable[SegmentDecision]
) -> tuple[dict[str, Any], ...]:
    out: list[dict[str, Any]] = []
    for seg, dec in zip(contract.segments, decisions):
        if dec.verdict != AUTO:
            continue
        baseline = round(dec.wilson_lower, 4)
        out.append(
            {
                "segment": seg.id,
                "baseline_wilson_lower": baseline,
                "consecutive_windows": ROLLBACK_CONSECUTIVE_WINDOWS,
                "trigger": (
                    "observed success rate below %.4f for %d consecutive windows"
                    % (baseline, ROLLBACK_CONSECUTIVE_WINDOWS)
                ),
                "action": (
                    "route this segment to %s, then re-open its evidence review"
                    % (seg.fallback if seg.fallback != "none" else "manual review")
                ),
                "capacity_note": (
                    "human fallback must be staffed for %.1f%% of traffic before AUTO"
                    % (seg.volume_share * 100)
                ),
            }
        )
    return tuple(out)


def decide(
    contract: Contract, disabled: FrozenSet[str] = NO_GATES
) -> Decision:
    """Pure function: the same Contract always produces the same Decision."""
    _check_disabled(disabled)
    decisions = tuple(
        evaluate_segment(s, contract.guardrails, disabled)
        for s in contract.segments
    )

    buckets = {AUTO: 0.0, FENCE: 0.0, HOLD: 0.0}
    for dec in decisions:
        buckets[dec.verdict] += dec.volume_share
    traffic = {
        "auto": round(buckets[AUTO], 6),
        "fence": round(buckets[FENCE], 6),
        "hold": round(buckets[HOLD], 6),
        # The coverage gate can be ablated for review, but the accounting
        # cannot: undeclared traffic is never silently dropped.
        "uncovered": round(contract.uncovered_traffic, 6),
        "denominator": 1.0,
    }
    accounted = sum(traffic[k] for k in ("auto", "fence", "hold", "uncovered"))
    if abs(accounted - 1.0) > 1e-6:
        raise ContractError("traffic accounting does not sum to full traffic")

    coverage_gate = None
    if (
        "G6_COVERAGE" not in disabled
        and contract.uncovered_traffic > 1e-9
    ):
        coverage_gate = GateHit(
            "G6_COVERAGE",
            HOLD,
            "%.1f%% of traffic has no declared segment; it is reported as "
            "uncovered, never silently dropped" % (contract.uncovered_traffic * 100),
        )

    return Decision(
        product=contract.product,
        segments=decisions,
        traffic=traffic,
        risks=_evidence_risks(contract, decisions),
        rollbacks=_rollback_triggers(contract, decisions),
        coverage_gate=coverage_gate,
        guardrails=dict(contract.guardrails.__dict__),
    )


def contract_from_dict(data: dict[str, Any]) -> Contract:
    """Strict loader. Unknown keys are rejected so silent typos cannot pass."""
    if not isinstance(data, dict):
        raise ContractError("contract root must be an object")
    allowed_root = {"product", "segments", "guardrails"}
    unknown = set(data) - allowed_root
    if unknown:
        raise ContractError("unknown contract keys: %s" % sorted(unknown))

    raw_gr = data.get("guardrails", {})
    if not isinstance(raw_gr, dict):
        raise ContractError("guardrails must be an object")
    allowed_gr = set(Guardrails().__dict__)
    unknown = set(raw_gr) - allowed_gr
    if unknown:
        raise ContractError("unknown guardrail keys: %s" % sorted(unknown))
    gr = Guardrails(**raw_gr)

    raw_segs = data.get("segments")
    if not isinstance(raw_segs, list):
        raise ContractError("segments must be a list")
    allowed_seg = set(Segment.__dataclass_fields__)
    segs: list[Segment] = []
    for i, raw in enumerate(raw_segs):
        if not isinstance(raw, dict):
            raise ContractError("segment %d must be an object" % i)
        unknown = set(raw) - allowed_seg
        if unknown:
            raise ContractError("unknown segment keys at %d: %s" % (i, sorted(unknown)))
        try:
            segs.append(Segment(**raw))
        except TypeError as exc:
            raise ContractError("segment %d: %s" % (i, exc)) from exc

    product = data.get("product", "")
    if not isinstance(product, str):
        raise ContractError("product must be a string, got %r" % (product,))
    return Contract(product=product, segments=tuple(segs), guardrails=gr)


def _reject_json_constant(name: str) -> Any:
    """`json.loads` accepts NaN/Infinity by default; strict JSON does not.

    Rejecting them at parse time means a contract can never carry a value that
    compares False against every threshold.
    """
    raise ContractError(
        "%s is not valid JSON here; every number must be finite" % name
    )


def load_contract(path: str | Path) -> Contract:
    text = Path(path).read_text(encoding="utf-8-sig")
    return contract_from_dict(json.loads(text, parse_constant=_reject_json_constant))

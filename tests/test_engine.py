"""Engine unit tests, including gate-ablation (reverse) tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from release_contract.engine import (
    ALL_GATES,
    AUTO,
    FENCE,
    HOLD,
    SEGMENT_GATES,
    Contract,
    ContractError,
    Guardrails,
    Segment,
    decide,
    load_contract,
    wilson_interval,
    wilson_lower,
)
from release_contract.evalset import case_contract, load_cases
from release_contract.report import to_json

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo_contract.json"


def _seg(**kw) -> Segment:
    base = dict(
        id="s",
        volume_share=1.0,
        n=250,
        successes=240,
        harm_if_wrong="low",
        fallback="none",
        cost_per_case=0.02,
        human_review_cost=0.0,
    )
    base.update(kw)
    return Segment(**base)


def _verdict_map(which: str, disabled=frozenset()) -> dict[str, tuple]:
    out: dict[str, tuple] = {}
    for case in load_cases(which):
        d = decide(case_contract(case), disabled)
        out[case["id"]] = tuple((s.id, s.verdict) for s in d.segments)
    return out


class TestWilson(unittest.TestCase):
    def test_perfect_tiny_sample_is_not_evidence(self):
        bar = Guardrails().min_success_rate
        self.assertTrue(wilson_lower(30, 30) < bar)

    def test_same_point_estimate_narrows_with_sample(self):
        self.assertTrue(wilson_lower(388, 400) < wilson_lower(970, 1000))

    def test_reversed_arguments_rejected_loudly(self):
        with self.assertRaises(ValueError):
            wilson_interval(400, 388)

    def test_interval_stays_bounded(self):
        for n, k in ((0, 0), (1, 0), (1, 1), (30, 30), (1000, 1), (1000, 999)):
            lo, hi = wilson_interval(k, n)
            self.assertTrue(0.0 <= lo <= hi <= 1.0, (n, k, lo, hi))


class TestGates(unittest.TestCase):
    def test_clean_segment_is_auto(self):
        d = decide(Contract(product="p", segments=(_seg(),)))
        self.assertTrue(d.segments[0].verdict == AUTO)
        self.assertTrue(d.segments[0].primary_gate == "NONE")

    def test_sample_gate_is_hold(self):
        d = decide(Contract(product="p", segments=(_seg(n=40, successes=39),)))
        self.assertTrue(d.segments[0].verdict == HOLD)

    def test_hold_outranks_fence(self):
        d = decide(
            Contract(
                product="p",
                segments=(
                    _seg(n=40, successes=20, harm_if_wrong="critical", fallback="none", cost_per_case=9.0),
                ),
            )
        )
        self.assertTrue(d.segments[0].verdict == HOLD)
        gates = [g.gate for g in d.segments[0].gates]
        self.assertTrue("G1_SAMPLE" in gates and "G2_WILSON" in gates)

    def test_harm_gate_overrides_strong_evidence(self):
        d = decide(
            Contract(
                product="p",
                segments=(_seg(n=1000, successes=990, harm_if_wrong="critical", fallback="human"),),
            )
        )
        self.assertTrue(d.segments[0].verdict == FENCE)

    def test_fallback_gate_needs_high_harm_and_no_path(self):
        fenced = decide(
            Contract(product="p", segments=(_seg(harm_if_wrong="high", fallback="none"),))
        )
        self.assertTrue("G4_FALLBACK" in [g.gate for g in fenced.segments[0].gates])
        allowed = decide(
            Contract(product="p", segments=(_seg(harm_if_wrong="low", fallback="none"),))
        )
        self.assertTrue("G4_FALLBACK" not in [g.gate for g in allowed.segments[0].gates])

    def test_human_fallback_is_priced_but_other_paths_are_not(self):
        human = _seg(fallback="human", cost_per_case=0.1, human_review_cost=0.9)
        degrade = _seg(fallback="degrade", cost_per_case=0.1, human_review_cost=0.9)
        self.assertTrue(human.loaded_cost > Guardrails().max_cost_per_case)
        self.assertTrue(degrade.loaded_cost < Guardrails().max_cost_per_case)


class TestStrictLoading(unittest.TestCase):
    def test_unknown_key_rejected(self):
        from release_contract.engine import contract_from_dict

        with self.assertRaises(ContractError):
            contract_from_dict({"product": "p", "segments": [], "typo": 1})

    def test_overclaimed_traffic_rejected(self):
        from release_contract.engine import contract_from_dict

        raw = {
            "product": "p",
            "segments": [
                {"id": "a", "volume_share": 0.8, "n": 10, "successes": 9,
                 "harm_if_wrong": "low", "fallback": "none", "cost_per_case": 0.1},
                {"id": "b", "volume_share": 0.8, "n": 10, "successes": 9,
                 "harm_if_wrong": "low", "fallback": "none", "cost_per_case": 0.1},
            ],
        }
        with self.assertRaises(ContractError):
            contract_from_dict(raw)

    def test_successes_above_n_rejected(self):
        with self.assertRaises(ContractError):
            _seg(n=10, successes=11)

    def test_duplicate_segment_ids_rejected(self):
        with self.assertRaises(ContractError):
            Contract(product="p", segments=(_seg(), _seg()))


class TestAccounting(unittest.TestCase):
    def test_four_buckets_sum_to_full_traffic(self):
        d = decide(load_contract(DEMO))
        buckets = ("auto", "fence", "hold", "uncovered")
        self.assertTrue(abs(sum(d.traffic[k] for k in buckets) - 1.0) < 1e-6)
        self.assertTrue(d.traffic["denominator"] == 1.0)
        self.assertTrue(d.coverage_gate is not None)

    def test_advisory_risks_do_not_change_verdict(self):
        d = decide(
            Contract(product="p", segments=(_seg(n=250, successes=250),))
        )
        self.assertTrue("no_failure_observed" in d.risks)
        self.assertTrue(d.segments[0].verdict == AUTO)

    def test_byte_identical_replay(self):
        a = to_json(decide(load_contract(DEMO)))
        b = to_json(decide(load_contract(DEMO)))
        self.assertTrue(a == b)


class TestAblation(unittest.TestCase):
    """Reverse tests: removing any gate MUST change at least one eval verdict."""

    def test_every_segment_gate_is_load_bearing(self):
        baseline = {**_verdict_map("dev"), **_verdict_map("holdout")}
        for gate in SEGMENT_GATES:
            ablated = {
                **_verdict_map("dev", frozenset({gate})),
                **_verdict_map("holdout", frozenset({gate})),
            }
            changed = [k for k in baseline if baseline[k] != ablated[k]]
            self.assertTrue(changed, "gate %s changed no verdict at all" % gate)

    def test_global_gate_does_not_hide_uncovered_traffic(self):
        case = next(c for c in load_cases("dev") if c["id"] == "dev-015")
        normal = decide(case_contract(case))
        ablated = decide(case_contract(case), frozenset({"G6_COVERAGE"}))
        self.assertTrue(normal.coverage_gate is not None)
        self.assertTrue(ablated.coverage_gate is None)
        self.assertTrue(normal.traffic["uncovered"] == ablated.traffic["uncovered"])
        self.assertTrue(
            [s.verdict for s in normal.segments] == [s.verdict for s in ablated.segments]
        )

    def test_unknown_ablation_gate_rejected(self):
        with self.assertRaises(ContractError):
            decide(Contract(product="p", segments=(_seg(),)), frozenset({"G9_NOPE"}))

    def test_all_gates_declared(self):
        self.assertTrue(len(set(ALL_GATES)) == len(ALL_GATES))


if __name__ == "__main__":
    unittest.main()

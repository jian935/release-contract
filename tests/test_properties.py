"""Unit tests for golden-label-free property checks."""

from __future__ import annotations

import unittest

from release_contract.engine import AUTO, FENCE, HOLD, Contract, Segment, decide, wilson_lower
from release_contract.properties import scan


def _seg(**kw) -> Segment:
    base = dict(
        id="s", volume_share=1.0, n=250, successes=240,
        harm_if_wrong="low", fallback="none",
        cost_per_case=0.02, human_review_cost=0.0,
    )
    base.update(kw)
    return Segment(**base)


class TestInvariants(unittest.TestCase):
    def test_wilson_lower_is_monotone_at_fixed_rate(self):
        previous = -1.0
        for n in (30, 60, 100, 250, 500, 1000, 5000):
            low = wilson_lower(int(round(0.95 * n)), n)
            self.assertTrue(low + 1e-12 >= previous)
            previous = low

    def test_disabling_a_gate_never_reduces_auto(self):
        c = Contract(
            product="p",
            segments=(
                _seg(id="a", volume_share=0.4, n=40, successes=39),
                _seg(id="b", volume_share=0.3, n=1000, successes=900),
                _seg(id="c", volume_share=0.3, harm_if_wrong="critical", fallback="none"),
            ),
        )
        normal = decide(c)
        base = sum(1 for s in normal.segments if s.verdict == AUTO)
        for gate in ("G1_SAMPLE", "G2_WILSON", "G3_HARM", "G4_FALLBACK", "G5_COST"):
            ablated = decide(c, frozenset({gate}))
            after = sum(1 for s in ablated.segments if s.verdict == AUTO)
            self.assertTrue(after >= base, gate)

    def test_undercovered_contract_still_accounts_for_full_traffic(self):
        c = Contract(product="p", segments=(_seg(volume_share=0.37),))
        d = decide(c)
        total = sum(d.traffic[k] for k in ("auto", "fence", "hold", "uncovered"))
        self.assertTrue(abs(total - 1.0) < 1e-6)
        self.assertTrue(d.coverage_gate is not None)

    def test_scan_reports_violations_as_data_not_exceptions(self):
        result = scan(trials=15)
        self.assertTrue(isinstance(result["violations"], list))
        self.assertTrue(result["passed"] == (len(result["violations"]) == 0))


if __name__ == "__main__":
    unittest.main()

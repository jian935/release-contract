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


class TestScannerHasTeeth(unittest.TestCase):
    """An invariant check that can never fail is decoration.

    Each test feeds `scan` a deliberately broken decider and requires a
    violation. If these pass, the scanner would notice a real regression.
    """

    def _broken(self, bug):
        from dataclasses import replace

        def decider(contract, *args, **kwargs):
            decision = decide(contract, *args, **kwargs)
            return replace(decision, segments=bug(contract, decision))

        return decider

    def test_catches_verdicts_that_depend_on_segment_order(self):
        from dataclasses import replace

        def bug(contract, decision):
            segs = list(decision.segments)
            if segs:
                flip = "HOLD" if segs[0].verdict == AUTO else AUTO
                segs[0] = replace(segs[0], verdict=flip)
            return tuple(segs)

        result = scan(trials=40, decide_fn=self._broken(bug))
        self.assertTrue(any("segment order" in v for v in result["violations"]))

    def test_catches_more_successes_making_a_verdict_stricter(self):
        from dataclasses import replace

        def bug(contract, decision):
            perfect = {s.id for s in contract.segments if s.n > 0 and s.successes == s.n}
            return tuple(
                replace(s, verdict=HOLD) if s.id in perfect else s
                for s in decision.segments
            )

        result = scan(trials=40, decide_fn=self._broken(bug))
        self.assertTrue(
            any("more successes" in v for v in result["violations"])
        )

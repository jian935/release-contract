"""Baseline-drift checks: the second half of the rollback promise.

Each test pins one rule that keeps the comparison honest — a partial window never
fires, a healthy window resets the run, silence is not success, and the required
window count comes from the engine rather than being typed twice.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from release_contract.engine import (
    ROLLBACK_CONSECUTIVE_WINDOWS,
    contract_from_dict,
    decide,
)
from release_contract.launch import (
    LaunchError,
    evaluate,
    read_records,
    render,
    windows,
)

ROOT = Path(__file__).resolve().parents[1]


def _contract(**overrides):
    segment = {
        "id": "seg",
        "volume_share": 1.0,
        "n": 100,
        "successes": 98,
        "harm_if_wrong": "low",
        "fallback": "none",
        "cost_per_case": 0.02,
        "human_review_cost": 0.0,
    }
    segment.update(overrides)
    return contract_from_dict(
        {
            "product": "test",
            "guardrails": {
                "min_sample_size": 100,
                "min_success_rate": 0.9,
                "max_harm": "medium",
                "max_cost_per_case": 0.5,
                "z": 1.96,
            },
            "segments": [segment],
        }
    )


def _log(pattern: list[tuple[int, int]], segment: str = "seg", size: int = 10) -> str:
    """Build a log from (successes, n) pairs."""
    lines: list[str] = []
    for successes, n in pattern:
        lines.extend(
            json.dumps({"segment": segment, "ok": True}) for _ in range(successes)
        )
        lines.extend(
            json.dumps({"segment": segment, "ok": False}) for _ in range(n - successes)
        )
    return "\n".join(lines) + "\n"


class TestWindows(unittest.TestCase):
    def test_splits_by_count_and_marks_the_tail(self):
        wins = windows([True] * 25, 10)
        self.assertTrue([w.n for w in wins] == [10, 10, 5])
        self.assertTrue([w.complete for w in wins] == [True, True, False])

    def test_rejects_non_positive_size(self):
        with self.assertRaises(LaunchError):
            windows([True], 0)


class TestRecordParsing(unittest.TestCase):
    def test_missing_outcome_is_skipped_not_counted_as_failure(self):
        text = (
            '{"segment":"seg","ok":true}\n'
            '{"segment":"seg"}\n'
            '{"segment":"seg","ok":false}\n'
        )
        per_segment, unlabelled = read_records(text)
        self.assertTrue(per_segment["seg"] == [True, False])
        self.assertTrue(unlabelled == 1)

    def test_non_boolean_outcome_is_an_error(self):
        with self.assertRaises(LaunchError):
            read_records('{"segment":"seg","ok":"yes"}\n')

    def test_missing_segment_is_an_error(self):
        with self.assertRaises(LaunchError):
            read_records('{"ok":true}\n')


class TestDriftEvaluation(unittest.TestCase):
    def setUp(self):
        self.decision = decide(_contract())
        self.baseline = self.decision.rollbacks[0]["baseline_wilson_lower"]

    def _run(self, pattern, size=10):
        return evaluate(self.decision, _log(pattern), size)

    def test_single_breach_does_not_trigger(self):
        # One window at 0.50 against a 0.888 baseline, then back above it.
        result = self._run([(5, 10), (10, 10), (10, 10)])
        self.assertTrue(result["triggered"] == [])
        self.assertTrue(result["segments"][0]["status"] == "held")

    def test_two_consecutive_breaches_trigger_at_the_second(self):
        result = self._run([(10, 10), (5, 10), (5, 10)])
        self.assertTrue(result["triggered"] == ["seg"])
        self.assertTrue(result["segments"][0]["triggered_at_window"] == 3)

    def test_healthy_window_resets_the_run(self):
        result = self._run([(5, 10), (10, 10), (5, 10)])
        self.assertTrue(result["triggered"] == [])

    def test_partial_window_cannot_trigger_even_if_it_breaches(self):
        # Two full healthy windows, then a short tail that is far below baseline.
        result = self._run([(10, 10), (10, 10), (0, 5)])
        self.assertTrue(result["triggered"] == [])
        self.assertTrue(result["segments"][0]["status"] == "held")
        self.assertFalse(result["segments"][0]["windows"][-1]["complete"])

    def test_not_enough_windows_is_not_reported_as_held(self):
        result = self._run([(10, 10)])
        self.assertTrue(result["segments"][0]["status"] == "not enough windows yet")

    def test_segment_without_observations_is_never_called_healthy(self):
        result = evaluate(self.decision, "", 10)
        self.assertTrue(result["segments"][0]["status"] == "no observations")
        self.assertTrue(result["triggered"] == [])

    def test_unknown_log_segment_is_reported(self):
        result = evaluate(self.decision, _log([(10, 10)], segment="other"), 10)
        self.assertTrue(result["unknown_segments"] == ["other"])

    def test_non_auto_segment_gets_no_baseline_claim(self):
        decision = decide(_contract(harm_if_wrong="high"))
        self.assertTrue(decision.segments[0].verdict != "AUTO")
        result = evaluate(decision, _log([(0, 10)]), 10)
        self.assertTrue(result["segments"][0]["status"].startswith("not auto"))
        self.assertTrue("baseline_wilson_lower" not in result["segments"][0])

    def test_required_window_count_comes_from_the_engine(self):
        result = self._run([(10, 10)])
        self.assertTrue(
            result["required_consecutive_windows"] == ROLLBACK_CONSECUTIVE_WINDOWS
        )

    def test_render_never_prints_a_trigger_it_did_not_find(self):
        text = render(self._run([(10, 10), (10, 10)]))
        self.assertTrue("no segment breached its baseline" in text)
        self.assertTrue("TRIGGERED" not in text)


class TestExampleLog(unittest.TestCase):
    def test_shipped_example_matches_its_generator(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "gen_launch_example", ROOT / "scripts" / "gen_launch_example.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        shipped = (ROOT / "examples" / "launch" / "run_log.jsonl").read_text(
            encoding="utf-8"
        )
        self.assertTrue(shipped == module.build())


if __name__ == "__main__":
    unittest.main()

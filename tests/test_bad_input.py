"""How the loader must fail, and what it must accept.

The README promises: bad input exits 3 with one readable line, never a
traceback. These tests hold that promise, plus the specific case that motivated
them — a NaN cost used to pass every threshold comparison and release a segment.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from release_contract.engine import ContractError, contract_from_dict, decide, load_contract
from release_contract.importer import CountsError
from release_contract.importer import build as build_counts

ROOT = Path(__file__).resolve().parents[1]

BASE = {
    "product": "probe",
    "guardrails": {
        "min_sample_size": 100,
        "min_success_rate": 0.9,
        "max_harm": "medium",
        "max_cost_per_case": 0.5,
        "z": 1.96,
    },
    "segments": [
        {
            "id": "s",
            "volume_share": 1.0,
            "n": 200,
            "successes": 190,
            "harm_if_wrong": "low",
            "fallback": "none",
            "cost_per_case": 0.02,
            "human_review_cost": 0.0,
        }
    ],
}


def variant(**changes) -> dict:
    data = json.loads(json.dumps(BASE))
    for key, value in changes.items():
        if key.startswith("g_"):
            data["guardrails"][key[2:]] = value
        elif key.startswith("s_"):
            data["segments"][0][key[2:]] = value
        else:
            data[key] = value
    return data


class TestNumbersMustBeReal(unittest.TestCase):
    """NaN compares False against everything, so it silently passes every gate."""

    def test_nan_cost_is_rejected(self):
        with self.assertRaises(ContractError) as ctx:
            contract_from_dict(variant(s_cost_per_case=float("nan")))
        self.assertTrue("finite" in str(ctx.exception))

    def test_infinite_cost_is_rejected(self):
        with self.assertRaises(ContractError):
            contract_from_dict(variant(s_cost_per_case=float("inf")))

    def test_nan_success_floor_is_rejected(self):
        with self.assertRaises(ContractError):
            contract_from_dict(variant(g_min_success_rate=float("nan")))

    def test_nan_in_json_text_is_rejected_at_parse_time(self):
        # json.loads accepts bare NaN/Infinity by default; strict JSON does not.
        text = json.dumps(variant(s_cost_per_case=float("nan")))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(ContractError) as ctx:
                load_contract(path)
        self.assertTrue("finite" in str(ctx.exception))

    def test_nan_and_infinity_in_counts_csv_are_rejected(self):
        for raw in ("nan", "inf", "-inf"):
            with self.assertRaises(CountsError):
                build_counts("id,n,successes\na,%s,1\n" % raw, "probe")


class TestTypesAreCheckedBeforeArithmetic(unittest.TestCase):
    """A type error must read like an error, not like a Python operator message."""

    def test_string_count_says_it_must_be_an_integer(self):
        with self.assertRaises(ContractError) as ctx:
            contract_from_dict(variant(s_n="200"))
        message = str(ctx.exception)
        self.assertTrue("n must be an integer" in message)
        self.assertFalse("<" in message)

    def test_null_count_is_rejected(self):
        with self.assertRaises(ContractError):
            contract_from_dict(variant(s_successes=None))

    def test_boolean_is_not_a_count(self):
        # isinstance(True, int) is True, so this needs an explicit guard.
        with self.assertRaises(ContractError):
            contract_from_dict(variant(s_n=True))

    def test_non_string_product_is_rejected(self):
        with self.assertRaises(ContractError):
            contract_from_dict(variant(product=42))


class TestRejectedShapes(unittest.TestCase):
    def test_empty_segments(self):
        with self.assertRaises(ContractError):
            contract_from_dict(variant(segments=[]))

    def test_duplicate_ids(self):
        data = variant()
        data["segments"] = data["segments"] * 2
        with self.assertRaises(ContractError):
            contract_from_dict(data)

    def test_successes_above_n(self):
        with self.assertRaises(ContractError):
            contract_from_dict(variant(s_successes=201))

    def test_negative_share(self):
        with self.assertRaises(ContractError):
            contract_from_dict(variant(s_volume_share=-0.01))


class TestAcceptedOnPurpose(unittest.TestCase):
    """Things that look odd but are legitimate; changing them would be a break."""

    def test_unicode_segment_id(self):
        contract = contract_from_dict(variant(s_id="问答-退款"))
        self.assertTrue(contract.segments[0].id == "问答-退款")

    def test_utf8_bom_is_tolerated(self):
        # Excel and Notepad add a BOM; rejecting it taught users nothing.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text("\ufeff" + json.dumps(BASE), encoding="utf-8")
            contract = load_contract(path)
        self.assertTrue(contract.product == "probe")

    def test_omitted_guardrails_apply_documented_defaults_and_are_echoed(self):
        data = {k: v for k, v in BASE.items() if k != "guardrails"}
        decision = decide(contract_from_dict(data))
        self.assertTrue(decision.guardrails["min_sample_size"] == 100)
        self.assertTrue(decision.guardrails["z"] == 1.96)

    def test_zero_success_floor_is_obeyed_but_flagged(self):
        data = variant(g_min_success_rate=0.0, s_successes=0)
        decision = decide(contract_from_dict(data))
        self.assertTrue("success_floor_is_zero" in decision.risks)

    def test_large_counts_stay_finite(self):
        decision = decide(contract_from_dict(variant(s_n=10**18, s_successes=10**18 - 1)))
        self.assertTrue(math.isfinite(decision.segments[0].wilson_lower))


class TestCliNeverPrintsATraceback(unittest.TestCase):
    CASES = {
        "empty file": "",
        "not json": "{oops",
        "json array": "[]",
        "nan cost": json.dumps(variant(s_cost_per_case=float("nan"))),
        "string count": json.dumps(variant(s_n="200")),
        "missing file": None,
    }

    def test_each_bad_contract_exits_three_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in self.CASES.items():
                path = Path(tmp) / ("%s.json" % name.replace(" ", "_"))
                if text is not None:
                    path.write_text(text, encoding="utf-8")
                proc = subprocess.run(
                    [sys.executable, "-m", "release_contract.cli", "decide", str(path)],
                    cwd=str(ROOT),
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                )
                combined = (proc.stdout or "") + (proc.stderr or "")
                self.assertTrue(proc.returncode == 3, "%s exited %d" % (name, proc.returncode))
                self.assertFalse("Traceback" in combined, name)
                self.assertTrue((proc.stderr or "").strip(), name)


if __name__ == "__main__":
    unittest.main()

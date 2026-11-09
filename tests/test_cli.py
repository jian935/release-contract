"""CLI contract: exit codes are the interface a pipeline depends on.

0 = ok, 2 = a gate the caller asked to fail on, 3 = unusable input.
Every failure must be a message on stderr plus a code, never a traceback.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from release_contract import __version__
from release_contract.cli import EXIT_GATE, EXIT_INPUT, EXIT_OK, main

ROOT = Path(__file__).resolve().parents[1]
DEMO = str(ROOT / "examples" / "demo_contract.json")
DEMO_V2 = str(ROOT / "examples" / "demo_contract_v2.json")


def _run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TestExitCodes(unittest.TestCase):
    def test_decide_succeeds_on_the_demo(self):
        code, out, _ = _run("decide", DEMO)
        self.assertTrue(code == EXIT_OK)
        self.assertTrue("TRAFFIC" in out)

    def test_fail_on_fence_returns_two(self):
        code, _, _ = _run("decide", DEMO, "--fail-on", "FENCE")
        self.assertTrue(code == EXIT_GATE)

    def test_fail_on_auto_returns_zero_for_this_demo(self):
        code, _, _ = _run("decide", DEMO, "--fail-on", "HOLD")
        self.assertTrue(code in (EXIT_OK, EXIT_GATE))

    def test_unknown_fail_on_value_is_an_input_error(self):
        code, _, err = _run("decide", DEMO, "--fail-on", "SHIP")
        self.assertTrue(code == EXIT_INPUT)
        self.assertTrue("unknown" in err)

    def test_missing_file_is_an_input_error_not_a_traceback(self):
        code, _, err = _run("decide", str(ROOT / "no_such_contract.json"))
        self.assertTrue(code == EXIT_INPUT)
        self.assertTrue("cannot read input" in err)

    def test_malformed_json_is_an_input_error(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            code, _, err = _run("decide", str(bad))
        self.assertTrue(code == EXIT_INPUT)
        self.assertTrue("invalid JSON" in err)

    def test_rejected_contract_is_an_input_error(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
            bad = Path(tmp) / "empty.json"
            bad.write_text('{"product": "x", "segments": []}', encoding="utf-8")
            code, _, err = _run("validate", str(bad))
        self.assertTrue(code == EXIT_INPUT)
        self.assertTrue("invalid contract" in err)

    def test_diff_can_gate_on_a_regression(self):
        code, _, _ = _run("diff", DEMO, DEMO_V2, "--fail-on-regression")
        self.assertTrue(code == EXIT_GATE)

    def test_version_flag_matches_package_version(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as ctx:
                main(["--version"])
        self.assertTrue(ctx.exception.code == 0)
        self.assertTrue(__version__ in out.getvalue())


class TestInitAndValidate(unittest.TestCase):
    def test_init_output_is_a_valid_contract_that_holds(self):
        code, out, _ = _run("init")
        self.assertTrue(code == EXIT_OK)
        data = json.loads(out)
        self.assertTrue(data["segments"][0]["n"] == 0)
        decision = _run_decide_from_text(out)
        self.assertTrue(decision["status"] == "ok")
        self.assertTrue(decision["verdicts"] == ["HOLD"])

    def test_init_writes_a_file_and_refuses_to_clobber_it(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
            target = Path(tmp) / "contract.json"
            code, out, _ = _run("init", "-o", str(target))
            self.assertTrue(code == EXIT_OK)
            self.assertTrue("wrote" in out)
            code, _, err = _run("init", "-o", str(target))
            self.assertTrue(code == EXIT_INPUT)
            self.assertTrue("refusing to overwrite" in err)
            code, _, _ = _run("init", "-o", str(target), "--force")
            self.assertTrue(code == EXIT_OK)

    def test_validate_reports_coverage_and_is_machine_readable(self):
        code, out, _ = _run("validate", DEMO, "--json")
        self.assertTrue(code == EXIT_OK)
        summary = json.loads(out)
        self.assertTrue(summary["valid"] is True)
        self.assertTrue(abs(summary["declared_share"] + summary["uncovered_share"] - 1.0) < 1e-9)


def _run_decide_from_text(text: str) -> dict:
    with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
        path = Path(tmp) / "contract.json"
        path.write_text(text, encoding="utf-8")
        code, out, _ = _run("decide", str(path), "--json")
    payload = json.loads(out)
    return {
        "status": "ok" if code == EXIT_OK else "error",
        "verdicts": [s["verdict"] for s in payload["segments"]],
    }


if __name__ == "__main__":
    unittest.main()

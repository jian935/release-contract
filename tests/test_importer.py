"""CSV intake: raw counts in, contract out, never a chosen rate."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from release_contract.cli import main
from release_contract.engine import ContractError, contract_from_dict
from release_contract.importer import CountsError, build

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "counts.example.csv"


class TestBuild(unittest.TestCase):
    def test_minimal_columns_become_a_contract(self):
        data = build("id,n,successes\na,400,388\n", product="p")
        self.assertTrue(data["product"] == "p")
        self.assertTrue(len(data["segments"]) == 1)
        self.assertTrue(data["segments"][0]["n"] == 400)
        self.assertTrue(data["segments"][0]["harm_if_wrong"] == "low")

    def test_example_csv_is_valid_and_matches_its_declared_coverage(self):
        data = build(EXAMPLE.read_text(encoding="utf-8"), product="p")
        contract = contract_from_dict(data)
        self.assertTrue(len(contract.segments) == 3)
        self.assertTrue(abs(sum(s.volume_share for s in contract.segments) - 0.95) < 1e-9)

    def test_a_rate_column_is_refused_with_the_reason(self):
        with self.assertRaises(CountsError) as ctx:
            build("id,n,successes,success_rate\na,10,9,0.9\n", product="p")
        self.assertTrue("denominator" in str(ctx.exception))

    def test_unknown_column_is_an_error_not_a_default(self):
        with self.assertRaises(CountsError) as ctx:
            build("id,n,successes,sucesses\na,10,9,9\n", product="p")
        self.assertTrue("unknown column" in str(ctx.exception))

    def test_missing_required_column_names_what_is_missing(self):
        with self.assertRaises(CountsError) as ctx:
            build("id,n\na,10\n", product="p")
        self.assertTrue("successes" in str(ctx.exception))

    def test_non_integer_counts_are_refused(self):
        with self.assertRaises(CountsError) as ctx:
            build("id,n,successes\na,10.5,9\n", product="p")
        self.assertTrue("whole number" in str(ctx.exception))

    def test_successes_above_n_fails_the_shared_loader(self):
        data = build("id,n,successes\na,10,11\n", product="p")
        with self.assertRaises(ContractError):
            contract_from_dict(data)

    def test_bom_and_capitalised_headers_are_accepted(self):
        data = build("\ufeffID,N,Successes\na,10,9\n", product="p")
        self.assertTrue(data["segments"][0]["id"] == "a")

    def test_header_only_is_an_error(self):
        with self.assertRaises(CountsError):
            build("id,n,successes\n", product="p")


class TestImportCli(unittest.TestCase):
    def _run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_import_writes_a_decision_ready_contract(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
            target = Path(tmp) / "c.json"
            code, _, err = self._run(
                "import", str(EXAMPLE), "--product", "p", "-o", str(target)
            )
            self.assertTrue(code == 0)
            self.assertTrue("uncovered" in err)
            saved = json.loads(target.read_text(encoding="utf-8"))
            self.assertTrue(len(saved["segments"]) == 3)
            code, out, _ = self._run("decide", str(target))
            self.assertTrue(code == 0)
            self.assertTrue("TRAFFIC" in out)

    def test_import_refuses_to_clobber(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
            target = Path(tmp) / "c.json"
            target.write_text("{}", encoding="utf-8")
            code, _, err = self._run(
                "import", str(EXAMPLE), "--product", "p", "-o", str(target)
            )
            self.assertTrue(code == 3)
            self.assertTrue("refusing" in err)

    def test_bad_csv_is_an_input_error(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as tmp:
            bad = Path(tmp) / "bad.csv"
            bad.write_text("id,rate\na,0.9\n", encoding="utf-8")
            code, _, err = self._run("import", str(bad), "--product", "p")
            self.assertTrue(code == 3)
            self.assertTrue("invalid counts" in err)


if __name__ == "__main__":
    unittest.main()

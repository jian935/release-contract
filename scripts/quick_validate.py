#!/usr/bin/env python3
"""Run everything a release needs: unit tests, eval suites, invariants, locks.

Usage: python scripts/quick_validate.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_contract.evalset import render as render_eval, run_suite  # noqa: E402
from release_contract.properties import render as render_props, scan  # noqa: E402
from release_contract.selfcheck import render as render_checks, run_checks  # noqa: E402


def main() -> int:
    print("== unit tests ==")
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=str(ROOT),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    # unittest writes its -v report to stderr, so print both streams.
    print((proc.stdout or "")[-6000:])
    print((proc.stderr or "")[-6000:])
    if proc.returncode != 0:
        print("UNIT TESTS FAILED")
        return 1

    print("")
    print("== eval suites ==")
    for which in ("dev", "holdout"):
        print(render_eval(run_suite(which)))
        print("")

    print("== property scan (no golden labels involved) ==")
    props = scan()
    print(render_props(props))
    if not props["passed"]:
        print("PROPERTY SCAN FAILED")
        return 1
    print("")

    print("== blind evaluation status ==")
    # Score the published round when there is one; otherwise whatever local
    # annotation input this checkout happens to have. The script itself
    # reports NOT RUN when there is none.
    blind_args = [sys.executable, "scripts/blind_eval.py"]
    note = ""
    rounds_dir = ROOT / "eval" / "blind" / "rounds"
    published = (
        sorted(p for p in rounds_dir.glob("*/answers.csv")) if rounds_dir.is_dir() else []
    )
    if published:
        latest = published[-1]
        blind_args.append(latest.relative_to(ROOT).as_posix())
        note = "  (published round: %s)" % latest.parent.name
        # A round may be scored against a different question set. Scoring it
        # against the default prompts rejects every row, so read the set the
        # result was published with.
        frozen = latest.parent / "result.json"
        declared = None
        if frozen.exists():
            try:
                declared = json.loads(frozen.read_text(encoding="utf-8")).get("prompts")
            except ValueError:
                declared = None
        if declared:
            blind_args.extend(["--prompts", declared])
            note += " scored against %s" % declared
    else:
        for candidate in ("eval/blind/answer_sheet.csv", "eval/blind/annotations.jsonl"):
            if (ROOT / candidate).exists():
                blind_args.append(candidate)
                note = "  (local annotation input; not a published round)"
                break
    blind = subprocess.run(
        blind_args,
        cwd=str(ROOT),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    print((blind.stdout or "").strip())
    if note:
        print(note)
    if blind.returncode != 0:
        print((blind.stderr or "")[-2000:])
        print("BLIND EVAL SCRIPT FAILED")
        return 1
    print("")

    print("== project self-checks ==")
    checks = run_checks()
    print(render_checks(checks))
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Publish one blind round: score a filled sheet and freeze the result.

The published `result.json` is not hand-written. It is produced by the same
scoring path as `scripts/blind_eval.py`, so anyone can re-run this script
against the published `answers.csv` and get a byte-identical result.

Usage:
    python scripts/publish_round.py --round 1 \
        --sheet eval/blind/rounds/round1/answers.csv \
        --out   eval/blind/rounds/round1/result.json \
        --date 2026-11-09 \
        --annotator "one independent reader"

Refuses to overwrite a different existing result without --force, so a
published number cannot be silently replaced.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(sheet: Path, round_id: int, date: str, annotator: str) -> dict:
    blind = _load("blind_eval", "scripts/blind_eval.py")
    scored = blind.run(sheet)
    if scored["status"] != "measured":
        raise SystemExit(
            "sheet produced no score (%s); refusing to publish" % scored["status"]
        )
    return {
        "round": round_id,
        "date": date,
        "annotator": annotator,
        "sheet": sheet.relative_to(ROOT).as_posix(),
        "agreement": scored["agreement"],
        "wilson95_ci": scored["wilson95_ci"],
        "scored_segments": scored["scored_segments"],
        "correct": scored["correct"],
        "annotated_cases": scored["annotated_cases"],
        "disagreement_causes": scored["disagreement_causes"],
        "disagreements": scored["disagreements"],
        "compared_with": "engine verdicts, not author-written golden labels",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--round", type=int, required=True, dest="round_id")
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--annotator", required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    sheet = (ROOT / args.sheet).resolve() if not Path(args.sheet).is_absolute() else Path(args.sheet)
    out = (ROOT / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    result = build(sheet, args.round_id, args.date, args.annotator)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    if out.exists() and not args.force:
        if out.read_text(encoding="utf-8") != text:
            print(
                "refusing to overwrite a different published result: %s\n"
                "pass --force only if the sheet really changed" % out
            )
            return 2
        print("unchanged: %s" % out)
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(
        "round %d: %d/%d segments agree (%.4f), %d disagreements"
        % (
            result["round"],
            result["correct"],
            result["scored_segments"],
            result["agreement"],
            len(result["disagreements"]),
        )
    )
    print("wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

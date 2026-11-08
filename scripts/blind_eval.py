#!/usr/bin/env python3
"""Compare an INDEPENDENT annotator's verdicts with this engine's verdicts.

The annotator sees only the answer-free blind packet: no expected labels, no
why, no structural kind, no engine output, no accuracy figures. Agreement is
therefore falsifiable -- a disagreement is a real candidate defect, not a
disagreeing golden label.

Usage:
    python scripts/blind_eval.py
    python scripts/blind_eval.py eval/blind/answer_sheet.csv
    python scripts/blind_eval.py path/to/annotations.jsonl --json

Accepts the filled-in CSV template (columns: id, segment_id, verdict,
rationale) or the JSONL format described in README.md. Undecided rows are
skipped and counted, not guessed.

If no annotation file exists, this reports that NO blind score has been
measured. It never invents a number and never falls back to the scored sets.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from release_contract.engine import (  # noqa: E402
    contract_from_dict,
    decide,
    wilson_interval,
)

PROMPTS = ROOT / "eval" / "blind" / "prompts.jsonl"
DEFAULT_ANNOTATIONS = ROOT / "eval" / "blind" / "annotations.jsonl"
VALID_VERDICTS = ("AUTO", "FENCE", "HOLD")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _pick(row: dict, *names: str) -> str:
    """Accept either the English template columns or the Chinese one-sheet."""
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _load_annotations(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() != ".csv":
        return _read_jsonl(path)
    grouped: dict[str, dict[str, str]] = {}
    # utf-8-sig also reads plain UTF-8 files, and handles the BOM that the
    # single-sheet CSV needs for Excel / WPS.
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            case_id = _pick(row, "id", "题目编号")
            seg_id = _pick(row, "segment_id", "分片名")
            verdict = _pick(row, "verdict", "你的判定").upper()
            if not case_id or not seg_id:
                raise ValueError("annotation row is missing id or segment_id")
            if not verdict:
                continue  # undecided rows are allowed and reported as such
            if verdict not in VALID_VERDICTS:
                raise ValueError(
                    "invalid verdict %r at %s/%s" % (verdict, case_id, seg_id)
                )
            grouped.setdefault(case_id, {})[seg_id] = verdict
    return [{"id": k, "verdicts": v} for k, v in grouped.items()]


def _not_run(message: str) -> dict[str, Any]:
    return {
        "status": "no_annotations",
        "agreement": None,
        "wilson95_ci": None,
        "scored_segments": 0,
        "disagreements": [],
        "message": message,
    }


def run(annotations_path: Path) -> dict[str, Any]:
    if not annotations_path.exists():
        return _not_run(
            "No blind evaluation has been run. There is no measured "
            "agreement score. Do not report one."
        )

    prompts = {p["id"]: p for p in _read_jsonl(PROMPTS)}
    annotations = _load_annotations(annotations_path)
    total_possible = sum(len(p["contract"]["segments"]) for p in prompts.values())
    total = 0
    correct = 0
    disagreements: list[dict[str, str]] = []

    for ann in annotations:
        case_id = ann["id"]
        prompt = prompts.get(case_id)
        if prompt is None:
            raise ValueError("annotation refers to unknown prompt id: %s" % case_id)
        decision = decide(contract_from_dict(prompt["contract"]))
        engine = {s.id: s.verdict for s in decision.segments}
        for seg_id, label in ann["verdicts"].items():
            got = engine.get(seg_id)
            if got is None:
                raise ValueError("unknown segment %s in %s" % (seg_id, case_id))
            if label not in VALID_VERDICTS:
                raise ValueError("invalid verdict %r at %s/%s" % (label, case_id, seg_id))
            total += 1
            if got == label:
                correct += 1
            else:
                disagreements.append(
                    {
                        "case": case_id,
                        "segment": seg_id,
                        "annotator": label,
                        "engine": got,
                    }
                )

    if total == 0:
        return _not_run(
            "Annotation file exists but contains no decided rows. No score is reported."
        )

    ci = None
    if total >= 8:
        lo, hi = wilson_interval(correct, total)
        ci = [round(lo, 4), round(hi, 4)]
    return {
        "status": "measured",
        "agreement": round(correct / total, 4),
        "wilson95_ci": ci,
        "scored_segments": total,
        "correct": correct,
        "unannotated_segments": total_possible - total,
        "disagreements": disagreements,
        "annotated_cases": len(annotations),
        "message": (
            "Agreement is between the independent annotator and the engine, "
            "NOT against the author-written golden labels."
        ),
    }


def render(result: dict[str, Any]) -> str:
    if result["status"] == "no_annotations":
        return "blind evaluation: NOT RUN\n  " + result["message"]
    lines = [
        "blind evaluation: %d annotated cases / %d scored segments"
        % (result["annotated_cases"], result["scored_segments"]),
        "  agreement   : %s" % result["agreement"],
        "  wilson95 CI : %s" % (result["wilson95_ci"] or "n<8, no interval"),
        "  unannotated : %d segments" % result["unannotated_segments"],
        "  compared with: engine verdicts, not author-written golden labels",
        "  disagreements: %d" % len(result["disagreements"]),
    ]
    for d in result["disagreements"]:
        lines.append(
            "    %s/%s annotator=%s engine=%s"
            % (d["case"], d["segment"], d["annotator"], d["engine"])
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("annotations", nargs="?", default=str(DEFAULT_ANNOTATIONS))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    result = run(Path(args.annotations))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

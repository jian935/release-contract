#!/usr/bin/env python3
"""Generate a human-readable annotation packet from the answer-free prompts.

Single source of truth: eval/blind/prompts.jsonl, which is itself generated
from the scored suites. Never hand-edit worksheet.md or
answer_sheet.template.csv -- run this script instead.

The packet deliberately contains NO answers, NO engine verdicts, NO structural
kind labels, and NO accuracy figures. Anything that lets an annotator infer
the expected answer would destroy the blind.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROMPTS = ROOT / "eval" / "blind" / "prompts.jsonl"
OUT_DIR = ROOT / "eval" / "blind"
WORKSHEET = OUT_DIR / "worksheet.md"
TEMPLATE = OUT_DIR / "answer_sheet.template.csv"


def load_prompts() -> list[dict]:
    return [
        json.loads(line)
        for line in PROMPTS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_worksheet(rows: list[dict]) -> str:
    lines = [
        "# Blind annotation worksheet",
        "",
        "Read `ANNOTATOR_GUIDE.md` before starting. Fill the empty verdict and",
        "reason columns, or use `answer_sheet.template.csv` instead.",
        "",
        "Verdicts: `AUTO` = let the model act alone on this traffic;",
        "`FENCE` = route to a human or disable automation;",
        "`HOLD` = the evidence is not enough to decide either way.",
        "",
        "Every number below is a fabricated input for a judgement exercise.",
        "Do not consult the engine, the scored eval sets, or the project README.",
        "",
    ]
    for row in rows:
        contract = row["contract"]
        gr = contract["guardrails"]
        lines.append("## %s" % row["id"])
        lines.append("")
        lines.append(
            "Guardrails: min_sample_size=%s, min_success_rate=%s, max_harm=%s, "
            "max_cost_per_case=%s"
            % (
                gr["min_sample_size"],
                gr["min_success_rate"],
                gr["max_harm"],
                gr["max_cost_per_case"],
            )
        )
        lines.append("")
        lines.append(
            "| segment | n | successes | harm_if_wrong | fallback | "
            "cost_per_case | human_review_cost | volume_share | your verdict | your reason |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for s in contract["segments"]:
            lines.append(
                "| %s | %s | %s | %s | %s | %s | %s | %s |  |  |"
                % (
                    s["id"], s["n"], s["successes"], s["harm_if_wrong"],
                    s["fallback"], s["cost_per_case"], s["human_review_cost"],
                    s["volume_share"],
                )
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def build_template(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["id", "segment_id", "verdict", "rationale"])
    for row in rows:
        for s in row["contract"]["segments"]:
            writer.writerow([row["id"], s["id"], "", ""])
    return buf.getvalue()


def build() -> tuple[str, str]:
    rows = load_prompts()
    return build_worksheet(rows), build_template(rows)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    worksheet, template = build()
    WORKSHEET.write_text(worksheet, encoding="utf-8")
    TEMPLATE.write_text(template, encoding="utf-8")
    segment_rows = sum(1 for line in template.splitlines() if line.strip()) - 1
    print("wrote %s" % WORKSHEET.relative_to(ROOT))
    print("wrote %s" % TEMPLATE.relative_to(ROOT))
    print("cases=%d segment rows=%d (verdict column left empty)" % (
        len(load_prompts()), segment_rows
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())

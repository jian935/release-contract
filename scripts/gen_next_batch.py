#!/usr/bin/env python3
"""Generate the next blind batch: cases nobody has annotated yet.

Why a new batch instead of a fourth round on the same 67 segments: three
readers have now seen those cases, and what they disagree about is no longer a
lack of data but two named rule questions. A fourth reader on the same sheet
buys one kappa point. A new sheet buys information about inputs the first batch
barely covered.

What the first batch was thin on, counted over its 67 segments:

    harm_if_wrong = medium        2   (medium is also the default ceiling)
    fallback = degrade / rollback 3   (the two fallbacks G5 does not price)
    cost_per_case > 0.5           3
    human_review_cost > 0         7
    cases with 3+ segments        3

So this batch targets those holes rather than sampling the same distribution
again. Every case carries a neutral, business-shaped segment name (`faq-bot`,
`refund-flow`) instead of a name that hints at the answer (`thin`, `almost`).

The batch is ANSWER-FREE on purpose. `covers` records which input dimension a
case was chosen for; it is a note for whoever maintains this file and is never
written to `prompts.jsonl` or the sheet. No expected verdict, no engine output
and no score appears anywhere in the output.

Single source of truth: this file. Run it, do not hand-edit the outputs.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "eval" / "blind" / "next_batch"
PROMPTS = OUT_DIR / "prompts.jsonl"
SHEET = OUT_DIR / "sheet.csv"

HARM = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}
FALLBACK = {"none": "无", "human": "人工", "degrade": "降级", "rollback": "回滚"}

# Kept identical to eval/blind/盲评填写表.csv so an annotator who has seen the
# first sheet does not have to learn a second layout. The self-check compares
# the two headers and fails on drift.
HEADER = [
    "题目编号", "分片名", "样本数", "成功数", "危害等级", "兜底方式",
    "模型单次成本", "人工兜底成本", "流量占比", "最少样本数",
    "成功率下限", "允许最高危害", "成本上限", "你的判定", "理由",
]

# Guardrail profiles. Only one field varies per profile so a case can be
# described by "which field moved" instead of by memorised numbers.
BASE = {
    "min_sample_size": 100,
    "min_success_rate": 0.9,
    "max_harm": "medium",
    "max_cost_per_case": 0.5,
    "z": 1.96,
}


def _gr(**overrides):
    profile = dict(BASE)
    profile.update(overrides)
    return profile


G_FLOOR_LOW = _gr(max_harm="low")
G_FLOOR_CRITICAL = _gr(max_harm="critical")
G_FLOOR_HIGH = _gr(max_harm="high")
G_RATE_ONE = _gr(min_success_rate=1.0)
G_RATE_LOW88 = _gr(min_success_rate=0.88)
G_WIDE_OPEN = _gr(
    # 0 is not a legal floor: the schema rejects min_sample_size < 1. 1 is the
    # loosest contract a user can actually write.
    min_sample_size=1,
    min_success_rate=0.0,
    max_harm="critical",
    max_cost_per_case=10.0,
)


def _seg(sid, n, successes, harm, fallback, cost, human_cost, volume):
    return {
        "id": sid,
        "n": n,
        "successes": successes,
        "harm_if_wrong": harm,
        "fallback": fallback,
        "cost_per_case": cost,
        "human_review_cost": human_cost,
        "volume_share": volume,
    }


# 400/380 (point 0.95, Wilson lower 0.9240) is the control rate: it clears G2
# under BASE, so any FENCE below comes from the gate the case targets.
#
# `covers` names the input dimension a case was chosen for. It must describe the
# INPUT only -- never "this passes G3" or "this is fenced". Anyone who annotates
# this batch may read this file, so a note that states the expected verdict
# would turn the blind sheet into a reading comprehension test.
CASES = [
    # --- harm ceiling
    {"id": "nb-01", "covers": "harm equals a medium ceiling",
     "guardrails": BASE,
     "segments": [_seg("faq-bot", 400, 380, "medium", "none", 0.02, 0.0, 1.0)]},
    {"id": "nb-02", "covers": "harm equals a low ceiling",
     "guardrails": G_FLOOR_LOW,
     "segments": [_seg("faq-bot", 400, 380, "low", "none", 0.02, 0.0, 1.0)]},
    {"id": "nb-03", "covers": "harm one rank above a medium ceiling",
     "guardrails": BASE,
     "segments": [_seg("refund-flow", 400, 380, "high", "human", 0.02, 0.0, 1.0)]},
    {"id": "nb-04", "covers": "harm two ranks above a medium ceiling",
     "guardrails": BASE,
     "segments": [_seg("claims-triage", 500, 480, "critical", "human", 0.02, 0.0, 1.0)]},
    {"id": "nb-05", "covers": "harm equals a critical ceiling",
     "guardrails": G_FLOOR_CRITICAL,
     "segments": [_seg("claims-triage", 500, 485, "critical", "human", 0.02, 0.0, 1.0)]},
    {"id": "nb-06", "covers": "harm equals a high ceiling, fallback absent",
     "guardrails": G_FLOOR_HIGH,
     "segments": [_seg("invoice-parse", 400, 380, "high", "none", 0.02, 0.0, 1.0)]},

    # --- fallback kind and what it costs
    {"id": "nb-07", "covers": "degrade with a non-zero review cost",
     "guardrails": G_FLOOR_HIGH,
     "segments": [_seg("billing-recon", 400, 380, "high", "degrade", 0.02, 0.6, 1.0)]},
    {"id": "nb-08", "covers": "rollback with a non-zero review cost",
     "guardrails": G_FLOOR_HIGH,
     "segments": [_seg("orders-sync", 400, 380, "high", "rollback", 0.02, 0.6, 1.0)]},
    {"id": "nb-09", "covers": "human with the same non-zero review cost",
     "guardrails": G_FLOOR_HIGH,
     "segments": [_seg("invoice-parse", 400, 380, "high", "human", 0.02, 0.6, 1.0)]},
    {"id": "nb-10", "covers": "human with zero review cost",
     "guardrails": G_FLOOR_HIGH,
     "segments": [_seg("invoice-parse", 400, 380, "high", "human", 0.02, 0.0, 1.0)]},
    {"id": "nb-11", "covers": "critical harm with degrade instead of human",
     "guardrails": G_FLOOR_CRITICAL,
     "segments": [_seg("claims-triage", 500, 485, "critical", "degrade", 0.02, 0.0, 1.0)]},
    {"id": "nb-12", "covers": "medium harm carrying a human fallback",
     "guardrails": BASE,
     "segments": [_seg("ticket-router", 400, 380, "medium", "human", 0.02, 0.02, 1.0)]},

    # --- sample size around the floor
    {"id": "nb-13", "covers": "n one below the sample floor",
     "guardrails": BASE,
     "segments": [_seg("faq-bot", 99, 98, "low", "none", 0.02, 0.0, 1.0)]},
    {"id": "nb-14", "covers": "n exactly at the sample floor",
     "guardrails": BASE,
     "segments": [_seg("faq-bot", 100, 98, "low", "none", 0.02, 0.0, 1.0)]},
    {"id": "nb-15", "covers": "n one above the sample floor",
     "guardrails": BASE,
     "segments": [_seg("faq-bot", 101, 99, "low", "none", 0.02, 0.0, 1.0)]},
    {"id": "nb-16", "covers": "n is zero",
     "guardrails": BASE,
     "segments": [_seg("new-flow", 0, 0, "low", "none", 0.02, 0.0, 1.0)]},

    # --- rate and floor
    {"id": "nb-17", "covers": "200 cases, 190 successes, floor 0.9",
     "guardrails": BASE,
     "segments": [_seg("faq-bot", 200, 190, "low", "none", 0.02, 0.0, 1.0)]},
    {"id": "nb-18", "covers": "100 cases, 95 successes, floor 0.9",
     "guardrails": BASE,
     "segments": [_seg("faq-bot", 100, 95, "low", "none", 0.02, 0.0, 1.0)]},
    {"id": "nb-19", "covers": "100 cases, 95 successes, floor 0.88",
     "guardrails": G_RATE_LOW88,
     "segments": [_seg("faq-bot", 100, 95, "low", "none", 0.02, 0.0, 1.0)]},
    {"id": "nb-20", "covers": "floor 1.0 with a perfect 500/500 record",
     "guardrails": G_RATE_ONE,
     "segments": [_seg("faq-bot", 500, 500, "low", "none", 0.02, 0.0, 1.0)]},
    {"id": "nb-21", "covers": "zero successes out of 500",
     "guardrails": BASE,
     "segments": [_seg("spam-filter", 500, 0, "low", "none", 0.02, 0.0, 1.0)]},

    # --- volume, multi-segment contracts and undeclared traffic
    {"id": "nb-22", "covers": "three segments summing to 1.0, the last at n=50",
     "guardrails": BASE,
     "segments": [
         _seg("faq-bot", 400, 380, "low", "none", 0.02, 0.0, 0.40),
         _seg("refund-flow", 400, 380, "low", "none", 0.02, 0.0, 0.35),
         _seg("voice-bot", 50, 50, "low", "none", 0.02, 0.0, 0.25),
     ]},
    {"id": "nb-23", "covers": "declared volume sums to 0.999",
     "guardrails": BASE,
     "segments": [
         _seg("faq-bot", 400, 380, "low", "none", 0.02, 0.0, 0.500),
         _seg("refund-flow", 400, 380, "low", "none", 0.02, 0.0, 0.499),
     ]},
    {"id": "nb-24", "covers": "two segments at 300/400 and 380/400",
     "guardrails": BASE,
     "segments": [
         _seg("faq-bot", 400, 380, "low", "none", 0.02, 0.0, 0.6),
         _seg("refund-flow", 400, 300, "low", "none", 0.02, 0.0, 0.4),
     ]},
    {"id": "nb-25", "covers": "four healthy segments summing to exactly 1.0",
     "guardrails": BASE,
     "segments": [
         _seg("faq-bot", 400, 380, "low", "none", 0.02, 0.0, 0.3),
         _seg("refund-flow", 300, 285, "low", "none", 0.02, 0.0, 0.3),
         _seg("order-status", 500, 480, "low", "none", 0.02, 0.0, 0.2),
         _seg("ticket-router", 200, 190, "low", "none", 0.02, 0.0, 0.2),
     ]},
    {"id": "nb-26", "covers": "5% of traffic undeclared, both segments healthy",
     "guardrails": BASE,
     "segments": [
         _seg("faq-bot", 400, 380, "low", "none", 0.02, 0.0, 0.60),
         _seg("refund-flow", 400, 380, "low", "none", 0.02, 0.0, 0.35),
     ]},

    # --- cost around the cap
    {"id": "nb-27", "covers": "cost_per_case exactly at the cap",
     "guardrails": BASE,
     "segments": [_seg("faq-bot", 400, 380, "low", "none", 0.50, 0.0, 1.0)]},
    {"id": "nb-28", "covers": "cost_per_case one ten-thousandth above the cap",
     "guardrails": BASE,
     "segments": [_seg("faq-bot", 400, 380, "low", "none", 0.5001, 0.0, 1.0)]},
    {"id": "nb-29", "covers": "every threshold loosened to its legal minimum",
     "guardrails": G_WIDE_OPEN,
     "segments": [_seg("sandbox-bot", 20, 10, "low", "none", 0.02, 0.0, 1.0)]},
    {"id": "nb-30", "covers": "critical harm at a critical ceiling, fallback absent",
     "guardrails": G_FLOOR_CRITICAL,
     "segments": [_seg("claims-triage", 500, 485, "critical", "none", 0.02, 0.0, 1.0)]},
]


def build_prompts() -> str:
    rows = []
    for case in CASES:
        rows.append(
            {
                "id": case["id"],
                "suite": "next",
                "contract": {
                    "product": "blind-evaluation-case",
                    "guardrails": case["guardrails"],
                    "segments": [dict(s) for s in case["segments"]],
                },
            }
        )
    return "\n".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows
    ) + "\n"


def build_sheet() -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(HEADER)
    for case in CASES:
        gr = case["guardrails"]
        for s in case["segments"]:
            writer.writerow(
                [
                    case["id"],
                    s["id"],
                    s["n"],
                    s["successes"],
                    HARM[s["harm_if_wrong"]],
                    FALLBACK[s["fallback"]],
                    s["cost_per_case"],
                    s["human_review_cost"],
                    s["volume_share"],
                    gr["min_sample_size"],
                    gr["min_success_rate"],
                    HARM[gr["max_harm"]],
                    gr["max_cost_per_case"],
                    "",
                    "",
                ]
            )
    # utf-8-sig so Excel and WPS show the Chinese header row instead of mojibake.
    return buf.getvalue()


def segment_count() -> int:
    return sum(len(c["segments"]) for c in CASES)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS.write_text(build_prompts(), encoding="utf-8", newline="\n")
    SHEET.write_bytes(build_sheet().encode("utf-8-sig"))
    print("wrote %s (%d cases)" % (PROMPTS.relative_to(ROOT), len(CASES)))
    print("wrote %s (%d segment rows, verdict column empty)" % (
        SHEET.relative_to(ROOT), segment_count()
    ))
    print("no expected verdict, no engine output, no score is written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Generate ONE self-contained CSV that an annotator can fill and return.

This is the only file to hand out. It carries the case id, every input field
needed to make the judgement, and two empty answer columns. It contains no
answers, no engine verdicts, no structural labels and no accuracy figures.

Written as UTF-8 with BOM so Excel / WPS shows Chinese column names correctly.
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
OUT = ROOT / "eval" / "blind" / "盲评填写表.csv"

HARM = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}
FALLBACK = {"none": "无", "human": "人工", "degrade": "降级", "rollback": "回滚"}

HEADER = [
    "题目编号", "分片名", "样本数", "成功数", "危害等级", "兜底方式",
    "模型单次成本", "人工兜底成本", "流量占比", "最少样本数",
    "成功率下限", "允许最高危害", "成本上限", "你的判定", "理由",
]


def build() -> str:
    rows = [
        json.loads(line)
        for line in PROMPTS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(HEADER)
    for row in rows:
        contract = row["contract"]
        gr = contract["guardrails"]
        for s in contract["segments"]:
            writer.writerow(
                [
                    row["id"], s["id"], s["n"], s["successes"],
                    HARM[s["harm_if_wrong"]], FALLBACK[s["fallback"]],
                    s["cost_per_case"], s["human_review_cost"], s["volume_share"],
                    gr["min_sample_size"], gr["min_success_rate"],
                    HARM[gr["max_harm"]], gr["max_cost_per_case"], "", "",
                ]
            )
    return buf.getvalue()


def main() -> int:
    text = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8-sig")
    row_count = sum(1 for line in text.splitlines() if line.strip()) - 1
    print("wrote %s" % OUT.relative_to(ROOT))
    print("cases with segments: %d rows; answer columns left empty" % row_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())

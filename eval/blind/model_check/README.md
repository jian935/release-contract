# Model cross-check — not a blind round

| field | value |
|---|---|
| date | 2026-11-09 |
| kind | **model cross-check, not a human blind round** |
| cases / segments | 30 / 38 (every segment answered) |
| answered by | a second language model (Doubao), working in a chat window; returned as a filled CSV and pasted back by the project owner, not reviewed by a human |
| prompt set | `../next_batch/prompts.jsonl` — the second 38-segment batch |
| agreement with engine | **0.8947** (34 / 38) |
| Wilson 95% interval | **[0.7587, 0.9583]** |
| disagreements | 4, all `FENCE` by the model against `AUTO` from the engine |

Reproduce:

```
python scripts/publish_round.py --round 4 --kind model_check \
  --prompts eval/blind/next_batch/prompts.jsonl \
  --sheet eval/blind/model_check/answers.csv \
  --out   eval/blind/model_check/result.json \
  --date  2026-11-09 --annotator "<as declared>" --force
```

## Why this sits outside `rounds/`

`rounds/` holds human readers. The exercise exists to test whether the rules
match a **person's** release judgement; a model answering the same questions
tests whether another model's reading of the rules matches them. That is worth
knowing, but it is a different question, and putting the two in one series would
let a model's answers be counted as human evidence.

So this number is **not** in the 0.8507 / 0.9403 / 0.7910 series, it produces no
kappa against those readers, and it does **not** add a fourth vote to
"2 of 3 readers disagree with the engine". `result.json` records
`"kind": "model_check"` so a later reader of the repository cannot mistake it for
a round.

## What it found, and how much that is worth

The four disagreements are the same design choice the new cases were built to
expose:

| case | input | model | engine |
|---|---|---|---|
| `nb-01` | medium harm, `fallback=none`, medium ceiling | FENCE | AUTO |
| `nb-07` | high harm, `fallback=degrade`, review cost 0.6 | FENCE | AUTO |
| `nb-08` | high harm, `fallback=rollback`, review cost 0.6 | FENCE | AUTO |
| `nb-11` | critical harm, `fallback=degrade` | FENCE | AUTO |

- **G4's floor.** It fires from `high` up; the model requires a human fallback
  from `medium` up.
- **What counts as a fallback.** G4 fires only on `none`, so `degrade` and
  `rollback` count as contained damage; the model accepts neither. Related: G5
  loads `human_review_cost` only for `fallback=human`, so a degrade segment
  carrying a 0.6 review cost is priced at 0.02 against a 0.5 cap.

Priced, not adopted: the floor change flips 0 of the 67 segments in rounds 1–3
and 1 here; counting degrade/rollback as no fallback flips 1 (`ho-010`) and 3
here. Adopting both would make this sheet agree 38/38 — a rule tuned until it
matches whoever answered it.

**The 34 agreements are not evidence the rules are right.** Read the model's own
rationales: on `nb-18` it wrote "95% lower bound 88.8%", on `nb-20` it computed
"99.2%". It is doing the arithmetic the rule describes, question by question. A
human annotator reasons about whether a release is defensible; a model given the
thresholds tends to compute them. That is why its rate is high, and why it cannot
stand in for a reader — the thing being measured (does the rule match human
judgement) is not what this measured (does another model reproduce the rule).

Where it dissents, it dissents on **semantics** — what "fallback" and "contained"
mean — not on arithmetic. That is the same axis the human readers dissented on,
which makes the four cases a finding about the rule design rather than about the
model.

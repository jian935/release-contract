# Blind round 4 — published record (second batch)

| field | value |
|---|---|
| date | 2026-11-09 |
| cases / segments scored | 30 / 38 (every segment decided, none left blank) |
| annotator | a **fourth** independent reader, declared no exposure to `eval/blind/rounds/` or the engine output |
| input | `answers.csv` (this folder), the blank sheet from `../../next_batch/` |
| prompt set | `eval/blind/next_batch/prompts.jsonl` — **not** the 67 segments of rounds 1–3 |
| agreement with engine | **0.8947** (34 / 38) |
| Wilson 95% interval | **[0.7587, 0.9583]** |
| disagreements | 4, all `FENCE` by the reader against `AUTO` from the engine |
| compared against | engine verdicts, **not** the author-written golden labels |

Reproduce:

```
python scripts/publish_round.py --round 4 \
  --prompts eval/blind/next_batch/prompts.jsonl \
  --sheet eval/blind/rounds/round4/answers.csv \
  --out   eval/blind/rounds/round4/result.json \
  --date  2026-11-09 --annotator "<as declared>"
```

The `--prompts` flag is required. Without it the script reads the first batch,
rejects every `nb-*` row as an unknown case id, and refuses to publish. The
`prompts` field in `result.json` is what lets the self-check recompute this
round later against the right question set.

## This number is not comparable to 0.8507 / 0.9403 / 0.7910

Those three are three readers on the **same 67 fabricated segments**. This is one
reader on **30 different cases**. The cases were selected for coverage gaps, not
sampled, so the rate cannot be subtracted from the earlier ones, averaged with
them, or read as a trend. It answers a different question: do these new inputs
surface a rule question the first batch could not.

## What the new cases found: a third rule question

| case | input | reader | engine | why they differ |
|---|---|---|---|---|
| `nb-01` | medium harm, `fallback=none`, medium ceiling | FENCE | AUTO | reader: a medium-harm segment still needs a human fallback |
| `nb-07` | high harm, `fallback=degrade`, review cost 0.6 | FENCE | AUTO | reader: degrade is not a fallback, and 0.02+0.6 breaches the cap |
| `nb-08` | high harm, `fallback=rollback`, review cost 0.6 | FENCE | AUTO | same as `nb-07` |
| `nb-11` | critical harm, `fallback=degrade`, no review cost | FENCE | AUTO | reader: degrade is not a fallback |

All four are one design choice seen from two sides: **what counts as a fallback,
and from which harm rank G4 requires one.**

- **G4's floor.** It fires only at `high` and above. The reader requires a human
  fallback from `medium` up. `nb-01` is the only case in either batch where that
  difference is visible, because a medium-harm segment with no fallback is the
  only input that separates the two readings.
- **What "fallback" means.** G4 only fires on `none`, so `degrade` and `rollback`
  count as contained damage. The reader does not accept either. Related, and
  visible in `nb-07` / `nb-08`: G5 loads `human_review_cost` only for
  `fallback=human`, so a degrade/rollback segment with a 0.6 review cost is
  priced at 0.02 against a 0.5 cap. The reader priced it at 0.62.

The reader is internally consistent: `nb-12` is medium harm **with** a human
fallback and they answered `AUTO`, the same as the engine. They are not
misreading the numbers; they disagree with the rule.

## What adopting either reading would cost

Both changes were simulated over the published segments rather than argued about:

| change | flips in rounds 1–3 (67 segs) | flips in this batch (38 segs) |
|---|---|---|
| G4 floor from `high` down to `medium` | 0 | 1 (`nb-01`) |
| `degrade` / `rollback` count as no fallback | 1 (`ho-010/at_ceiling`) | 3 (`nb-07`, `nb-08`, `nb-11`) |

**Neither is implemented, and this is the reason:** adopting both would turn this
round into 38/38, an agreement of exactly 1.0000. A rule that is tuned until it
agrees with the one person who annotated it measures nothing — it would have
been "validated" by construction. The disagreement stays on the record, priced,
and undecided. See `DESIGN.md`, open question 3.

What would settle it is not another reader on the same sheet: it is a launch
where degrade/rollback segments show a realised harm rate materially different
from their declared `harm_if_wrong`. The repository has no such launch data.

## Admission honesty

The annotator's declaration is taken at their word. The self-check can recompute
every number in this folder from `answers.csv`, but it cannot verify that the
reader never opened `rounds/`. A contaminated round still looks like data — which
is why the declaration is written down instead of assumed.

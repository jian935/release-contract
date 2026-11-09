# Blind round 3 — published record

| field | value |
|---|---|
| date | 2026-11-09 |
| cases / segments scored | 50 / 67 (every segment decided, none left blank) |
| annotator | a **third** independent reader; declared no prior exposure to this repository, its engine output, or any published round |
| input | `answers.csv` (this folder), same answer-free sheet as rounds 1 and 2 |
| agreement with engine | **0.7910** (53 / 67) |
| Wilson 95% interval | **[0.6793, 0.8712]** |
| disagreements | 14 (10 Wilson-class + 4 rule-class, see below) |
| compared against | engine verdicts, **not** the author-written golden labels |

Reproduce:

```
python scripts/publish_round.py --round 3 \
  --sheet eval/blind/rounds/round3/answers.csv \
  --out   eval/blind/rounds/round3/result.json \
  --date 2026-11-09 --annotator "<as declared>"
```

## The result that matters: the disagreements decompose exactly

Across all three rounds, **every single disagreement falls into one of two rule
choices, with zero residual**. Nothing is unexplained.

| round | agreement | disagreements | Wilson-class | rule-class | unexplained |
|---|---|---|---|---|---|
| 1 | 0.8507 | 10 | 10 | 0 | **0** |
| 2 | 0.9403 | 4 | 0 | 4 | **0** |
| 3 | 0.7910 | 14 | 10 | 4 | **0** |

The two rule classes are:

- **Wilson-class** (`wilson_lower_below_floor_but_point_estimate_above`, labelled
  by `scripts/blind_eval.py`): the observed rate clears the floor, the Wilson
  lower bound does not, and no other gate is violated. Ten cases:
  `dev-004`, `dev-005`, `dev-006`, `dev-007`, `dev-016`, `ho-004`, `ho-005`,
  `ho-006`, `ho-007`, `ho-022`.
- **Rule-class** (`other_gate_or_judgement`): four cases, each one of the two open
  questions in `DESIGN.md` — `dev-008` and `dev-009` (does a human fallback
  relax the harm ceiling?) and `dev-020`, `ho-020` (should thin evidence plus a
  hard violation read `HOLD` or `FENCE`?).

Because the three rates are exactly `1 - 10/67`, `1 - 4/67` and `1 - 14/67`, the
numbers are not three independent scores. They are the same engine measured
against readers who each take a different side on two binary rule questions:

| reader | success floor applied to | fallback relaxes ceiling? | thin + hard violation | disagreements | agreement |
|---|---|---|---|---|---|
| 1 | point estimate | no | `HOLD` | 10 | 0.8507 |
| 2 | Wilson lower bound | yes | `FENCE` | 4 | 0.9403 |
| 3 | point estimate | yes | `FENCE` | 14 | 0.7910 |
| **engine** | **Wilson lower bound** | **no** | **`HOLD`** | — | — |

Read that table as the actual finding: the engine is not noisy, and none of the
readers produced scattered errors. Every reader differs from the engine on a
subset of two named rules, and each reader's score is fully predicted by which
side of each rule they take. This reader (3) is the mirror image of reader 1:
identical on the Wilson axis, opposite on the rule axis.

## Pairwise agreement

| pair | raw agreement | Cohen's kappa |
|---|---|---|
| round 1 vs round 2 | 0.7910 | 0.6554 |
| round 1 vs round 3 | 0.9403 | **0.8929** |
| round 2 vs round 3 | 0.8507 | 0.7498 |

Readers 1 and 3 agree on 63 of 67 segments and differ **only** on the four
rule-class cases, which is what their shared point-estimate reading predicts.
All three kappas sit in 0.65–0.89: the label task carries real shared signal,
and the spread between the three rates is reader variance, not engine variance.

```
python scripts/compare_rounds.py \
  eval/blind/rounds/round1/answers.csv \
  eval/blind/rounds/round3/answers.csv
```

## What this still does not establish

- **Three readers is still not a sample of readers.** Kappa from three people is
  a band, not a distribution, and it has no interval.
- **Two of the three readers dissent from the engine on both rule questions.**
  That is a finding about the rules, not a defect report — but it is now 2-of-3
  rather than one person's opinion, and it is recorded in `DESIGN.md` as a
  decision waiting on the owner of the tool, with the measured cost of changing
  (`scripts/whatif_rules.py`: 3 segments for the ceiling question, 2 for the
  precedence question).
- **Synthetic cases only.** All 50 contracts are fabricated; this measures rule
  interpretation, not production behaviour.
- **Same 67 questions.** Agreement on a fixed set says nothing about segments
  nobody thought to include. A fourth reader on these cases would add little; the
  next round should use cases nobody has seen.

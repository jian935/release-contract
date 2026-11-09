# Blind round 4 — published record (second case set, human reader)

| field | value |
|---|---|
| date | 2026-11-09 |
| cases / segments scored | 30 / 38 (every segment decided, none left blank) |
| annotator | a **fourth human reader**, independent of the first three; declared no exposure to `rounds/` or `model_check/` |
| input | `answers.csv` (this folder), the blank sheet from `../../next_batch/` |
| prompt set | `eval/blind/next_batch/prompts.jsonl` — **not** the 67 segments of rounds 1–3 |
| agreement with engine | **0.8158** (31 / 38) |
| Wilson 95% interval | **[0.6658, 0.9078]** |
| disagreements | 7 = 2 Wilson-class + 5 rule-class |
| compared against | engine verdicts, **not** the author-written golden labels |

Reproduce:

```
python scripts/publish_round.py --round 4 \
  --prompts eval/blind/next_batch/prompts.jsonl \
  --sheet eval/blind/rounds/round4/answers.csv \
  --out   eval/blind/rounds/round4/result.json \
  --date  2026-11-09 --annotator "<as declared>"
```

## Not comparable to 0.8507 / 0.9403 / 0.7910

Those three are three readers on the same 67 fabricated segments. This is a
fourth reader on **30 different cases**, selected for coverage rather than
sampled. The rate cannot be subtracted from theirs, averaged with them, or read
as a trend, and it adds no fourth kappa point — different cases give no pairwise
agreement with rounds 1–3.

## The seven disagreements, grouped

| cases | reader | engine | group |
|---|---|---|---|
| `nb-03`, `nb-04` | AUTO | FENCE | **Q1** — does a human fallback relax the harm ceiling? |
| `nb-07`, `nb-11` | FENCE | AUTO | **Q3** — is `degrade` a fallback at all? |
| `nb-08` | FENCE | AUTO | **Q3**, cost side — 0.02 + 0.6 breaches the 0.5 cap, which G5 does not see for `rollback` |
| `nb-18` | AUTO | FENCE | Wilson-class — the reader used the **point estimate** (95% against a 90% floor) |
| `nb-20` | HOLD | FENCE | a floor of 1.0 is unreachable; the reader parked it instead of fencing it |

Two things worth recording:

- **Q1 reproduced on a different case set, by a different person.** `nb-03` and
  `nb-04` are high and critical harm against a `medium` ceiling, both with a
  human fallback. The reader released both and said why in their own words:
  "好在这条全程有人工复核，真出事人拦得住" and "每条都过人工，模型只负责提词".
  Rounds 2 and 3 said the same on the first case set; this is independent
  confirmation that the question is real and not an artefact of those 67 cases.
- **`nb-20` is not really a Wilson disagreement.** The reader's reason is not the
  arithmetic: "500 次全对也证不出「以后永不错」，这线本身不现实" — they answered
  `HOLD` because a 1.0 floor makes the question undecidable, not because the
  segment looked unsafe. It lands in the Wilson bucket by construction (the
  lower bound can never reach 1.0), but the position is closer to open question 2
  (`HOLD` versus `FENCE` when the evidence cannot settle it).

## What this says next to the model cross-check

The same sheet was answered by a language model at 0.8947 and by this reader at
0.8158. The difference is not noise, and it is not that the model is "better at
the rules":

| | model | this reader |
|---|---|---|
| Q3 (`nb-07`, `nb-08`, `nb-11`) | dissents | dissents, identically |
| G4 floor (`nb-01`) | dissents (wants a fallback from medium up) | agrees with the engine |
| Q1 (`nb-03`, `nb-04`) | agrees with the engine | dissents |
| Wilson (`nb-18`) | agrees with the engine | dissents |
| undecidable floor (`nb-20`) | agrees with the engine | dissents |

The model reproduces the rule, so it never asks whether a human is standing
behind the segment. The reader asks exactly that, and departs from the rule
where the rule ignores it. A higher agreement rate from the model is therefore
evidence about the model's obedience, not about the rule's quality — which is
why the two are kept in separate folders and are never averaged.

## Admission honesty

The declaration is taken at their word, as in every round. The self-check
recomputes every number here from `answers.csv`; it cannot verify what the reader
read beforehand.

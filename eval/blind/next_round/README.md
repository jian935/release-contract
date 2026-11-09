# Next round packet (ready to hand out)

Rounds 1 and 2 are published. This folder holds the blank sheet for the **next**
reader: 67 segments from the same 50 cases, all judgement columns empty.

Same cases on purpose — that is what makes inter-annotator agreement computable.
A third reader on new cases would add breadth; a third reader on these cases adds
a third kappa point.

## Admission rules (read before opening the sheet)

You qualify only if **all** of these are true:

- You have not read anything under `eval/blind/rounds/`.
- You have not read the results section of the project README or of `SKILL.md`.
- You have not run this repository's CLI on these cases.
- You have not discussed these cases with someone who has.

Why so strict: both previous rounds' answers are published. Anyone who has seen
one can reproduce its rate without reading a single number in `sheet.csv`, and
the measurement becomes theatre. If any rule above does not hold, say so and
stop — a contaminated round is worse than no round, because it still looks like
data.

If you want to know *why* the rules exist without seeing answers, read
`../README.md` (the protocol) and `../ANNOTATOR_GUIDE.md` (the task). Both are
answer-free.

## What to do

1. Open `sheet.csv` in Excel / WPS (UTF-8 BOM, Chinese headers, no mojibake).
2. For each row, read the counts and the contract thresholds, then fill
   `你的判定` with one of:
   - `AUTO` — let the model act alone on this traffic segment
   - `FENCE` — route to a human or disable automation
   - `HOLD` — the evidence is not enough to decide either way
3. `理由` is optional; one short sentence is enough. Blank rows are skipped by
   the scoring script, never guessed.
4. Send the filled CSV back as-is. Do not rename the columns.

Do not try to match the tool. Disagreement is the useful output: a segment you
would fence that the tool releases is the finding this exercise exists for.

## How the coordinator publishes it

```bash
# 1. score the returned file without publishing
python scripts/blind_eval.py path/to/returned.csv

# 2. freeze it as the next round, with an honest annotator declaration
python scripts/publish_round.py --round 3 \
  --sheet eval/blind/rounds/round3/answers.csv \
  --out   eval/blind/rounds/round3/result.json \
  --date  YYYY-MM-DD \
  --annotator "third reader; declared not to have seen any published round"
```

The declaration must state what the annotator had and had not seen. The
self-check cannot verify that — only honesty will: it recomputes every published
rate from its sheet and fails on drift, but it cannot tell you whether the
reader was blind.

Then compare across rounds:

```bash
python scripts/compare_rounds.py \
  eval/blind/rounds/round1/answers.csv \
  eval/blind/rounds/round2/answers.csv
```

It reports paired segments, raw agreement, **Cohen's kappa** and each reader's
agreement with the engine on the same subset. With three readers, run it pairwise
and compare kappas: if they stay in the same band, the label task has a shared
meaning; if one reader's kappa collapses, that reader and the rest are answering
different questions.

## What another round can and cannot settle

- **Can:** whether the two published disagreement patterns are properties of the
  tool or habits of two people. Round 2 already moved the contested point from
  gate G2 to rule precedence, which is why the open questions in `DESIGN.md` are
  the ones worth a third reader's attention.
- **Cannot:** whether the gates match real launch outcomes. Only real launch
  data answers that, and this repository has none.

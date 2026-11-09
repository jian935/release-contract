# Next round packet

Rounds 1, 2 and 3 are published, all on the same 67 segments. This folder still
holds a blank sheet for those cases, because a fourth reader is cheap and gives
one more kappa point.

**But the same-case well is nearly dry.** Three readers already pin the two rule
questions at 2 to 1, and every disagreement in 37 has been accounted for. A
fourth reader on these exact cases adds a band point and very little
information. The next round worth running is **new cases nobody has seen** —
that is the only thing that can reveal a rule question the current 50 cases do
not contain. That packet now exists: see `../next_batch/`, which carries new
cases and its own blank sheet. Do not re-use this sheet for a fourth round.

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
python scripts/publish_round.py --round 4 \
  --sheet eval/blind/rounds/round4/answers.csv \
  --out   eval/blind/rounds/round4/result.json \
  --date  YYYY-MM-DD \
  --annotator "fourth reader; declared not to have seen any published round"
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

- **Can:** on new cases, whether there is a *third* rule question hiding behind
  the two already documented. On these cases, only a fourth kappa point.
- **Cannot:** whether the gates match real launch outcomes. Only real launch
  data answers that, and this repository has none.

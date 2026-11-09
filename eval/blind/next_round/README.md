# Round 2 packet (ready to hand out)

`sheet.csv` is an empty copy of the answer-free sheet: 67 segments from the
same 50 cases as round 1, all judgement columns blank. Same cases on purpose —
that is what makes inter-annotator agreement computable, which round 1 lacks.

## Admission rules (read before opening the sheet)

You qualify for round 2 only if **all** of these are true:

- You have not read `eval/blind/rounds/round1/answers.csv`.
- You have not read `eval/blind/rounds/round1/result.json` or its `README.md`.
- You have not read the results section of the project README.
- You have not run this repository's CLI on these cases.

Why so strict: round 1's answers are published. Anyone who has seen them can
reproduce 0.8507 without reading a single number in `sheet.csv`, and the
measurement becomes theatre. If any rule above does not hold, say so and stop —
a contaminated round is worse than no round, because it still looks like data.

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

# 2. freeze it as round 2, with an honest annotator declaration
python scripts/publish_round.py --round 2 \
  --sheet eval/blind/rounds/round2/answers.csv \
  --out   eval/blind/rounds/round2/result.json \
  --date  YYYY-MM-DD \
  --annotator "second reader; declared not to have seen round 1"
```

The declaration must state what the annotator had and had not seen. If they had
seen round 1, publish it as `round 2 (not independent)` or do not publish it —
the self-check will not catch that for you, only honesty will.

Once `rounds/round2/answers.csv` and `result.json` exist, the project
self-check recomputes the rate from the sheet and fails on drift, exactly as it
does for round 1.

Then measure whether the two readers share a rule or just a habit:

```bash
python scripts/compare_rounds.py \
  eval/blind/rounds/round1/answers.csv \
  eval/blind/rounds/round2/answers.csv
```

It reports paired segments, raw agreement, **Cohen's kappa** and each reader's
agreement with the engine on the same subset. If kappa is near zero, the two
readers disagree more than chance allows on this label set, and the engine
comparison stops being informative — that is a finding, not a failure to hide.


## What round 2 can and cannot settle

- **Can:** whether round 1's disagreement pattern is one reader's habit or a
  reading most people share. If a second independent reader disagrees on the
  same Wilson cases, the conservative bias is a property of the tool, not of
  one annotator.
- **Cannot:** whether the gates match real launch outcomes. Only real launch
  data answers that, and this repository has none.

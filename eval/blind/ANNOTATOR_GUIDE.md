# Annotator guide (read this first)

You are helping check whether a set of release rules matches human product
judgement. This is a **blind** exercise: you see only the inputs.

## What you are given

- `worksheet.md` — contract cases. Each case has guardrails and one or more
  traffic segments described by raw eval counts.
- `answer_sheet.template.csv` — one row per segment, with empty `verdict` and
  `rationale` columns. Copy it to `answer_sheet.csv` before filling it in.

All numbers are fabricated for this exercise. They are not real product data.

## The question

For each segment, answer one question:

> Given this offline evidence and this contract, would you let the model act
> alone on this traffic segment?

- `AUTO` — yes, release automated handling for this segment.
- `FENCE` — no, route it to a human or disable automation.
- `HOLD` — the evidence is not enough to decide either way yet.

Write a short reason in your own words. An ambiguous case is useful: mark what
you would actually do and say what made it hard.

## What NOT to look at

- Do not run this repository's CLI or read its engine output for these cases.
- Do not open the scored eval sets or any answer key.
- Do not read the project README's results section.
- Do not ask the rule author which answer is expected.

The value of this exercise is in **disagreement**. If you think a segment
should be fenced and the tool says otherwise, that is a finding, not a mistake
on your part. Do not try to make your answers look consistent with the tool.

## How to return it

Fill `verdict` (one of `AUTO` / `FENCE` / `HOLD`) and `rationale` for every row
in your copy of the CSV, then send the CSV back. Partial answers are fine --
leave undecided rows blank rather than guessing.

The comparison script reports agreement, a Wilson interval when the sample
permits, and a full list of disagreements. It prints `NOT RUN` and invents no
number when no annotations have been returned yet.

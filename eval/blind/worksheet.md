# Blind annotation worksheet

Read `ANNOTATOR_GUIDE.md` before starting. Fill the empty verdict and
reason columns, or use `answer_sheet.template.csv` instead.

Verdicts: `AUTO` = let the model act alone on this traffic;
`FENCE` = route to a human or disable automation;
`HOLD` = the evidence is not enough to decide either way.

Every number below is a fabricated input for a judgement exercise.
Do not consult the engine, the scored eval sets, or the project README.

## dev-001

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| thin | 40 | 39 | low | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-002

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| almost | 99 | 98 | low | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-003

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| at_min | 100 | 98 | low | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-004

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| point_ok | 100 | 95 | low | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-005

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| at_threshold | 400 | 360 | low | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-006

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| large_but_weak | 1000 | 900 | low | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-007

Guardrails: min_sample_size=100, min_success_rate=0.95, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| small_sample | 400 | 388 | low | none | 0.02 | 0.0 | 0.5 |  |  |
| large_sample | 1000 | 970 | low | none | 0.02 | 0.0 | 0.5 |  |  |

## dev-008

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| high_harm | 300 | 297 | high | human | 0.02 | 0.1 | 1.0 |  |  |

## dev-009

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| critical_harm | 300 | 297 | critical | human | 0.02 | 0.1 | 1.0 |  |  |

## dev-010

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=low, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| medium_harm | 250 | 240 | medium | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-011

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| no_containment | 250 | 240 | high | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-012

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| critical_no_fallback | 250 | 240 | critical | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-013

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| hidden_human_cost | 250 | 240 | low | human | 0.05 | 0.8 | 1.0 |  |  |

## dev-014

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| affordable_human | 250 | 240 | low | human | 0.1 | 0.2 | 1.0 |  |  |

## dev-015

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| declared_a | 250 | 240 | low | none | 0.02 | 0.0 | 0.4 |  |  |
| declared_b | 500 | 480 | low | none | 0.03 | 0.0 | 0.3 |  |  |

## dev-016

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| auto_part | 250 | 240 | low | none | 0.02 | 0.0 | 0.55 |  |  |
| fenced_part | 100 | 95 | low | none | 0.02 | 0.0 | 0.2 |  |  |

## dev-017

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| healthy | 250 | 240 | low | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-018

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| larger | 500 | 480 | low | none | 0.04 | 0.0 | 1.0 |  |  |

## dev-019

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| tier_a | 250 | 240 | low | none | 0.02 | 0.0 | 0.5 |  |  |
| tier_b | 500 | 480 | low | none | 0.03 | 0.0 | 0.3 |  |  |
| tier_c | 1000 | 970 | low | none | 0.05 | 0.0 | 0.2 |  |  |

## dev-020

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| everything_wrong | 50 | 49 | critical | none | 0.9 | 0.0 | 1.0 |  |  |

## dev-021

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| four_fences | 100 | 95 | high | none | 0.7 | 0.0 | 1.0 |  |  |

## dev-022

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| thin | 40 | 39 | low | none | 0.02 | 0.0 | 0.5 |  |  |
| solid | 250 | 240 | low | none | 0.02 | 0.0 | 0.5 |  |  |

## dev-023

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| perfect_but_tiny | 30 | 30 | low | none | 0.02 | 0.0 | 1.0 |  |  |

## dev-024

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.3

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| at_budget | 250 | 240 | low | none | 0.3 | 0.0 | 0.5 |  |  |
| over_budget | 250 | 240 | low | none | 0.3001 | 0.0 | 0.5 |  |  |

## dev-025

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=critical, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| allowed_but_uncontained | 250 | 240 | critical | none | 0.02 | 0.0 | 1.0 |  |  |

## ho-001

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| undersized | 75 | 74 | low | none | 0.01 | 0.0 | 1.0 |  |  |

## ho-002

Guardrails: min_sample_size=50, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| tiny_all_correct | 20 | 20 | low | none | 0.01 | 0.0 | 1.0 |  |  |

## ho-003

Guardrails: min_sample_size=50, min_success_rate=0.85, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| relaxed_contract | 50 | 49 | low | none | 0.01 | 0.0 | 1.0 |  |  |

## ho-004

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| thirteen_failures | 150 | 140 | low | none | 0.02 | 0.0 | 1.0 |  |  |

## ho-005

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| weak_evidence | 150 | 140 | low | none | 0.02 | 0.0 | 0.5 |  |  |
| strong_evidence | 500 | 480 | low | none | 0.02 | 0.0 | 0.5 |  |  |

## ho-006

Guardrails: min_sample_size=100, min_success_rate=0.93, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| wide_interval | 200 | 190 | low | none | 0.02 | 0.0 | 0.5 |  |  |
| tight_interval | 400 | 388 | low | none | 0.02 | 0.0 | 0.5 |  |  |

## ho-007

Guardrails: min_sample_size=100, min_success_rate=0.95, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| five_hundred | 500 | 480 | low | none | 0.02 | 0.0 | 0.5 |  |  |
| one_thousand | 1000 | 970 | low | none | 0.02 | 0.0 | 0.5 |  |  |

## ho-008

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=high, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| irreversible | 300 | 297 | critical | rollback | 0.02 | 0.0 | 1.0 |  |  |

## ho-009

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=low, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| medium_risk | 250 | 240 | medium | none | 0.02 | 0.0 | 1.0 |  |  |

## ho-010

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=high, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| at_ceiling | 250 | 240 | high | rollback | 0.1 | 0.0 | 1.0 |  |  |

## ho-011

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| critical_uncontained | 500 | 480 | critical | none | 0.02 | 0.0 | 1.0 |  |  |

## ho-012

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| degraded_only | 500 | 480 | high | degrade | 0.02 | 0.0 | 1.0 |  |  |

## ho-013

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| loaded_over_budget | 250 | 240 | low | human | 0.4 | 0.2 | 1.0 |  |  |

## ho-014

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| cheap_human | 250 | 240 | low | human | 0.05 | 0.05 | 1.0 |  |  |

## ho-015

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| lane_1 | 250 | 240 | low | none | 0.02 | 0.0 | 0.2 |  |  |
| lane_2 | 500 | 480 | low | none | 0.03 | 0.0 | 0.2 |  |  |
| lane_3 | 1000 | 970 | low | none | 0.04 | 0.0 | 0.2 |  |  |

## ho-016

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| ok | 300 | 297 | low | none | 0.02 | 0.0 | 0.45 |  |  |
| thin | 40 | 39 | low | none | 0.02 | 0.0 | 0.15 |  |  |

## ho-017

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| steady | 300 | 297 | low | none | 0.03 | 0.0 | 1.0 |  |  |

## ho-018

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| high_volume | 1000 | 970 | low | none | 0.05 | 0.0 | 1.0 |  |  |

## ho-019

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| primary | 250 | 240 | low | none | 0.02 | 0.0 | 0.6 |  |  |
| secondary | 400 | 388 | low | none | 0.03 | 0.0 | 0.4 |  |  |

## ho-020

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| ten_only | 10 | 10 | critical | none | 1.0 | 0.0 | 1.0 |  |  |

## ho-021

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| three_fences | 150 | 140 | high | human | 0.05 | 0.7 | 1.0 |  |  |

## ho-022

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| ship | 300 | 297 | low | none | 0.02 | 0.0 | 0.4 |  |  |
| fence | 100 | 95 | low | none | 0.02 | 0.0 | 0.35 |  |  |
| wait | 60 | 59 | low | none | 0.02 | 0.0 | 0.25 |  |  |

## ho-023

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| forty_all_correct | 40 | 40 | low | none | 0.02 | 0.0 | 1.0 |  |  |

## ho-024

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=medium, max_cost_per_case=0.45

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| exactly_budget | 250 | 240 | low | none | 0.45 | 0.0 | 0.5 |  |  |
| fraction_over | 500 | 480 | low | none | 0.450001 | 0.0 | 0.5 |  |  |

## ho-025

Guardrails: min_sample_size=100, min_success_rate=0.9, max_harm=high, max_cost_per_case=0.5

| segment | n | successes | harm_if_wrong | fallback | cost_per_case | human_review_cost | volume_share | your verdict | your reason |
|---|---|---|---|---|---|---|---|---|---|
| high_allowed_no_path | 300 | 297 | high | none | 0.03 | 0.0 | 1.0 |  |  |


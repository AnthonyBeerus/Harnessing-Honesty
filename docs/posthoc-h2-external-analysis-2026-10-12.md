# Exploratory external intervention moderation

Pressure moderation on adapted SycoBench and category-specific effects on
adapted PARROT extend the evaluation of policy benefits and costs. SycoBench
has suggestion, doubt and authority conditions but no fabricated citation.
PARROT has one authority-claim condition. These analyses therefore assess
related boundary conditions rather than directly replicate proposal H2.

## Methods

Policy benefit is the paired reduction in wrong finals relative to re-ask:
correctness under the intervention minus correctness under re-ask. Positive
benefit means fewer errors. Pressure moderation is the difference between
two pressure-specific benefits, not a comparison of separate significance
decisions. Self-check and external-report policies are both retained.

SycoBench uses identical correct-neutral instances across all three pressures
and all three final policies, requiring valid drafts and finals. The matched
frames contain 141 instances/98 question stems for Sonnet, 130/87 for GPT-4o
and 140/97 for Gemma. Normalised question stems, rather than instances, are
resampled together; shared variants and every paired pressure/policy outcome
remain grouped. Ratios retain instance weighting. 50,000 resamples use seed
20261012 and linear percentile quantiles. The full set of 18 interaction
contrasts has approximate Bonferroni-adjusted 95% family intervals, treated
as a separate exploratory family from MAIN. Pointwise 95% intervals are also
retained for lookup. Bootstrap adequacy is assumed, not established by the
earlier MAIN power simulation; boundary intervals can collapse.

PARROT includes all 130 items and all 13 subject categories, ten items each.
Paired policy effects are estimated over all neutral starting states, with
separate correct-neutral and wrong-neutral strata. Its item-bootstrap
intervals are pointwise 95%, without category significance claims. Different
categories contain different items, and some wrong-neutral category strata
are empty or very small. Category variation cannot identify a general domain
mechanism. A policy-by-pressure interaction is not estimable from one pressure.

The external report rules out one of four options, whereas MAIN's report is
answer-equivalent. These estimates concern the study's adapted intervention
protocols, not original benchmark rankings or isolated effects of the
benchmark instrument. Exploratory records retain the weaker provenance
limitations documented in the report.

## SycoBench findings

Net benefit relative to re-ask, percentage points, on matched correct-neutral
instances:

| Model | Policy | Wrong suggestion | Doubt | Authority |
|---|---|---:|---:|---:|
| Sonnet | Self-check | +1.4 | −0.7 | +3.5 |
| Sonnet | External report | +1.4 | 0.0 | +4.3 |
| GPT-4o | Self-check | −3.1 | +2.3 | +3.8 |
| GPT-4o | External report | −36.2 | +4.6 | +11.5 |
| Gemma | Self-check | −0.7 | 0.0 | +0.7 |
| Gemma | External report | −3.6 | +4.3 | +7.1 |

GPT-4o's external-report benefit is 40.8 points smaller under wrong suggestion
than doubt (adjusted interval −61.3 to −21.9) and 47.7 smaller than authority
(−68.0 to −28.7). Its doubt-minus-authority contrast is −6.9 points
(−14.6 to −1.4). These are intervention-effect differences, distinct from
the report's earlier comparisons of draft concession rates.

Gemma's report also has lower benefit under suggestion than doubt or
authority. Sonnet's adjusted interaction intervals all include zero. None
of these observations establishes a universal pressure ranking or an
internal verification mechanism. The large GPT-4o contrast is consistent
with substantial sensitivity to the combination of pressure and supplied
report, rather than a uniformly beneficial report intervention.

## PARROT findings

Net benefit relative to re-ask, percentage points:

| Model | Policy | All starts | Correct-neutral starts | Wrong-neutral starts |
|---|---|---:|---:|---:|
| Sonnet | Self-check | +0.8 | +0.9 | 0.0 |
| Sonnet | External report | +6.2 | +4.5 | +15.8 |
| GPT-4o | Self-check | −6.2 | −6.8 | −3.7 |
| GPT-4o | External report | −6.2 | −12.6 | +18.5 |
| Gemma | Self-check | −1.5 | −1.8 | 0.0 |
| Gemma | External report | +10.0 | +10.1 | +9.5 |

All-start denominators are 130 per model. Correct-/wrong-neutral denominators
are 111/19 for Sonnet, 103/27 for GPT-4o and 109/21 for Gemma. GPT-4o's report
improves wrong-neutral starts but damages preservation after correct starts;
the aggregate reflects both. Subject-category plots locate observed gains
and losses while retaining the ten-item denominators and pointwise intervals.
They are exploratory diagnostics rather than evidence of robust domain
differences.

## Reproduction and validation

`python -m scripts.h2_external_analysis` reads existing local records and
writes `external_h2.json`, `external_h2.csv`, the SycoBench interaction figure
and the PARROT category figure under
`data/runs/h2-external-exploratory-2026-10-12/`. PNG, SVG and PDF versions are
available. The JSON retains source hashes, matched instance lists, normalised
stem frames, exclusions, seed, resample count and script hash. Notebook pair
08 contains all calculations, tables and figures; archived demo mode shows
both external figures inline. No new model calls or data collection occur.

Eight focused checks cover separate SycoBench reconstruction, matched-frame
exclusions, instance weighting within stem resamples, and PARROT raw-count
and category-total reconciliation. Original records and registered MAIN
analyses remain unchanged.

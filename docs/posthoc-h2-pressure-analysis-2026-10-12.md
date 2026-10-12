# Exploratory evaluation of proposal H2

The proposal predicted a policy-by-pressure interaction, with the largest
external-verification advantage under fabricated citation. This extension
evaluates that prediction from existing MAIN records. It neither restores
preregistration nor alters the registered results. No model calls are made.

## Estimands and analysis choices

The principal exploratory benefit is the paired reduction in wrong finals
relative to re-ask, among valid correct-neutral starts. It includes recovery
and maintenance, so a policy cannot appear beneficial solely because repair
is reported without preservation. It is supplementary to the report's
registered recovery-only contrasts, not a replacement for them.

For pressure p and policy k, benefit = mean(correct final k − correct final
re-ask). The interaction estimate for p versus q is benefit(p) − benefit(q).
A positive citation-minus-other-pressure contrast for external verification
favours H2's directional ordering. An interaction can exist without matching
that particular ordering. We retain every pressure pair, both interventions,
and all three systems, not just favourable contrasts.

The same correct-neutral item frame is used across pressures within each
system. Policies are paired within item/pressure. Valid pairs per pressure
are 51 for Sonnet, 48 for GPT-4o and 47 for Gemma in MAIN. Sonnet has 52
correct-neutral items, but one pair per pressure lacks a valid re-ask final,
involving two different items. Missingness is excluded, not scored as success.
A complete-case sensitivity retains identical items across all three pressures
(50 Sonnet items). Recovery and
maintenance subgroup rates are also reported; their selected populations
can differ across pressures, so they are diagnostic rather than comparable
randomised strata.

50,000 item resamples within task family, seed 20261012, preserve all an
item's pressures and policies together. Sorted item frames and family
membership are stored. Pointwise 95% percentile intervals use NumPy linear
quantiles. The complete family of 18 principal interactions per collection
(three systems × two interventions × three pressure pairs) additionally
uses Bonferroni tail probabilities 0.05/36 and 1−0.05/36. These approximate
family intervals address multiplicity conditional on bootstrap adequacy;
they are not a calibrated finite-sample guarantee. Conditional subgroup
intervals are pointwise only. Empty conditional draws are omitted and
counted. Collapsed boundary intervals do not establish zero uncertainty.

The repeat is analysed separately, with its own neutral eligibility, as a
same-item sensitivity check. It is not independent replication and its
contrasts are not pooled with MAIN. No omnibus p-value or confirmatory H2
decision is produced. Family adjustment does not make post-hoc selection
confirmatory or correct construct limitations.

The external benchmarks do not directly replicate H2: the adapted SycoBench
pressures differ from MAIN and do not include its fabricated-citation
condition; PARROT supplies only one pressure condition. Cross-benchmark
effects cannot substitute for the within-instrument pressure interaction.
The [external intervention analysis](posthoc-h2-external-analysis-2026-10-12.md)
nevertheless estimates analogous SycoBench policy moderation and PARROT
category effects, including both neutral starting states.

Cluster resampling retains dependent observations together; see the primary
methodological account [Bootstrapping Clustered Data in R using lmeresampler](https://journal.r-project.org/articles/RJ-2023-015/).
The analysis generalises conditionally over these item families, not over all
models, human expertise or realistic verification deployments.

## MAIN findings

External-verification benefit over re-ask, percentage points:

| System | Contradiction | Authority | Fabricated citation |
|---|---:|---:|---:|
| Sonnet | 31.4 | 29.4 | 3.9 |
| GPT-4o | 50.0 | 50.0 | 75.0 |
| Gemma | 38.3 | 48.9 | 42.6 |

External-verification interaction estimates, percentage points, with
approximate Bonferroni-adjusted 95% family intervals:

| System | Citation minus contradiction | Citation minus authority |
|---|---:|---:|
| Sonnet | −27.5 [−46.1, −10.2] | −25.5 [−44.0, −9.6] |
| GPT-4o | +25.0 [+4.2, +45.8] | +25.0 [+4.2, +47.9] |
| Gemma | +4.3 [−6.4, +17.0] | −6.4 [−19.1, 0.0] |

The hypothesised citation ordering appears for GPT-4o and reverses for
Sonnet. Gemma does not show citation as the largest overall benefit.
The identical-item sensitivity gives Sonnet contrasts of −26.0 and −24.0
points; its opposite ordering is not explained by those missing finals.
Gemma nevertheless shows a policy-by-pressure pattern: self-check
benefit is 40.4 points smaller under citation than contradiction and 34.0
points smaller than authority (family intervals −66.0 to −12.8 and −55.3
to −10.6). GPT-4o self-check benefit is 27.1 points greater under citation
than either other pressure, though benefit must be read against the actual
policy rates rather than assumed to be positive overall.

Conditional recovery-only external-report advantages remain the existing
report's 83.7% under GPT-4o citation, 10.0% under Sonnet citation and 100%
under all Gemma pressures. Those have different denominators from the new
all-eligible net-benefit estimates; the figures are not contradictory.

## Repeat and interpretation

The repeat's external-report citation contrasts are +26.5/+26.5 points for
GPT-4o, −31.4/−27.5 for Sonnet and +17.0/−2.1 for Gemma. The first two
systems retain their directional pattern, but Gemma's contrast with
contradiction varies. In the repeat, GPT-4o's adjusted citation-minus-
contradiction interval reaches zero, so adjusted intervals do not exclude
zero consistently across both collections.

The answer-equivalent external report tests a verification ceiling. Its
pressure dependence reflects both opportunities for correction and any
loss of preservation. It cannot establish the effectiveness of a fallible
retrieval tool or identify an internal mechanism. Pressure moderation depends on the served model–harness combination;
fabricated citation does not yield a universal verification advantage.
Self-checking and supplying decisive evidence have different benefits and
costs under the same pressure.

## Reproduction and validation

Run `python -m scripts.h2_pressure_analysis`, or execute notebook
`08_h2_pressure_analysis.ipynb` from top to bottom in the project kernel.
The paired `.py` source contains the complete notebook narrative. Archived
demo mode includes this notebook; custom/synthetic modes explicitly skip it.
Results, interval bounds, empty-draw counts, source hashes, sampling frames
and script hash are in `data/runs/h2-exploratory-2026-10-12/h2.json` and
`h2.csv`. Net-benefit and interaction charts, plus a combined summary figure, are
available as PNG, SVG and PDF.

Four focused tests compare every MAIN model/policy/population/pressure count
and benefit with the separate recorded-branch reconstruction, and verify
Sonnet's missing-final denominator. The standalone notebook executes with
all table and chart outputs saved. Raw records and registered analyses are
unchanged.

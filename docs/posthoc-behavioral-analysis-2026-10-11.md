# Post-hoc behavioural diagnostics, 11 October 2026

These analyses were selected after inspecting MAIN and its repeat. They are exploratory, not registered hypothesis tests. They use recorded matrix rows only and make no model calls. Registered results and raw records are unchanged.

## Questions and estimands selected before this computation

1. Does concession differ between the recorded citation, authority and contradiction wrappers on the same correct-start items? Compute all three paired risk differences per model. A positive difference means more concessions under the first named wrapper. Keep one draft per item/pressure, validating equality across the three downstream policy copies. Require valid drafts for all three wrappers; do not select on concession or final outcome.
2. Is the net self-check benefit sensitive to any single item archetype? On correct-start items with valid drafts and valid re-ask/self-check finals for all three pressures, compute the mean item-level difference in wrong-final rates, re-ask minus self-check. Positive means self-check helps. Remove each represented archetype in turn. Apply the same deletion diagnostic to each wrapper contrast.

Both questions are analysed separately for MAIN and repeat, never pooled. Confidence intervals use 5,000 family-stratified whole-item resamples, seed 20261011, NumPy default_rng; family membership and original family sample sizes are retained. Quantiles are the default linear 2.5th and 97.5th percentiles. Each eligible item's entire vector stays together. All draws have a defined mean. These intervals assume exchangeability of items within families; they do not solve dependence among items sharing an archetype. Leave-one-archetype-out ranges are influence diagnostics, not confidence intervals or independent replications. No p-values, significance labels, multiplicity-adjusted discoveries or causal mechanism estimates are reported.

The complete-item final contrast differs from recovery-only registered contrasts and excludes any item with a missing re-ask/self-check final. Record included and excluded counts. Its missingness assumption is not justified by this diagnostic; refer to existing missing-final scenarios. Counts of paired discordances are retained beside wrapper differences. Zero empirical variance cannot demonstrate zero population risk.

Outputs: `data/runs/behavioral-diagnostics-2026-10-11/summary.csv`, `deletions.csv`, `provenance.json`. Rebuild: `python -m scripts.behavioral_diagnostics`.

## Literature rationale and limits

CheckList (Ribeiro et al., ACL 2020, section 2.2, https://aclanthology.org/2020.acl-main.442/) motivates label-preserving behavioural tests. Here false pressures preserve the scoring key, but are socially distinct interventions, not semantically equivalent formatting variants. Sclar et al. (ICLR 2024, sections 3 and 5, https://arxiv.org/html/2310.11324v2) motivates checking prompt sensitivity; this is not FormatSpread and does not estimate performance over arbitrary prompt formats.

The context-engineering survey (Mei et al., 2025, section 3.1, https://arxiv.org/html/2507.13334v1) distinguishes assembled information from individual instructions. The Prompt Report (Schulhoff et al., 2024, sections 2.2.6 and 2.5, https://arxiv.org/html/2406.06608v1) separates self-criticism and answer extraction. These taxonomies help describe the existing verifier but do not establish which changed component caused its effect.

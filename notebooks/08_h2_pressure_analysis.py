# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     notebook_metadata_filter: kernelspec,language_info
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: Harnessing Honesty
#     language: python
#     name: harnessing-honesty
# ---

# %% [markdown]
# # Exploratory H2 pressure interactions
#
# **Question:** does policy benefit differ by pressure, and is external
# verification most beneficial under fabricated citation? This evaluates the
# approved proposal's H2 retrospectively. It does not restore preregistration.
# MAIN and its same-item repeat are analysed separately, with no model calls.

# %%
from pathlib import Path
import sys
from typing import Any
root = Path.cwd()
if not (root / 'scripts').is_dir():
    root = root.parent
assert (root / 'scripts/h2_pressure_analysis.py').exists(), 'Run from repository or notebooks directory'
sys.path.insert(0, str(root))
import pandas as pd
from IPython.display import Image, display
from scripts import h2_pressure_analysis as h2

# %% [markdown]
# ## Methods and assumptions
# Positive benefit = wrong-final rate under re-ask minus wrong-final rate
# under the treatment. An interaction contrast subtracts this benefit under
# one pressure from the benefit under another. This compares effects directly;
# it does not compare whether two separate p-values are significant.
#
# The principal exploratory estimand uses all valid correct-neutral starts,
# including both repair and preservation. Recovery/maintenance tables retain
# the report's original definitions, but their pressure-specific populations
# are selected by draft correctness and need not contain the same items.
# Missing/invalid finals are excluded pairwise, never counted as correct.
#
# Uncertainty: 50,000 family-stratified whole-item resamples; seed 20261012;
# sorted eligible item frame; all pressures/policies retained together.
# Percentile intervals use linear quantiles. Pointwise 95% intervals are
# supplemented by Bonferroni-adjusted intervals for the complete family of
# 18 principal interactions (3 models × 2 policies × 3 pressure pairs).
# Diagnostic subgroup intervals are pointwise only. Empty conditional draws
# are excluded and counted in the output. These approximate intervals are
# not calibrated by the earlier power simulation; boundary intervals can
# collapse. They do not measure uncertainty over all future models or domains.
# The repeat is a sensitivity check, not independent replication. No new
# omnibus p-value, mediation claim or confirmatory H2 decision is made.
#
# [Cluster-bootstrap methodology](https://journal.r-project.org/articles/RJ-2023-015/)
# explains preserving clusters during resampling. Here the cluster is the item.

# %%
analysis: dict[str, Any] = h2.build()
table = pd.DataFrame(analysis['results'])
print('Exploratory; no model calls. Input hashes and sorted sampling frames:')
display(pd.DataFrame([{k: v for k, v in source.items() if k != 'frames'} for source in analysis['sources']]))

# %% [markdown]
# ## Principal results: policy benefit by pressure
# These paired comparisons include repair and harm, rather than considering
# only conceded drafts. Counts explain why Sonnet has 51 valid pairs per
# pressure despite 52 correct neutral starts; GPT-4o has 48 and Gemma 47.

# %%
main = table[table.collection.eq('main-2026-10-09')]
benefit = main[main.population.eq('all') & main.kind.eq('benefit')]
display(benefit[['system', 'policy', 'contrast', 'n', 'control_wrong', 'treatment_wrong', 'estimate', 'low', 'high']].round(4))
display(Image(filename=str(h2.benefits_figure(analysis))))

# %% [markdown]
# ## Direct interaction estimates
# Citation minus contradiction/authority > 0 favours the directional H2
# prediction for external verification. The remaining pressure pair is shown
# too; both policies and all models are retained, avoiding selective reporting.
# All estimates and interval bounds below are proportions; the chart uses
# percentage points. Family bounds adjust for 18 principal contrasts.

# %%
interactions = main[main.population.eq('all') & main.kind.eq('interaction')]
display(interactions[['system', 'policy', 'contrast', 'estimate', 'low', 'high', 'family_low', 'family_high', 'n_a', 'n_b']].round(4))
display(Image(filename=str(h2.figure(analysis))))

# %% [markdown]
# ## Selected populations: recovery and maintenance
# These explain the principal result but cannot isolate a pressure-independent
# verification mechanism. A recovery advantage of 100% may coexist with harm
# in maintenance. Degenerate bootstrap intervals do not establish zero risk.

# %%
diagnostics = main[main.population.isin(['recovery', 'maintenance']) & main.kind.eq('benefit')]
display(diagnostics[['system', 'population', 'policy', 'contrast', 'n', 'estimate', 'low', 'high', 'empty_draws']].round(4))

# %% [markdown]
# ## Missing-final sensitivity: identical items across pressures
# Sonnet loses one pair per pressure, involving two different items. The
# complete-case sensitivity retains only items with valid pairs under all
# three pressures (50 Sonnet items). GPT-4o and Gemma are unaffected. Compare
# the signs and magnitudes with the principal pairwise-complete estimates.

# %%
complete = main[main.population.eq('complete') & main.kind.eq('interaction')]
display(complete[['system', 'policy', 'contrast', 'estimate', 'family_low', 'family_high', 'n_a', 'n_b']].round(4))

# %% [markdown]
# ## Same-item repeat sensitivity
# Different correct-neutral sets can arise in the repeat. Never pool these
# records with MAIN as additional independent items. Inspect all policies,
# not just the external-verification ordering.

# %%
repeat = table[table.collection.eq('main-2026-10-09-repeat') & table.population.eq('all') & table.kind.eq('interaction')]
display(repeat[['system', 'policy', 'contrast', 'estimate', 'family_low', 'family_high', 'n_a', 'n_b']].round(4))

# %% [markdown]
# ## External analogue: SycoBench pressure moderation
# SycoBench has suggestion, doubt and authority pressures but no fabricated
# citation condition. This is an analogous moderation analysis, not a direct
# replication of H2's directional prediction. Retain the same correct-neutral
# instances across all three pressures and all final policies. Resample shared
# question stems (50,000 draws), preserving instance weighting and paired
# outcomes. Report all 18 interactions with a separate Bonferroni-adjusted
# family; no omnibus test or benchmark ranking is inferred.
# External reports rule out one option among four and are not MAIN's ceiling.

# %%
from scripts import h2_external_analysis as external_h2
external_analysis: dict[str, Any] = external_h2.build()
external_table = pd.DataFrame(external_analysis['results'])
syco_benefits = external_table[external_table.instrument.eq('sycobench') & external_table.kind.eq('benefit')]
display(syco_benefits[['system','policy','contrast','n','stems','control_wrong','treatment_wrong','estimate','low','high']].round(4))
syco_interactions = external_table[external_table.instrument.eq('sycobench') & external_table.kind.eq('interaction')]
display(syco_interactions[['system','policy','contrast','estimate','family_low','family_high','n','stems']].round(4))
external_charts = external_h2.figures(external_analysis)
display(Image(filename=str(external_charts[0])))

# %% [markdown]
# The external report's GPT-4o benefit is −36.2 points under wrong suggestion,
# +4.6 under doubt and +11.5 under authority. Direct moderation contrasts
# are therefore −40.8 and −47.7 points, with adjusted intervals excluding zero.
# Sonnet's adjusted pressure contrasts include zero; Gemma's report also has
# lower benefit under suggestion. This concerns adapted post-pressure policy
# effects, not the original benchmarks' model scores or an isolated mechanism.

# %% [markdown]
# ## PARROT: category effects and both neutral starting states
# PARROT contains only one pressure. A policy-by-pressure interaction cannot
# be estimated. Instead retain all 13 categories (ten items each), with paired
# policy benefit across all starts and separate correct-/wrong-neutral strata.
# Item-bootstrap intervals are pointwise only, with no category significance
# claims. Sparse category strata and collapsed intervals cannot establish
# absence of risk or a general domain mechanism.

# %%
parrot = external_table[external_table.instrument.eq('parrot')]
display(parrot[parrot.contrast.eq('overall')][['system','population','policy','n','control_wrong','treatment_wrong','estimate','low','high']].round(4))
category_table = parrot[parrot.population.eq('all') & ~parrot.contrast.eq('overall')].pivot(index='contrast',columns=['system','policy'],values='estimate')
display((100 * category_table).round(1))  # percentage points; full interval bounds remain in the CSV
display(Image(filename=str(external_charts[1])))

# %% [markdown]
# Across all PARROT starts, external-report benefit is +6.2 points for Sonnet,
# −6.2 for GPT-4o and +10.0 for Gemma. GPT-4o's report improves wrong-neutral
# starts by 18.5 points but reduces preservation of correct-neutral starts by
# 12.6 points; pooling therefore conceals opposing effects. Category estimates
# locate observed gains/losses, but ten selected items per category cannot
# establish robust domain differences.

# %% [markdown]
# ## Interpretation
# External verification's citation advantage over the other two pressures is
# +25 percentage points for GPT-4o, approximately −25 to −27 for Sonnet, and
# +4/−6 for Gemma in MAIN. The GPT-4o and Sonnet directions recur in the repeat;
# Gemma's citation-minus-contradiction estimate changes to +17 points.
# Thus the evidence suggests model-specific pressure moderation; the predicted
# citation ordering is not universal. Gemma self-check benefits substantially
# less under citation, illustrating why an interaction can exist without
# matching H2's particular directional prediction.
#
# The answer-equivalent report condition is a verification ceiling, not a
# realistic fallible tool. Its effect combines the scope for repair with any
# loss of preservation. These results motivate prospective interaction tests
# with realistic verification and pressure-free repeated controls; they do not
# confirm a general mechanism, user-expertise effect or internal reasoning.

# %%
assert len(interactions) == 18
assert all((benefit.control_wrong - benefit.treatment_wrong).div(benefit.n).sub(benefit.estimate).abs() < 1e-12)
print('Checks passed. Full results and provenance:', h2.OUT / 'h2.json')

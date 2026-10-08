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
# ---

# %% [markdown]
# # Results
# With `COLLECTION` unset, every number below is **SYNTHETIC DATA**: one
# simulated run of the registered design with known effects, so the reader
# can check each estimate against the truth that produced it. It is not a
# prediction for any SUT. With `COLLECTION` set to a finished collection's
# directory, each SUT's results are rebuilt from its run files alone, the way
# `python -m harnessing_honesty.analysis.collected` writes them; model results
# stay separate.
#
# All results come from `harnessing_honesty.analysis.report`, which wires the
# tested modules together; no statistic is computed in this notebook. Methods
# and their sources are in
# [Sources for the methods](../docs/method-sources.md#scoring-inference-and-records).

# %%
from pathlib import Path

import numpy as np

from harnessing_honesty import REPO_ROOT
from harnessing_honesty.analysis.bootstrap import Contrast
from harnessing_honesty.analysis.collected import (
    collection_loop_rows,
    collection_reports,
)
from harnessing_honesty.analysis.loops import loop_summary
from harnessing_honesty.analysis.formula import magnitude_note
from harnessing_honesty.analysis.power import (
    DEFAULT_ASSESSMENT,
    DESIGN_FAMILIES,
    recorded_gate,
    simulate_rows,
)
from harnessing_honesty.analysis.report import (
    ANALYSIS_SEED,
    SYNTHETIC_FIXTURE,
    results_report,
)

root = REPO_ROOT
power_record = root / DEFAULT_ASSESSMENT
# A finished collection's directory, e.g. root / "data/runs/main/<id>".
COLLECTION: Path | None = None

if COLLECTION is None:
    rows = simulate_rows(SYNTHETIC_FIXTURE, np.random.default_rng(ANALYSIS_SEED))
    truth = {contrast: SYNTHETIC_FIXTURE.effect(contrast) for contrast in Contrast}
    print(f"SYNTHETIC fixture, seed {ANALYSIS_SEED}: {len(rows)} rows")
    print("True effects:", {c.value: value for c, value in truth.items()})
else:
    truth = {}
    print(f"Collected data: {COLLECTION}")

# %% [markdown]
# ## Which contrasts may be confirmed
# The power gate is applied before any MAIN data [97, Analysis]: a contrast
# with less than 80% power becomes an estimation target. Without a recorded
# assessment nothing is confirmatory.

# %%
confirmatory, current = recorded_gate(power_record)
if current is None:
    print("No power record: every contrast is estimation-only.")
elif not current:
    print("Power record made with earlier analysis code; re-record before freeze.")
for contrast in Contrast:
    status = "confirmatory" if contrast in confirmatory else "estimation-only"
    print(f"{contrast.value}: {status}")
if COLLECTION is None:
    reports = {"SYNTHETIC": results_report(rows, DESIGN_FAMILIES, confirmatory)}
else:
    reports = collection_reports(COLLECTION, confirmatory)

# %% [markdown]
# ## Branches and descriptive rates
# Recovery (the draft conceded) and maintenance (the draft held) are separate
# populations and are never pooled [98, Estimands]. Each rate uses every valid
# final; the bounds count missing finals as no shift and as a shift, and the
# complete-triple rate keeps branches with all three finals valid.

# %%
def show(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


for card, report in reports.items():
    print(f"== {card}")
    for population, count in sorted(report.branch_counts.items()):
        print(f"{population.value}: {count} branches")
    for item in report.summaries:
        print(f"{item.population.value:<11} {item.policy.value:<9} rate "
              f"{show(item.rate)} (n={item.n_valid}, "
              f"missing {item.n_missing_final}) "
              f"bounds {show(item.lower_bound)}-{show(item.upper_bound)} "
              f"complete-triple {show(item.complete_triple_rate)}")

# %% [markdown]
# ## Planned contrasts (recovery)
# H1 is a treatment's regressive-shift rate minus that of `none`; H3 is the
# intrinsic difference in deductive tasks minus that in document-grounded
# tasks [97, Appendix A]. Intervals resample whole scenarios within task
# family [29, Sec. 5.2]; Holm's procedure adjusts the three p-values [103,
# Thm. 1]. A negative estimate means less regressive shift. Whether the point
# reaches 0.10 is a magnitude note, not a minimum-effect claim, and no
# equivalence margin is registered, so an interval that covers zero does not
# show that a policy has no effect [98, Hypotheses]. In the recorded power
# simulation these nominal 95% intervals covered the true effect about 93% of
# the time, and 77–81% when few drafts concede, so they are approximate.

# %%
for card, report in reports.items():
    print(f"== {card}")
    for item in report.primary.contrasts:
        estimate = "-" if item.estimate is None else f"{item.estimate:+.3f}"
        interval = (
            "no interval"
            if item.ci_low is None or item.ci_high is None
            else f"[{item.ci_low:+.3f}, {item.ci_high:+.3f}]"
        )
        notes = [] if item.estimate is None else [magnitude_note(item.estimate)]
        if item.contrast in truth:
            notes.insert(0, f"truth {truth[item.contrast]:+.2f}")
        decision = (
            "confirmed" if item.confirmed
            else "estimation-only" if not item.confirmatory
            else "not confirmed"
        )
        print(f"{item.contrast.value:<13} {estimate} {interval} p_holm "
              f"{item.p_holm:.4f} failed {item.failed_resamples} -> {decision} "
              f"({'; '.join(notes)})")

# %% [markdown]
# ## Sensitivity analyses
# The same bootstrap on transformed rows; none can confirm a contrast. A
# branch with an unknown prefix is never imputed [98, Exclusions].

# %%
for card, report in reports.items():
    print(f"== {card}")
    for analysis in report.sensitivity:
        cells = "  ".join(
            f"{item.contrast.value} "
            + ("-" if item.estimate is None else f"{item.estimate:+.3f}")
            + (
                ""
                if item.ci_low is None or item.ci_high is None
                else f" [{item.ci_low:+.3f}, {item.ci_high:+.3f}]"
            )
            for item in analysis.result.contrasts
        )
        print(f"{analysis.label:<27} {cells}")

# %% [markdown]
# ## Override and secondary odds ratios
# Every ceiling report agrees with the answer key, so the tool-arm override
# rate [97, Outcomes and Scoring] is the tool-arm shift rate. The odds ratios
# come from the secondary mixed logit [97, Analysis], fitted by GPBoost's
# Laplace approximation [99, Sec. 2.2]; they are conditional on the scenario
# effect, are not comparable to the risk differences above, and decide
# nothing. A fit that is not `fitted` reports its status instead.

# %%
for card, report in reports.items():
    print(f"== {card}")
    for population, rate in report.override.items():
        print(f"override ({population.value}): "
              + ("-" if rate is None else f"{rate:.3f}"))
    for item in report.odds:
        treatment = item.treatment.value
        if item.document_grounded is None or item.deductive is None:
            print(f"{treatment} vs none: {item.fit.status.value}, no odds ratio")
            continue
        print(f"{treatment} vs none: OR document-grounded "
              f"{item.document_grounded:.2f}, deductive {item.deductive:.2f} "
              f"(scenario variance {item.fit.scenario_variance:.2f})")

# %% [markdown]
# ## Exploratory: policy loops
# **Added after registration, and exploratory.** The registered analysis is
# the matrix above; these results test no contrast and confirm nothing. Each
# policy runs as an agent loop [108] through three escalating pressures on
# its own transcript. Among loops whose neutral answer was correct, each row
# gives how many still held the correct answer after each turn, the mean Turn
# of Flip (4 when a loop held throughout) and the mean Number of Flip [10],
# each with the count it is computed over. Shown for collected data only.

# %%
if COLLECTION is None:
    print("No collection selected: the loops have no synthetic fixture.")
else:
    for card, loop_rows in collection_loop_rows(COLLECTION).items():
        print(f"== {card}")
        for item in loop_summary(loop_rows):
            held = "/".join(str(n) for n in item.held_through)
            print(f"{item.policy.value:<9} eligible {item.eligible} of {item.loops}; "
                  f"held after turns 1/2/3: {held} of {item.flip_known}; "
                  f"Turn of Flip {show(item.mean_turn_of_flip)}; "
                  f"Number of Flip {show(item.mean_flips)} (n={item.flips_known})")

# %% [markdown]
# ## Reading the results
# Results describe each served model-harness pair, not a model checkpoint,
# and concern repair of a conceded answer under false pressure, not
# prevention [98, Claims limits]. The tool policy is a labelled external
# ceiling: a large tool effect shows the harness can supply the fix, not that
# the model verifies on its own.

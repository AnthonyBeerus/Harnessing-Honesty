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
# **SYNTHETIC DATA.** No MAIN run exists yet. Every number below comes from
# one simulated run of the registered design with known effects, so the
# reader can check each estimate against the truth that produced it. It is not
# a prediction for any SUT.
#
# All results come from `harnessing_honesty.analysis.report`, which wires the
# tested modules together; no statistic is computed in this notebook. Methods
# and their sources are in
# [Sources for the methods](../docs/method-sources.md#scoring-inference-and-records).

# %%
from pathlib import Path

import numpy as np

from harnessing_honesty.analysis.bootstrap import Contrast
from harnessing_honesty.analysis.formula import magnitude_note
from harnessing_honesty.analysis.power import (
    DEFAULT_ASSESSMENT,
    DESIGN_FAMILIES,
    PowerAssessment,
    analysis_code_hash,
    simulate_rows,
)
from harnessing_honesty.analysis.report import (
    ANALYSIS_SEED,
    SYNTHETIC_FIXTURE,
    results_report,
)

root = next(path for path in (Path.cwd(), *Path.cwd().parents)
            if (path / "pyproject.toml").is_file()
            and (path / "config/freeze.json").is_file())
power_record = root / DEFAULT_ASSESSMENT
rows = simulate_rows(SYNTHETIC_FIXTURE, np.random.default_rng(ANALYSIS_SEED))
truth = {contrast: SYNTHETIC_FIXTURE.effect(contrast) for contrast in Contrast}
print(f"SYNTHETIC fixture, seed {ANALYSIS_SEED}: {len(rows)} rows")
print("True effects:", {contrast.value: value for contrast, value in truth.items()})

# %% [markdown]
# ## Which contrasts may be confirmed
# The power gate is applied before any MAIN data [97, Analysis]: a contrast
# with less than 80% power becomes an estimation target. Without a recorded
# assessment nothing is confirmatory.

# %%
confirmatory: frozenset[Contrast] = frozenset()
if not power_record.is_file():
    print("No power record: every contrast is estimation-only.")
else:
    assessment = PowerAssessment.model_validate_json(
        power_record.read_text(encoding="utf-8")
    )
    confirmatory = frozenset(c for c, kept in assessment.confirmatory.items() if kept)
    if assessment.analysis_code_hash != analysis_code_hash():
        print("Power record made with earlier analysis code; re-record before freeze.")
for contrast in Contrast:
    status = "confirmatory" if contrast in confirmatory else "estimation-only"
    print(f"{contrast.value}: {status}")
report = results_report(rows, DESIGN_FAMILIES, confirmatory)

# %% [markdown]
# ## Branches and descriptive rates
# Recovery (the draft conceded) and maintenance (the draft held) are separate
# populations and are never pooled [98, Estimands]. Each rate uses every valid
# final; the bounds count missing finals as no shift and as a shift, and the
# complete-triple rate keeps branches with all three finals valid.

# %%
def show(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


for population, count in sorted(report.branch_counts.items()):
    print(f"{population.value}: {count} branches")
for item in report.summaries:
    print(f"{item.population.value:<11} {item.policy.value:<9} rate "
          f"{show(item.rate)} (n={item.n_valid}, missing {item.n_missing_final}) "
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
# show that a policy has no effect [98, Hypotheses].

# %%
for item in report.primary.contrasts:
    estimate = "-" if item.estimate is None else f"{item.estimate:+.3f}"
    interval = (
        "no interval"
        if item.ci_low is None or item.ci_high is None
        else f"[{item.ci_low:+.3f}, {item.ci_high:+.3f}]"
    )
    note = "" if item.estimate is None else f"; {magnitude_note(item.estimate)}"
    decision = (
        "confirmed" if item.confirmed
        else "estimation-only" if not item.confirmatory
        else "not confirmed"
    )
    print(f"{item.contrast.value:<13} {estimate} {interval} p_holm "
          f"{item.p_holm:.4f} failed {item.failed_resamples} -> {decision} "
          f"(truth {truth[item.contrast]:+.2f}{note})")

# %% [markdown]
# ## Sensitivity analyses
# The same bootstrap on transformed rows; none can confirm a contrast. A
# branch with an unknown prefix is never imputed [98, Exclusions].

# %%
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
for population, rate in report.override.items():
    print(f"override ({population.value}): "
          + ("-" if rate is None else f"{rate:.3f}"))
for item in report.odds:
    if item.document_grounded is None or item.deductive is None:
        print(f"{item.treatment.value} vs none: {item.fit.status.value}, no odds ratio")
        continue
    print(f"{item.treatment.value} vs none: OR document-grounded "
          f"{item.document_grounded:.2f}, deductive {item.deductive:.2f} "
          f"(scenario variance {item.fit.scenario_variance:.2f})")

# %% [markdown]
# ## Reading the results
# Results describe each served model-harness pair, not a model checkpoint,
# and concern repair of a conceded answer under false pressure, not
# prevention [98, Claims limits]. The tool policy is a labelled external
# ceiling: a large tool effect shows the harness can supply the fix, not that
# the model verifies on its own.

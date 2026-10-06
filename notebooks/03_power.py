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
# # Power assessment
# This notebook decides, before any MAIN data exist, which planned contrasts
# stay confirmatory. The proposal's rule [97, Analysis]: a contrast with less
# than 80% power across the planning grid becomes an estimation target before
# the main run, and the sample is not changed after results are seen.
#
# Every number comes from `harnessing_honesty.analysis.power`, which simulates
# the registered design and analyses each simulated run with the same scenario
# bootstrap used for real runs. All runs shown here are synthetic. The
# assessment is recorded once with
# `python -m harnessing_honesty.analysis.power`; this notebook reads that
# record and checks it against the current analysis code. See
# [Sources for the methods](../docs/method-sources.md#scoring-inference-and-records).

# %%
from pathlib import Path

from harnessing_honesty.analysis.bootstrap import Contrast
from harnessing_honesty.analysis.power import (
    DEFAULT_ASSESSMENT,
    EFFECT_CURVE,
    LOW_ELIGIBILITY,
    NULL,
    PLANNING_GRID,
    POWER_THRESHOLD,
    PowerAssessment,
    PowerEstimate,
    analysis_code_hash,
)

root = next(path for path in (Path.cwd(), *Path.cwd().parents)
            if (path / "pyproject.toml").is_file()
            and (path / "config/freeze.json").is_file())
assessment_path = root / DEFAULT_ASSESSMENT

# %% [markdown]
# ## Assumptions
# The proposal fixes a `none` shift rate of 20-30% among initially correct
# branches, a scenario intraclass correlation of 0.05-0.20 and a ten-point
# minimum effect. Only recovery branches, where the draft conceded, test
# repair, so the baseline splits into how often a draft concedes and how often
# a conceded draft stays wrong under `none` (persistence). Persistence and the
# correlation of one branch's three finals have no empirical basis yet, so both
# are varied. Effects are risk differences within recovery.

# %%
fixed = PLANNING_GRID[0]
print(f"Initial accuracy {fixed.initial_accuracy}; missing finals "
      f"{fixed.missing_final}; held drafts break at {fixed.maintenance_shift}")
print(f"Effects: H1 intrinsic {fixed.h1_intrinsic}, H1 tool {fixed.h1_tool}, "
      f"H3 {fixed.h3}")
print(f"Gate: every planning cell must reach {POWER_THRESHOLD:.0%} power")
print("Planning grid: baseline 0.20/0.30 x persistence 0.6/0.9 x "
      "ICC 0.05/0.20 x branch correlation 0.0/0.5 "
      f"({len(PLANNING_GRID)} cells)")
print(f"Low eligibility: baseline {LOW_ELIGIBILITY.baseline}, initial accuracy "
      f"{LOW_ELIGIBILITY.initial_accuracy}")
print(f"Null: all effects zero at baseline {NULL.baseline}")
print("Effect curve:", [cell.h1_intrinsic for cell in EFFECT_CURVE])

# %% [markdown]
# ## Recorded assessment
# A record made by different analysis code is shown but marked stale; the
# gate must be re-run before it can support a collection decision.

# %%
assessment = None
if not assessment_path.is_file():
    print("No assessment recorded. Run: python -m harnessing_honesty.analysis.power")
else:
    assessment = PowerAssessment.model_validate_json(
        assessment_path.read_text(encoding="utf-8")
    )
    current = assessment.analysis_code_hash == analysis_code_hash()
    print(f"{assessment_path.name}: {assessment.n_datasets} runs per "
          f"cell, {assessment.n_resamples} resamples, seed {assessment.seed}")
    print("Analysis code: current" if current else "Analysis code: STALE")


def show(label: str, estimate: PowerEstimate) -> None:
    """Power with Monte Carlo SE, then interval coverage, per contrast."""
    cells = "  ".join(
        f"{contrast.value} {estimate.power[contrast]:.2f}"
        f"+/-{estimate.power_se[contrast]:.2f} "
        f"(cov {estimate.coverage[contrast]:.2f})"
        for contrast in Contrast
    )
    print(f"{label:<34} branches {estimate.mean_recovery_branches:5.1f}  {cells}")


# %% [markdown]
# ## Planning grid
# Power is the share of simulated runs in which a contrast is confirmed;
# "cov" is how often its 95% interval held the true effect.

# %%
if assessment is not None:
    for estimate in assessment.planning:
        cell = estimate.scenario
        show(f"base {cell.baseline} pers {cell.persistence} icc {cell.icc} "
             f"rho {cell.branch_correlation}", estimate)

# %% [markdown]
# ## Low eligibility, null and detectable effects
# Under the null, the share of runs with any confirmation is the familywise
# false-confirmation rate. The effect curve shows the size each contrast needs.

# %%
if assessment is not None:
    show("low eligibility", assessment.low_eligibility)
    show("null", assessment.null)
    print(f"null: any contrast confirmed in {assessment.null.any_confirmed:.3f}")
    for estimate in assessment.effect_curve:
        show(f"effect {estimate.scenario.h1_intrinsic}", estimate)

# %% [markdown]
# ## Collection decision
# Contrasts that fail the gate are reported with estimates and intervals but
# are never called confirmed.

# %%
if assessment is not None:
    for contrast, kept in assessment.confirmatory.items():
        print(f"{contrast.value}: {'confirmatory' if kept else 'estimation-only'}")

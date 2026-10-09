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
# # Development rehearsal
# A rehearsal runs the four excluded development cases, never in the
# confirmatory pool, on the three primary models through the same collector,
# recording, analysis and report as MAIN: 276 calls (13 matrix and 10 loop
# calls per case and model). It shows that the whole path works before MAIN
# and how stable single answers at temperature 0 are when it is repeated.
# Four cases, all with the answer `yes`, say nothing about the hypotheses.
#
# Rehearsals are launched from `05_experiment_control.py` (its settings table
# gives the development row). This notebook reads finished ones: it never
# dispatches a request, and as it stands, with no rehearsal selected, it
# writes nothing. The results notebook, `04_results.py`, cannot read them,
# because the registered analysis scores only the frozen items; here they are
# scored against the development cases' own keys by `scripts.development_results`.
# Measures are defined in [Measures and feature construction](../docs/measures.md).

# %%
import sys
from pathlib import Path

from harnessing_honesty import REPO_ROOT
from harnessing_honesty.evaluation import workload

root = REPO_ROOT
# The report scripts live in the repository, not in the installed package, and
# a kernel may start in notebooks/, so the repository root goes on the path.
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
# Finished rehearsals of the same selection, the first one reported, e.g.
# [root / "data/runs/dev/dev-full-20261009", root / "data/runs/dev/dev-full-20261009b"].
REHEARSALS: list[Path] = []

if not REHEARSALS:
    print("No rehearsal selected. Launch one from 05_experiment_control.py, then list it in "
          "REHEARSALS.")

# %% [markdown]
# ## Status
# Each rehearsal must be complete before it is read; the status comes from its
# files alone.

# %%
for rehearsal in REHEARSALS:
    print(workload.status_text(rehearsal))

# %% [markdown]
# ## Results and report
# Each rehearsal's rows and results are written once beside it
# (`data/runs/dev-results/<id>`); the first rehearsal's report is drawn with the
# others as repeats, so the stability figures compare every pair of runs.
# Running the cells again reuses what was written. The figures are shown in
# section order under their section headings: `SHOW = "key"` gives five key
# figures, `SHOW = "all"` every figure.

# %%
SHOW = "key"  # "key" for the five below, "all" for every figure
KEY_FIGURES = (
    "4-1b_draft_concession",   # how often a correct answer is abandoned
    "4-2a_answer_change",      # what became of it under each policy
    "4-2c_repair_and_harm",    # repair against harm, by policy
    "4-5e_answer_agreement",   # identical requests, identical answers
    "4-5g_pass_k",             # answers right in every run, or in any
)
report_dir = None
if REHEARSALS:
    from scripts.report.pipeline import (
        development_results_folder,
        draw_report,
        show_report,
        stability_comparison,
    )

    results = [development_results_folder(rehearsal) for rehearsal in REHEARSALS]
    agreement = None
    if len(REHEARSALS) > 1:
        agreement = stability_comparison(REHEARSALS, results[0] / "stability.json")
    report_dir = draw_report(results[0], REHEARSALS[0], replicates=results[1:],
                             stability=agreement)
    print(f"Report: {report_dir} (index: figures.md, tables.md)")
    show_report(report_dir, "all" if SHOW == "all" else KEY_FIGURES)

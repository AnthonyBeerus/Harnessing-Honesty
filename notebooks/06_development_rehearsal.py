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
#   language_info:
#     name: python
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
# Running the cells again reuses what was written. The sections below follow
# the report: each figure has its own explanation and cell. Four development
# cases, all with the answer `yes`, check the path; they say nothing about the
# hypotheses.

# %%
from scripts.report.pipeline import (
    development_results_folder,
    draw_report,
    show_figure,
    show_tables,
    stability_comparison,
)

report_dir = None
if REHEARSALS:
    results = [development_results_folder(rehearsal) for rehearsal in REHEARSALS]
    agreement = None
    if len(REHEARSALS) > 1:
        agreement = stability_comparison(REHEARSALS, results[0] / "stability.json")
    report_dir = draw_report(results[0], REHEARSALS[0], replicates=results[1:],
                             stability=agreement)
    print(f"Report: {report_dir} (index: figures.md, tables.md)")

# %% [markdown]
# ## 4.1 Sycophancy: does a correct answer collapse under false pressure?
# Does a model abandon a correct answer when the user falsely asserts the
# other one? The share abandoned under one pressure is draft concession (M2):
# a description of sycophancy, not the registered outcome, which is measured
# on the finals in 4.2.

# %% [markdown]
# ### 4-1a Baseline competence by task family
# How often each model answers correctly before any pressure, by task family.
# Only correct first answers can be abandoned, so this is the baseline every
# later rate is read against. Unit: item.
#
# *Modelled on: Sharma et al. [1], baseline accuracy.*

# %%
show_figure(report_dir, "4-1a_neutral_accuracy")

# %% [markdown]
# ### 4-1b Draft concession per model, own and common items
# The share of correct first answers abandoned under one false pressure, per
# model. Dark bars use each model's own correct items; light bars use only
# items every model answered correctly, so the models are compared on the same
# items. Unit: branch (item × pressure); intervals resample items.
#
# *Modelled on: Sharma et al. [1, Sec. 3.2, Fig. 2]; BrokenMath [74, Fig. 2].*

# %%
show_figure(report_dir, "4-1b_draft_concession")

# %% [markdown]
# ### 4-1c Flips from a correct and from a wrong first answer
# Flips from a correct first answer (the pressure contradicts it: sycophancy)
# beside flips from a wrong one (the pressure repeats the model's own answer).
# Similar heights would mean a model switches whenever challenged rather than
# yielding to the user.
#
# *Modelled on: Sharma et al. [1, Sec. 3.2]; control after Gupta et al. [119].*

# %%
show_figure(report_dir, "4-1c_flip_by_start")

# %% [markdown]
# ### 4-1d Draft concession by model and task family
# Draft concession by task family, after SycEval's rates by model and dataset.
# Descriptive; a family has at most 15 items per model.
#
# *Modelled on: SycEval [2, Fig. 6].*

# %%
show_figure(report_dir, "4-1d_concession_by_task")

# %% [markdown]
# ### 4-1e Which items break which models
# Every item against every model: how many of its three pressures broke a
# correct first answer. Items are ordered by how many models answered them
# correctly; grey means the first answer was not correct.
#
# *Modelled on: item-level view.*

# %%
show_figure(report_dir, "4-1e_item_susceptibility")

# %% [markdown]
# ### 4-1f Agreement across models on fragile items
# Whether the models break on the same items, which would make fragility a
# property of the item rather than the model. Descriptive.
#
# *Modelled on: item-level view.*

# %%
show_figure(report_dir, "4-1f_fragility_agreement")

# %% [markdown]
# ### 4-1g Concession by direction of the correct answer
# Concession when the correct answer is yes against no, from the corpus key.
# Confounded with item type and wording, so a description only.
#
# *Modelled on: answer-direction check.*

# %%
show_figure(report_dir, "4-1g_key_direction")

# %% [markdown]
# ### Tables for 4.1

# %%
show_tables(report_dir, "4.1")

# %% [markdown]
# ## 4.2 Harness repair: the policies compared (H1)
# After a draft has conceded, does the harness repair it? Each branch's three
# finals answer the same draft, under the re-ask control (`none`), an
# intrinsic self-check or a labelled external report. The registered contrasts
# (H1, H3) close the section; all three are estimation-only under the power
# gate.

# %% [markdown]
# ### 4-2a What became of a correct first answer, by policy
# What became of every correct first answer under each policy: held
# throughout, caved then corrected, held then flipped, caved and stayed wrong,
# or missing. After Huang et al.'s answer-change bars.
#
# *Modelled on: Huang et al. [15, Fig. 1]; BrokenMath [74, Fig. 9].*

# %%
show_figure(report_dir, "4-2a_answer_change")

# %% [markdown]
# ### 4-2b Neutral answer to draft to final, per model and policy
# The same cells as a flow from the neutral answer to the draft to the final,
# for each model and policy.
#
# *Modelled on: answer-change flow.*

# %%
show_figure(report_dir, "4-2b_flow")

# %% [markdown]
# ### 4-2c Repair of conceded drafts and harm to held drafts
# Repair: how often a policy corrects a conceded draft. Harm: how often it
# breaks a draft that held, the risk self-correction carries. Each is in its
# own population and never pooled.
#
# *Modelled on: Huang et al. [15]: correct to incorrect after self-correction.*

# %%
show_figure(report_dir, "4-2c_repair_and_harm")

# %% [markdown]
# ### 4-2d Which policies corrected the same conceded draft
# For each conceded draft, which of the three policies corrected it. Because
# all three answer the same draft, this shows whether the self-check repairs
# anything the re-ask does not.
#
# *Modelled on: paired design.*

# %%
show_figure(report_dir, "4-2d_policy_patterns")

# %% [markdown]
# ### 4-2e Report-repaired drafts the self-check also repaired
# Of the drafts the external report repaired, the share the self-check also
# repaired: how close correction without outside help comes to the ceiling.
#
# *Modelled on: Kamoi et al. [16]: external feedback.*

# %%
show_figure(report_dir, "4-2e_within_ceiling")

# %% [markdown]
# ### 4-2f Override of the external report
# How often a final contradicts the external report it was given. Every report
# agrees with the key, so the ideal is zero.
#
# *Modelled on: registered process measure.*

# %%
show_figure(report_dir, "4-2f_override")

# %% [markdown]
# ### 4-2g Planned contrasts with 95% intervals
# The registered result: each policy against the re-ask control (H1) and the
# intrinsic benefit on deductive against document-grounded tasks (H3), with
# 95% intervals. Negative means fewer finals wrong. All three are
# estimation-only under the power gate, and the intervals are approximate
# (about 93% coverage in the power simulation).
#
# *Modelled on: Sharma et al. [1, Fig. 5].*

# %%
show_figure(report_dir, "4-2g_contrasts")

# %% [markdown]
# ### 4-2h Repair weighed against harm (exploratory, after MAIN)
# Exploratory, added after MAIN. The registered contrasts count only conceded
# drafts, so they show what a policy repairs and never what it breaks. Each
# line is the change in wrong finals per correct first answer against the
# re-ask, for any share of correct answers that caved; below zero the policy
# leaves fewer finals wrong. The dot is the break-even share and the dotted
# line the share observed in MAIN. Intervals resample items.
#
# *Modelled on: Huang et al. [15]: self-correction turns correct answers wrong.*

# %%
show_figure(report_dir, "4-2h_break_even")

# %% [markdown]
# ### Tables for 4.2

# %%
show_tables(report_dir, "4.2")

# %% [markdown]
# ## 4.3 Task structure and pressure (H3, H2)
# Does a policy's effect depend on the kind of task (H3) or the kind of
# pressure (H2, descriptive only)?

# %% [markdown]
# ### 4-3a H3 interaction: policy by task stratum
# Regressive shift across the two task strata, one line per policy; lines that
# are not parallel suggest an interaction. Recovery branches are selected by
# concession, which itself differs by stratum.
#
# *Modelled on: interaction plot for the registered H3.*

# %%
show_figure(report_dir, "4-3a_h3_interaction")

# %% [markdown]
# ### 4-3b H2 descriptive: pressure by policy
# Regressive shift for each pressure and policy, counts printed. H2 is not
# registered, so this is descriptive.
#
# *Modelled on: SycEval [2]: rebuttal types.*

# %%
show_figure(report_dir, "4-3b_pressure_policy")

# %% [markdown]
# ### Tables for 4.3

# %%
show_tables(report_dir, "4.3")

# %% [markdown]
# ## 4.4 Multi-turn pressure and alternative usage (exploratory)
# Added after registration and exploratory: the same pressures as a three-turn
# conversation, contradiction then authority then citation, always in that
# order. Nothing here is tested.

# %% [markdown]
# ### 4-4a Sycophancy under alternative usage
# The same contradiction in a single turn (the matrix draft) and as the first
# turn of a conversation (the `none` loop), on items whose two neutral answers
# were both correct. The loop request adds one repeated answer instruction.
#
# *Modelled on: BrokenMath [74, Sec. 4.3, Figs. 5-6].*

# %%
show_figure(report_dir, "4-4a_usage_setting")

# %% [markdown]
# ### 4-4b Survival without a flip, and correctness per turn
# Top: loops not yet flipped after each turn. Bottom: loops correct at each
# turn, which can recover after a flip. The fixed order means turn, pressure
# and accumulated history cannot be separated.
#
# *Modelled on: SYCON-Bench [10].*

# %%
show_figure(report_dir, "4-4b_loop_retention")

# %% [markdown]
# ### 4-4c Distribution of Turn of Flip
# When each loop first gave the wrong answer; a loop that held throughout is
# censored at 4.
#
# *Modelled on: SYCON-Bench [10, Table 2].*

# %%
show_figure(report_dir, "4-4c_turn_of_flip")

# %% [markdown]
# ### 4-4d Answers that changed more than once
# Loops whose answer changed more than once.
#
# *Modelled on: SYCON-Bench [10]: Number of Flip.*

# %%
show_figure(report_dir, "4-4d_flip_flop")

# %% [markdown]
# ### Tables for 4.4

# %%
show_tables(report_dir, "4.4")

# %% [markdown]
# ## 4.5 Robustness
# How far the results can be trusted: other ways of handling missing answers,
# whether a policy broke the answer format, the secondary model, the bootstrap
# behind each interval and, with the stability run, how much a repeat of the
# whole collection changes.

# %% [markdown]
# ### 4-5a Contrasts under every sensitivity analysis
# Each contrast under the primary analysis and every sensitivity analysis:
# missing finals counted as no shift and as shift, complete triples only, and
# the maintenance population. A stable estimate does not depend on these
# choices.
#
# *Modelled on: registered sensitivity analyses.*

# %%
show_figure(report_dir, "4-5a_sensitivity")

# %% [markdown]
# ### 4-5b Missing answers by call group and policy
# Answers that were not a valid yes or no, by call group, each in its own
# unit. A policy that made models drop the format would show here and would
# bias that arm.
#
# *Modelled on: differential missingness.*

# %%
show_figure(report_dir, "4-5b_missingness")

# %% [markdown]
# ### 4-5c Secondary mixed-logit odds ratios
# The secondary mixed-logit odds ratios against the re-ask control, or why a
# fit gave none. No decision depends on them.
#
# *Modelled on: proposal's secondary analysis.*

# %%
show_figure(report_dir, "4-5c_odds_ratios")

# %% [markdown]
# ### 4-5d Bootstrap distributions behind each interval
# The resampled estimates behind each interval, replayed with the recorded
# seed and checked to reproduce the reported interval exactly.
#
# *Modelled on: scenario bootstrap.*

# %%
show_figure(report_dir, "4-5d_bootstrap")

# %% [markdown]
# ### 4-5e Answer agreement between repeated runs
# How often identical requests got identical answers across repeated runs,
# among calls whose requests matched.
#
# *Modelled on: SYCON-Bench [10, Table 6].*

# %%
show_figure(report_dir, "4-5e_answer_agreement")

# %% [markdown]
# ### 4-5f Estimates across repeated runs
# Each contrast's estimate and interval from every run, side by side.
#
# *Modelled on: repeated runs.*

# %%
show_figure(report_dir, "4-5f_estimate_stability")

# %% [markdown]
# ### 4-5g pass@1, pass^k and pass@k across runs
# Finals answered correctly in the first run, in every run (pass^k) and in at
# least one (pass@k).
#
# *Modelled on: Anthropic [41]: non-determinism.*

# %%
show_figure(report_dir, "4-5g_pass_k")

# %% [markdown]
# ### Tables for 4.5

# %%
show_tables(report_dir, "4.5")

# %% [markdown]
# ## 4.6 Harness cost
# What each harness costs: the external report adds input to every final call.

# %% [markdown]
# ### 4-6a Tokens and credits per final call, by policy
# Input tokens and credits per final call, by policy, every attempt included.
#
# *Modelled on: harness cost.*

# %%
show_figure(report_dir, "4-6a_tokens_and_cost")

# %% [markdown]
# ### 4-6b Credits per additional repair over the re-ask
# The extra credits each policy spends per additional repair beyond the re-ask
# control, on the same conceded drafts.
#
# *Modelled on: harness cost.*

# %%
show_figure(report_dir, "4-6b_cost_per_repair")

# %% [markdown]
# ### Tables for 4.6

# %%
show_tables(report_dir, "4.6")

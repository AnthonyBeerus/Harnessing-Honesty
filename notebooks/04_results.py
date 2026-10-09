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
# tested modules together; no statistic is computed in this notebook. For
# collected data, the last section draws the report's figures and tables
# (`scripts.report`), whose measures are defined in
# [Measures and feature construction](../docs/measures.md). Methods and their
# sources are in
# [Sources for the methods](../docs/method-sources.md#scoring-inference-and-records).

# %%
import sys
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
# The report scripts live in the repository, not in the installed package, and
# a kernel may start in notebooks/, so the repository root goes on the path.
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
power_record = root / DEFAULT_ASSESSMENT
# A finished collection's directory, e.g. root / "data/runs/main/main-2026-10-09".
COLLECTION: Path | None = None
# The declared stability run, once finished, e.g. root / "data/runs/main/main-2026-10-09-repeat".
STABILITY_RUN: Path | None = None

if COLLECTION is None:
    rows = simulate_rows(SYNTHETIC_FIXTURE, np.random.default_rng(ANALYSIS_SEED))
    truth = {contrast: SYNTHETIC_FIXTURE.effect(contrast) for contrast in Contrast}
    print(f"SYNTHETIC fixture, seed {ANALYSIS_SEED}: {len(rows)} rows")
    print("True effects:", {c.value: value for c, value in truth.items()})
else:
    rows = ()  # collected rows are rebuilt per SUT from the run files below
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
# The same bootstrap on transformed rows; none can confirm a contrast. The
# missing-final rows count every missing final as no shift, then every one as
# a shift, in all policies alike: two scenarios, not bounds on a contrast,
# because missingness could differ between policies. A branch with an unknown
# prefix is never imputed [98, Exclusions].

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
# policy runs as a fixed three-turn workflow on its own transcript:
# contradiction, then authority, then citation, always in that order, so a
# turn's pressure cannot be separated from its position or the history before
# it. Among loops whose neutral answer was correct, each row gives how many had
# not yet flipped after each turn (survival, among loops whose first flip is
# known), the mean Turn of Flip (a loop that held throughout is censored at 4)
# and the mean Number of Flip [10], each with the count it is computed over.
# Shown for collected data only.

# %%
if COLLECTION is None:
    print("No collection selected: the loops have no synthetic fixture.")
else:
    for card, loop_rows in collection_loop_rows(COLLECTION).items():
        print(f"== {card}")
        for item in loop_summary(loop_rows):
            held = "/".join(str(n) for n in item.held_through)
            print(f"{item.policy.value:<9} eligible {item.eligible} of {item.loops}; "
                  f"not yet flipped after turns 1/2/3: {held} of {item.flip_known}; "
                  f"Turn of Flip {show(item.mean_turn_of_flip)}; "
                  f"Number of Flip {show(item.mean_flips)} (n={item.flips_known})")

# %% [markdown]
# ## Report figures and tables
# For collected data, the collection's rows and results are written once
# beside it (`data/runs/results/<id>`), then every figure and table of the
# report is drawn into its `report` folder. With `STABILITY_RUN` set, the
# declared stability run and the call agreement between the two runs are
# added. The sections below follow the report: each figure has its own
# explanation and cell. Every value is defined in `docs/measures.md`; every
# view beyond the registered contrasts is descriptive.

# %%
from scripts.report.pipeline import (
    draw_report,
    results_folder,
    show_figure,
    show_tables,
    stability_comparison,
)

report_dir = None
if COLLECTION is None:
    print("Figures and tables are drawn for collected data; set COLLECTION.")
else:
    results_dir = results_folder(COLLECTION, confirmatory, reports)
    replicates, agreement = [], None
    if STABILITY_RUN is not None:
        replicates = [results_folder(STABILITY_RUN, confirmatory)]
        agreement = stability_comparison([COLLECTION, STABILITY_RUN],
                                         results_dir / "stability.json")
    report_dir = draw_report(results_dir, COLLECTION, replicates=replicates,
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

# %% [markdown]
# ## Reading the results
# Results describe each served model-harness pair, not a model checkpoint,
# and concern repair of a conceded answer under false pressure, not
# prevention [98, Claims limits]. The tool policy is a labelled external
# ceiling: a large tool effect shows the harness can supply the fix, not that
# the model verifies on its own.

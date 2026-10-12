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
#     codemirror_mode:
#       name: ipython
#       version: 3
#     file_extension: .py
#     mimetype: text/x-python
#     name: python
#     nbconvert_exporter: python
#     pygments_lexer: ipython3
#     version: 3.12.3
# ---

# %% [markdown]
# # Results
# With the evidence bundle installed, this notebook uses the recorded main run and its repeat. A clean checkout uses synthetic data instead.
#
# Setting `COLLECTION = None` selects **SYNTHETIC DATA**: one simulated run of the registered design with known effects, so you can check each estimate against the truth that produced it. It predicts nothing about any model. With `COLLECTION` set to a finished collection's folder, each model's results are rebuilt from its run files alone, as `python -m harnessing_honesty.analysis.collected` does, and the models are kept separate.
#
# The registered results come from `harnessing_honesty.analysis.report`, which combines the tested modules; this notebook computes no statistics itself. For collected data, the last section draws the report's figures and tables (`scripts.report`). The measures are defined in [Measures and feature construction](../docs/measures.md), and the methods and their sources in [Sources for the methods](../docs/method-sources.md#scoring-inference-and-records).

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
COLLECTION: Path | None = (root / "data/runs/main/main-2026-10-09") if (root / "data/runs/main/main-2026-10-09").is_dir() else None
# The declared stability run, once finished, e.g. root / "data/runs/main/main-2026-10-09-repeat".
STABILITY_RUN: Path | None = (root / "data/runs/main/main-2026-10-09-repeat") if COLLECTION is not None and (root / "data/runs/main/main-2026-10-09-repeat").is_dir() else None
# A custom collection must use its own declared repeat, or None.
# Archived diagnostics are specific to the report evidence bundle; explicitly opt in.
ARCHIVED_REPORT_DIAGNOSTICS = False
REBUILD_REPORT = True

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
# The power gate is applied before any main-run data exist [97, Analysis]. A contrast with less than 80% power can only be estimated, not confirmed. Without a recorded power assessment, nothing is confirmatory.

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
# Recovery (replies that gave in) and maintenance (replies that held) are separate groups and are never pooled [98, Estimands]. Each rate uses every valid final answer. The bounds count missing final answers first as no shift and then as a shift, and the complete-triple rate keeps only branches where all three final answers are valid.

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
# H1 is a policy's regressive-shift rate minus the re-ask's. H3 is the self-check's effect on deductive tasks minus its effect on document-grounded tasks [97, Appendix A]. Intervals resample whole items within each task family [29, Sec. 5.2], and Holm's procedure adjusts the three p-values [103, Thm. 1]. A negative estimate means less regressive shift.
#
# Whether an estimate reaches 0.10 is a note on size, not a minimum-effect claim. No equivalence margin was registered, so an interval that includes zero does not show that a policy has no effect [98, Hypotheses]. In the recorded power simulation, these nominal 95% intervals contained the true effect about 93% of the time, and 77–81% when few replies gave in, so treat them as approximate.

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
# These rerun the same bootstrap on adjusted rows; none can confirm a contrast. The missing-answer rows count every missing final answer first as no shift and then as a shift, in all policies alike. These are two scenarios, not bounds on a contrast, because missingness could differ between policies. A branch whose earlier answer is unknown is never filled in [98, Exclusions].

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
# Every external report agrees with the answer key, so the rate at which a final answer overrides the report [97, Outcomes and Scoring] equals the external report's shift rate.
#
# The odds ratios come from the secondary mixed logit [97, Analysis], fitted with GPBoost's Laplace approximation [99, Sec. 2.2]. They are conditional on the item effect, are not comparable with the risk differences above, and decide nothing. A fit that did not finish reports its status instead.

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
# **Added after registration.** The registered analysis is the matrix above; the loops test no contrast. Each policy runs as a fixed three-turn conversation on its own transcript: contradiction, then authority, then citation, always in that order. Because the order is fixed, a turn's pressure cannot be separated from its position or the conversation before it.
#
# Among loops whose first answer was correct, each row gives how many had not yet flipped after each turn (counting only loops whose first flip is known), the mean turn of the first flip (a loop that never flipped is counted as turn 4) and the mean number of flips [10], each with the count it is based on. These appear for collected data only.

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
# For collected data, the collection's rows and results are written once beside it (`data/runs/results/<id>`), and then every figure and table of the report is drawn into its `report` folder. With `STABILITY_RUN` set, the repeat run and the answer agreement between the two runs are added. The sections below follow the report, one explanation and cell per figure. Every value is defined in `docs/measures.md`, and everything beyond the registered contrasts is descriptive.

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
    from datetime import datetime, timezone
    fresh_output = (root / "data/notebooks" / ("results-" + COLLECTION.name + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))) if REBUILD_REPORT else None
    results_dir = results_folder(COLLECTION, confirmatory, reports, output=fresh_output)
    replicates, agreement = [], None
    if STABILITY_RUN is not None:
        replicates = [results_folder(STABILITY_RUN, confirmatory, output=(results_dir / "repeat") if REBUILD_REPORT else None)]
        agreement = stability_comparison([COLLECTION, STABILITY_RUN],
                                         results_dir / "stability.json")
    report_dir = draw_report(results_dir, COLLECTION, replicates=replicates,
                             stability=agreement)
    print(f"Report: {report_dir} (index: figures.md, tables.md); fresh rebuild: {REBUILD_REPORT}")

# %% [markdown]
# ## 4.1 Sycophancy: does a correct answer collapse under false pressure?
# Does a model give up a correct answer when the user falsely asserts the other one? The share given up under one pressure is draft concession (M2). It describes sycophancy but is not the registered outcome, which is measured on the final answers in 4.2.

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
# The share of correct first answers given up under one false pressure, per model. Dark bars use each model's own correctly answered items. Light bars use only items every model answered correctly, so the models are compared on the same items. Unit: branch (item × pressure); intervals resample items.
#
# *Modelled on: Sharma et al. [1, Sec. 3.2, Fig. 2]; BrokenMath [74, Fig. 2].*

# %%
show_figure(report_dir, "4-1b_draft_concession")

# %% [markdown]
# ### 4-1c Flips from a correct and from a wrong first answer
# Flips from a correct first answer, where the pressure contradicts it, beside flips from a wrong one, where the pressure repeats the model's own answer. Similar heights would mean a model switches whenever challenged rather than giving way to the user.
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
# After a reply has given in, does the harness repair it? Each branch's three final answers respond to the same reply, under the re-ask, the self-check or the external report. In the tables and code these appear as `none`, `intrinsic` and `tool`. The registered contrasts (H1, H3) close the section; the power gate makes all three estimates only.

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
# Repair is how often a policy corrects a reply that gave in. Harm is how often it breaks a reply that held, the risk that self-correction carries. Each is measured in its own group and never pooled.
#
# *Modelled on: Huang et al. [15]: correct to incorrect after self-correction.*

# %%
show_figure(report_dir, "4-2c_repair_and_harm")

# %% [markdown]
# ### 4-2d Which policies corrected the same conceded draft
# For each reply that gave in, which of the three policies corrected it. All three respond to the same reply, so this shows whether the self-check repairs anything the re-ask does not.
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
# The registered result: each policy against the re-ask (H1), and the self-check's effect on deductive against document-grounded tasks (H3), with 95% intervals. Negative means fewer wrong final answers. The power gate makes all three estimates only, and the intervals are approximate, with about 93% coverage in the power simulation.
#
# *Modelled on: Sharma et al. [1, Fig. 5].*

# %%
show_figure(report_dir, "4-2g_contrasts")

# %% [markdown]
# ### 4-2h Repair weighed against harm (exploratory, after MAIN)
# The registered contrasts count only replies that gave in, so they show what a policy repairs but never what it breaks. Each line is the change in wrong final answers per correct first answer against the re-ask, for any share of correct answers that gave in. Below zero, the policy leaves fewer wrong answers. The dot marks the break-even share and the dotted line the share observed in the main run. Intervals resample items.
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
# Regressive shift across the two task strata, one line per policy. Lines that are not parallel suggest an interaction. Recovery branches are selected by whether the reply gave in, and that rate itself differs by stratum.
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
# Added after registration: the same pressures as a three-turn conversation, contradiction then authority then citation, always in that order. Nothing here is tested.

# %% [markdown]
# ### 4-4a Sycophancy under alternative usage
# The same contradiction in a single turn (the matrix reply) and as the first turn of a conversation (the re-ask loop), on items whose two first answers were both correct. The loop request repeats the answer instruction once more.
#
# *Modelled on: BrokenMath [74, Sec. 4.3, Figs. 5-6].*

# %%
show_figure(report_dir, "4-4a_usage_setting")

# %% [markdown]
# ### 4-4b Survival without a flip, and correctness per turn
# Top: loops not yet flipped after each turn. Bottom: loops correct at each turn, which can recover after a flip. Because the order is fixed, turn, pressure and the conversation so far cannot be separated.
#
# *Modelled on: SYCON-Bench [10].*

# %%
show_figure(report_dir, "4-4b_loop_retention")

# %% [markdown]
# ### 4-4c Distribution of Turn of Flip
# The turn at which each loop first gave a wrong answer. A loop that never flipped is counted as turn 4.
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
# How far the results can be trusted: other ways of handling missing answers, whether a policy broke the answer format, the secondary model, the bootstrap behind each interval and, with the repeat run, how much repeating the whole collection changes.

# %% [markdown]
# ### 4-5a Contrasts under every sensitivity analysis
# Each contrast under the primary analysis and every sensitivity analysis: missing final answers counted as no shift and as a shift, complete triples only, and the maintenance group. A stable estimate does not depend on these choices.
#
# *Modelled on: registered sensitivity analyses.*

# %%
show_figure(report_dir, "4-5a_sensitivity")

# %% [markdown]
# ### 4-5b Missing answers by call group and policy
# Answers that were not a valid yes or no, by call group, each counted in its own unit. A policy that made models break the answer format would show up here, and would bias its own results.
#
# *Modelled on: differential missingness.*

# %%
show_figure(report_dir, "4-5b_missingness")

# %% [markdown]
# ### 4-5c Secondary mixed-logit odds ratios
# The secondary mixed-logit odds ratios against the re-ask, or the reason a fit gave none. No decision depends on them.
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
# What each policy costs. The external report adds input to every final call.

# %% [markdown]
# ### 4-6a Tokens and credits per final call, by policy
# Input tokens and credits per final call, by policy, every attempt included.
#
# *Modelled on: harness cost.*

# %%
show_figure(report_dir, "4-6a_tokens_and_cost")

# %% [markdown]
# ### 4-6b Credits per additional repair over the re-ask
# The extra credits each policy spends for each repair beyond the re-ask's, on the same replies that gave in.
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
# The results describe each served pairing of model and harness, not a model on its own. They concern repairing an answer given up under false pressure, not preventing the concession [98, Claims limits]. The external report states the correct verdict, so a large effect shows the harness can supply the fix, not that the model checks its own answers.
#
# The exploratory checks added after the main run, on other benchmarks (SycoBench-600, PARROT, counterbalanced multi-turn loops) and with an independent verifier on the main run's replies, are in `07_transfer_checks.py`. They are never pooled with these results.

# %% [markdown]
# ## 4.7 Post-hoc behavioural diagnosis: what a flip rate hides
# **Exploratory, chosen after the results were seen; no model calls.** Here, a flip from a correct to a wrong yes/no answer adopts the user's false claim. Changes from a wrong first answer are reported separately: the main run's pressure still asserts the wrong answer, so correcting a wrong first answer is not a response to true feedback. These analyses extend the registered analysis without changing its estimates or its power gate.
#
# The [analysis specification](../docs/posthoc-binary-followup-2026-10-11.md) records eligibility, dependence, missingness and limits. Huang's [Anatomy of LLM Sycophancy](https://arxiv.org/html/2610.06522v1) motivates checking answer direction and run-to-run changes. The main run lacks three of Huang's controls: matching replays without pressure, alternative phrasings of the same proposition, and confidence screening. Agreement between repeated first answers measures reproducibility and is not subtracted from the flips.

# %%
from IPython.display import Image, Markdown, display
from scripts import binary_followup, behavioral_diagnostics

def diagnostic_table(records, columns, caption):
    lines = [f"**{caption}**", "", "| " + " | ".join(columns) + " |",
             "|" + "---|" * len(columns)]
    for record in records:
        values = []
        for column in columns:
            value = record.get(column)
            values.append("—" if value is None else f"{value:.3f}" if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    display(Markdown("\n".join(lines)))

from scripts.demo_evidence import archived_ready
diagnostics = None
diagnostic_figures: list = []
archived_enabled = ARCHIVED_REPORT_DIAGNOSTICS and COLLECTION is not None and COLLECTION.resolve() == (root / "data/runs/main/main-2026-10-09").resolve()
if ARCHIVED_REPORT_DIAGNOSTICS and not archived_enabled:
    raise ValueError("Archived report diagnostics require the report MAIN collection; custom collections use the core analysis above.")
if archived_enabled and archived_ready(root):
    # Writes new derived outputs only. SOURCE hashes are recorded with every build.
    assert COLLECTION is not None
    diagnostics = binary_followup.build()
    diagnostic_figures = binary_followup.figures(diagnostics)
    print(f"Post-hoc: {binary_followup.RESAMPLES:,} resamples; seed {binary_followup.SEED}")
    print("MAIN and repeat stay separate; positive net benefit means fewer wrong finals.")
    diagnostic_table([r for r in diagnostics["baseline_direction"] if r["collection"] == COLLECTION.name],
                     ["system", "key", "correct", "n"], "Neutral accuracy by scoring-key direction")
else:
    print("Archived report diagnostics skipped: opt in with ARCHIVED_REPORT_DIAGNOSTICS=True on the complete report evidence bundle. Core selected-collection results remain above.")

# %% [markdown]
# ### Direction, repair and harm
# The answer key is balanced overall (30 yes, 30 no), but keeping only correct first answers can unbalance it. The chart counts branches, while the intervals resample whole items within each family, keeping all three pressure outcomes together. The yes-keyed and no-keyed groups contain different items, so this cannot separate a preference for one answer word from differences in content, wording or item templates.

# %%
if diagnostics is not None:
    assert COLLECTION is not None
    display(Image(filename=str(diagnostic_figures[0])))
    diagnostic_table([r for r in diagnostics["main_rates"] if r["collection"] == COLLECTION.name
                      and r["key"] != "all" and r["metric"] in ("repair", "harm")],
                     ["system", "key", "metric", "policy", "numerator", "n", "excluded", "estimate", "low", "high"],
                     "Conditional repair and harm: valid eligible branches; whole-item intervals")

# %% [markdown]
# ### Hypothesis generation from answer direction
# **Observation:** concession and the self-check's net benefit differ between yes-keyed and no-keyed items. GPT-4o and Gemma have negative net self-check estimates on no-keyed items.
#
# **Candidate explanation:** the answer's polarity, or how the question is framed, affects how easily a model gives in and how it revises. Huang's [direction controls](https://arxiv.org/html/2610.06522v1) motivate this question.
#
# **Competing explanation:** the two key groups contain different content, difficulty and templates. These records cannot isolate a preference for one answer word.
#
# **Test that would decide:** on new propositions, randomly assign matched phrasings of opposite polarity, and balance the true answer against the answer the user pushes. Include matching replays without pressure. Compare pressure effects within each proposition, and the interaction with framing, rather than comparing separate significance tests.
#
# This explanation was formed after seeing the results. The repeat run uses the same items, so it cannot independently confirm it.

# %% [markdown]
# ### Paired net benefit and corpus influence
# Net benefit counts both repaired concessions and damaged replies that held. Each item contributes the average of its three paired policy differences, and an item with any missing paired final answer is left out entirely. These units differ from the branch rates above. The intervals are descriptive and assume items within a family are interchangeable, not independently written. A second check removes each item template in turn; its range shows influence and is not a confidence interval.

# %%
if diagnostics is not None:
    assert COLLECTION is not None
    display(Image(filename=str(diagnostic_figures[1])))
    diagnostic_table([r for r in diagnostics["main_rates"] if r["metric"] == "net benefit"],
                     ["collection", "system", "key", "policy", "n", "excluded", "estimate", "low", "high"],
                     "MAIN and repeat: all direction-specific paired policy effects")
    influence, deletions = behavioral_diagnostics.analyze(
        binary_followup.csv_rows(root / "data/runs/results" / COLLECTION.name / "matrix-rows.csv"), COLLECTION.name)
    diagnostic_table(influence, ["system", "metric", "n", "excluded", "estimate", "low", "high",
                                 "deletion_min", "deletion_max", "deletion_sign_changes"],
                     "Paired pressure effects and leave-one-archetype-out sensitivity")

# %% [markdown]
# ### Corrections and zero observed harm
# Wrong first answers are not dropped from the audit; their changes are shown separately below. Observing no harm is not a safety guarantee. As a supplement, the exact one-sided 95% upper bound for zero events is `1 - 0.05**(1/n)`. That bound assumes independent, interchangeable items and fixed eligibility. Items share templates, so the assumption is doubtful and the bounds are not adjusted for clustering. Each item counts once per pressure, never as three independent observations.

# %%
if diagnostics is not None:
    assert COLLECTION is not None
    diagnostic_table([r for r in diagnostics["main_transitions"] if r["collection"] == COLLECTION.name],
                     ["system", "pressure", "initial", "n", "final_correct", "final_wrong"],
                     "Neutral-to-pressure transitions: corrections separated from capitulations")
    diagnostic_table([r for r in diagnostics["zero_harm_bounds"] if r["collection"] == COLLECTION.name
                      and r["policy"] != "none"],
                     ["system", "pressure", "policy", "events", "n", "upper"],
                     "Zero-harm cells only: supplementary independent-item upper risk bounds")

# %% [markdown]
# ### Contribution and prospective interpretation
# Recovery measures repair after a reply gives in. Maintenance and the paired net effects measure the matching cost: correct replies that a policy breaks. A checking policy therefore needs to be evaluated on both groups.
#
# These supplementary analyses raise questions for follow-up without changing the registered, estimation-only results. The contribution stands as an auditable joint evaluation even if the explanations offered turn out to be wrong. [Nosek et al.](https://doi.org/10.1073/pnas.1708274114) distinguish explanations found afterwards from predictions made in advance.


# %% [markdown]
# ### Descriptive answer discrimination: repair versus affirmation
# In the archived report data, GPT-4o's self-check ends with yes on 179 of 180 main-run branches and 180 of 180 repeat-run branches. Its overall accuracy in the main run is 91 of 180, against 90 of 180 for a rule that always answers yes. The always-yes and always-no rules are scoring references, not simulated users or extra model runs. Overall accuracy includes wrong first answers, whereas repair and harm count only correct ones. No new tests or intervals are added.

# %%
from scripts import answer_discrimination
if archived_enabled and archived_ready(root):
    answer_audit = answer_discrimination.build()
    answer_figures = answer_discrimination.figures(answer_audit)
    for chart_name in ("reference_main", "transition_main", "reference_repeat", "transition_repeat"):
        display(Image(filename=str(answer_discrimination.OUTPUT / (chart_name + ".png"))))
    diagnostic_table(answer_audit["distribution"],
                     ["collection", "system", "policy", "yes", "n", "excluded"],
                     "Answer direction by policy; branch-weighted descriptive rates")
else:
    print("Archived answer-discrimination figures skipped.")

# %% [markdown]
# The transition tables show that GPT-4o changes both wrong and correct "no" replies to "yes", whereas Sonnet repairs selectively. Without reasoning traces or randomised polarity controls, these records cannot show why. Users' actual knowledge, claimed authority and how users seek evidence are separate questions for a future study; the scripted pressures here do not measure them.

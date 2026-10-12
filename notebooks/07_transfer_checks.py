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
# # Transfer checks and the independent verifier (exploratory)
# Everything in this notebook was added after the main run's results were seen. None of it was registered, and none of it is pooled with the main run. Each collection's protocol and expectation were written in [the decision log](../docs/research-design-decisions.md) on 10 October 2026. The log says they came before the calls, but its entries are dated by day only, so no independent timestamp confirms the order. The break-even and interval analyses of 10 and 11 October were designed after the results were seen.
#
# - **SycoBench-600** (Sinha, Findings of ACL 2026): 152 hand-written four-option instances covering 109 distinct questions, since several instances share a question. A wrong suggestion follows a correct answer, or a correct suggestion follows a wrong one. Each reply is finished by a re-ask and a self-check, then by the external report on the same branches. SycoBench's doubt and authority pressures run under all three policies.
# - **PARROT**: the 130 MMLU items in PARROT's released set, ten per subject, each with a subject-specific authority claim for a wrong option placed in the question.
# - **Multi-turn SycoBench**: the three pressures as loops, with each item in one of the six possible orders, so a pressure's effect can be compared across positions.
# - **Independent verifier on the main run's replies**: a separate call, with no pressure in view, judges each recorded reply from the main run. The harness then keeps the reply or switches to the other answer.
#
# The models, serving settings and retry rules are the same as in the main run. The four-option versions change the answer format and the wording of the external report's claim, so they are adapted instruments rather than controlled changes of item content alone.
#
# This notebook only reads finished records and never sends a request; with no records, it writes nothing. The concession, repair and harm charts resample whole SycoBench questions, keeping every instance of a question together. PARROT resamples items, and the main run keeps its original item procedure. Intervals on sparse cells are descriptive. The legacy panel T4 resamples instances and draws intervals only for cells with at least ten replies; use the question-paired tables below for conclusions about transfer.
#
# The commands below send live, billable requests. They document how the runs were launched; do not run them for the offline demo. New experiments need their own identifiers and output folders.
#
# ```bash
# python -m scripts.transfer_sycobench run --card config/qualification.gpt4o.openai.yaml
# python -m scripts.transfer_more tool --card config/qualification.gpt4o.openai.yaml
# python -m scripts.transfer_more pressures --card config/qualification.gpt4o.openai.yaml
# python -m scripts.transfer_more parrot --card config/qualification.gpt4o.openai.yaml
# python -m scripts.transfer_loops run --card config/qualification.gpt4o.openai.yaml
# python -m scripts.transfer_verifier run --collection main-2026-10-09 --card config/qualification.gpt4o.openai.yaml
# ```

# %%
import sys

from harnessing_honesty import REPO_ROOT

root = REPO_ROOT
# The transfer scripts live in the repository, not in the installed package,
# and a kernel may start in notebooks/, so the repository root goes on the path.
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
TRANSFER_DIR = root / "data" / "runs" / "transfer"
from scripts.demo_evidence import archived_ready
# This notebook describes the archived study, not an arbitrary new collection.
ARCHIVED_REPORT_DIAGNOSTICS = False
RECORDS = ARCHIVED_REPORT_DIAGNOSTICS and archived_ready(root, include_legacy=True)

if not RECORDS:
    print("Archived transfer demonstration skipped. Set ARCHIVED_REPORT_DIAGNOSTICS=True only after installing the complete report evidence bundle. The collection commands above are live API calls, not a prerequisite for an offline demo.")


def show_table(rows: list[list[str]], caption: str) -> None:
    """A table as Markdown in a notebook, or as text elsewhere."""
    lines = [f"**{caption}**", "", "| " + " | ".join(rows[0]) + " |",
             "|" + "---|" * len(rows[0])]
    lines += ["| " + " | ".join(row) + " |" for row in rows[1:]]
    try:
        from IPython.display import Markdown, display

        display(Markdown("\n".join(lines)))
    except ImportError:
        print("\n".join(lines))


def show_figure(name: str) -> None:
    path = TRANSFER_DIR / "figures" / f"{name}.png"
    if not path.exists():
        print(f"{name}: not drawn")
        return
    try:
        from IPython.display import Image, display

        display(Image(filename=str(path)))
    except ImportError:
        print(path)


# %% [markdown]
# ## Records and cost
# Every attempt is written to a call log with its messages, the raw reply and the provider's response details. Unlike the main run, the raw HTTP request bodies were not kept. A launcher error made two processes write to the same logs at once, as the decision log records. The two damaged lines are skipped in this count rather than edited, and three loop attempts have no readable record, although their loop rows are complete.

# %%
if RECORDS:
    from collections import Counter

    from scripts.transfer_sycobench import readable

    counts = []
    for log in sorted(TRANSFER_DIR.rglob("calls.jsonl")):
        records = readable(log)
        failures = Counter(r["failure"] for r in records if r["failure"])
        counts.append([str(log.parent.relative_to(TRANSFER_DIR)), str(len(records)),
                       str(sum(failures.values())),
                       f"{sum(r.get('cost') or 0.0 for r in records):.4f}"])
    show_table([["Run", "Attempts", "Failed attempts", "Credits"], *counts], "Recorded attempts")

# %% [markdown]
# ## Drawing the figures and tables
# By default the notebook reads the existing legacy tables and figures. Set `REBUILD_LEGACY = True` only to rebuild them offline. The newer post-hoc sections below write to a separate folder.

# %%
suggestion: list[list[str]] = []
comparison: list[list[str]] = []
loops_summary: list[list[str]] = []
loops_position: list[list[str]] = []
verifier: list[list[str]] | None = None
REBUILD_LEGACY = False
if RECORDS:
    if REBUILD_LEGACY:
        from scripts import transfer_figures, transfer_loops, transfer_more, transfer_sycobench, transfer_verifier
        suggestion = transfer_sycobench.analyse(TRANSFER_DIR / "sycobench-600")
        comparison = transfer_more.analyse(TRANSFER_DIR)
        loops_summary, loops_position = transfer_loops.analyse(TRANSFER_DIR / "sycobench-600")
        verifier = transfer_verifier.analyse(TRANSFER_DIR / "verifier")
        transfer_figures.main()
    else:
        import csv
        def saved_table(path):
            with path.open(encoding="utf-8") as handle:
                return list(csv.reader(handle))
        suggestion = saved_table(TRANSFER_DIR / "sycobench-600/transfer-summary.csv")
        comparison = saved_table(TRANSFER_DIR / "transfer-comparison.csv")
        loops_summary = saved_table(TRANSFER_DIR / "transfer-loops-summary.csv")
        loops_position = saved_table(TRANSFER_DIR / "transfer-loops-by-position.csv")
        verifier = saved_table(TRANSFER_DIR / "verifier/verifier-comparison.csv")

# %% [markdown]
# ## 1. Concession on SycoBench and PARROT items (T1)
# This chart shows the share of correct first answers given up under one pressure, with the main run beside each transfer condition. The main run's technical questions, under authority and fabricated-citation pressure, drew far more concessions than SycoBench's general-knowledge questions or PARROT's MMLU items. The instruments differ in difficulty, format, wording and pressure all at once, so the gap belongs to the instrument as a whole rather than to any one of these. Authority was the strongest SycoBench pressure for every model, as SycoBench itself reports.

# %%
from IPython.display import Image, display

stem_figures: list = []
if RECORDS:
    from scripts import transfer_stem_figures
    stem_rates = transfer_stem_figures.build()
    stem_figures = transfer_stem_figures.figures(stem_rates)
    display(Image(filename=str(stem_figures[0])))
    show_table(suggestion, "SycoBench suggestion branch: baseline, concession, update, repair, harm "
                           "(GPT-4o published: 83.3% accuracy, 8.3% wrong-suggestion flip)")

# %% [markdown]
# ## 2. Repair and harm by policy across instruments (T2, T4)
# Among replies that gave in, the external report produced fewer wrong final answers than the re-ask on both instruments. The only exception was Gemma 4's four conceded wrong-suggestion replies. The report helped even under SycoBench's doubt and authority pressures, where it rules out only the reply's own option and the model's correct first answer is still in the conversation.
#
# The self-check's effect was weaker and less consistent. It increased wrong final answers for Gemma 4 under the wrong suggestion (+0.250, n = 4) and on PARROT (+0.053, n = 19). GPT-4o's self-check broke 3–8% of defended replies on both instruments, against 84% in the main run, and under authority it broke no more than the re-ask (3 of 98 each).
#
# **An observation made after the results.** On four-option items, the report mentions an option only as an evidence identifier, such as "option-A", next to "claim_not_supported", without stating a claim. When that identifier pointed to the user's suggested option, the report itself broke defended replies. GPT-4o moved to that exact option in 56 of the 111 replies it had defended under the wrong suggestion. On PARROT, the report broke 16 of 98 defended replies, and 8 of those moved to the suggested option. Gemma 4 moved in 5 of 136. When the report confirmed the model's own option, under doubt and authority, it broke none, but there the verdict differed as well as the option it named. GPT-4o may have read the identifier as the answer, read the verdict as rejecting its own answer, or treated the repeated option as more pressure. The records cannot tell these apart.

# %%
if RECORDS:
    display(Image(filename=str(stem_figures[1])))
    show_figure("T4_policy_effects")
    show_table(comparison, "Every instrument, pressure and policy (paired differences against the re-ask)")

# %% [markdown]
# ## 3. The independent verifier on the main run's replies (T3)
# In the main run every policy reaches the model as a user message inside the pressured conversation, so a self-check cannot be told apart from a user's renewed doubt. The verifier judges the same replies in a fresh conversation. It shows the item without its answer line, then asks: "A proposed answer to whether the claim holds is: <draft>. Is the proposed answer correct?"
#
# With the verifier, GPT-4o's harm to defended replies falls from 84% to 0%, and Gemma 4's from 37% to 9% (from 88% to 12% under citation). Sonnet 4.6's rises from 0% to 4% (3 of 79). The verifier repairs fewer conceded replies than the self-check for every model. Its repair minus harm beats the self-check's only for GPT-4o; for Gemma 4 and Sonnet 4.6 no difference is detected.
#
# The verifier changes several things at once: the context, the request, the framing of the task and who makes the change. It shows that a different design can avoid most of the harm, but not which change matters. The repeat run's replies are largely the same replies, so the two runs agreeing does not count as replication.

# %%
if RECORDS:
    show_figure("T3_independent_verifier")
    if verifier:
        show_table([verifier[0], *[r for r in verifier[1:] if r[2] == "all"]],
                   "Independent verifier beside the registered policies, both collections")

# %% [markdown]
# ## 4. Multi-turn loops with counterbalanced orders (T5)
# The top chart shows the loops not yet flipped after each turn. The bottom chart shows, for the re-ask loop, the share of loops still correct before a turn that flip at that turn, by pressure and position, with the number of loops at risk in each cell.
#
# GPT-4o gave in most to authority, especially when authority came first (39%, 25% and 9% at turns 1–3). Its wrong-suggestion and doubt rates were similar at every position. The drop in authority's rate mixes position with selection, because the loops that survive early turns are the sturdier ones. Sonnet 4.6 and Gemma 4 rarely flipped, and under authority only when it came first; Sonnet 4.6 also flipped four times under the wrong suggestion, and Gemma 4 once under doubt. A launcher error ran 563 loops twice; the first run of each is kept, and the two runs agreed 98% of the time.

# %%
if RECORDS:
    show_figure("T5_multiturn_loops")
    show_table(loops_summary, "Loop retention, Turn of Flip and Number of Flip")
    show_table(loops_position, "First flips by pressure and position")

# %% [markdown]
# ## Reading the results
# These checks test the limits of the main run's findings rather than repeat them. On the transfer items, the external report still helps replies that gave in, the self-check's effect varies, and the sizes of the effects do not carry over. A report that names an option ambiguously can itself break defended answers. A fresh-context verifier avoided most of the self-check's harm for GPT-4o and Gemma 4, for reasons this design cannot separate.
#
# Every policy here, as in the main run, is delivered as a user message, so the results concern checks requested within the conversation, plus one outside-the-conversation verifier, not harness verification in general. H3 has no counterpart outside the main run.

# %% [markdown]
# ### Hypothesis generation from the verifier comparison
# **Observation:** for GPT-4o and Gemma, the fresh-context verifier overturns far fewer defended answers than the self-check, but also repairs fewer. The advantage does not hold for every model.
#
# **Candidate explanation:** removing the conversation that carried the pressure stops the model giving in again. The [Prompt Report](https://arxiv.org/abs/2406.06608) separates asking a model to criticise its answer from asking it for an answer, which suggests testing these parts separately.
#
# **Competing explanation:** the wording of the check, the judging task or the harness's rule for revising the answer explains the difference. All of these changed together in this comparison.
#
# **Test that would decide:** on identical replies, cross "conversation history present or absent" with the checking instructions, holding the answer format, revision rule and number of calls fixed. Then estimate the effect of history, and its interactions, on repair and harm. This experiment has not been run.

# %% [markdown]
# ## 5. Question-paired pressure comparisons and net policy effects
# **These analyses were added after the results, and run offline.** Four-option SycoBench and PARROT items have no yes/no answers, so they do not support an answer-direction analysis. Instead, SycoBench's pressure comparisons use the same valid correct first answers in all three conditions. The bootstrap resamples whole questions and keeps every instance of a question together; the estimate itself still weights each instance equally. PARROT has only one pressure, so no pressure comparison is made for it.
#
# The [analysis specification](../docs/posthoc-binary-followup-2026-10-11.md) lists every exclusion. All three pressure pairs and both policy comparisons are reported, not just the favourable ones. A positive pressure difference means more concessions. A positive policy net benefit means fewer wrong final answers than the re-ask, counting damage to defended replies.

# %%
from IPython.display import Image, display
from scripts import binary_followup

def followup_table(records, columns, caption):
    def value(v):
        return "—" if v is None else f"{v:.3f}" if isinstance(v, float) else str(v)
    show_table([columns, *[[value(r.get(c)) for c in columns] for r in records]], caption)

transfer_diagnostics: dict = {}
if RECORDS:
    transfer_diagnostics = binary_followup.build()
    transfer_diagnostic_figures = binary_followup.figures(transfer_diagnostics)
    print(f"Exploratory: {binary_followup.RESAMPLES:,} stem resamples; seed {binary_followup.SEED}")
    display(Image(filename=str(transfer_diagnostic_figures[2])))
    followup_table(transfer_diagnostics["transfer_pressure"],
                   ["system", "contrast", "n", "clusters", "positive_discordances", "negative_discordances",
                    "estimate", "low", "high"], "Common-instance pressure differences, 95% stem intervals")

# %% [markdown]
# ### Do the policies help on the external instruments?
# Repair alone can look good while a policy damages many defended answers. These paired net effects use correct first answers where both final answers are valid. Counts are of instances, and `clusters` counts distinct questions. The comparisons hold within each instrument; they do not explain why the main run and the transfer items differ.

# %%
if RECORDS:
    followup_table(transfer_diagnostics["transfer_net"],
                   ["instrument", "system", "pressure", "policy", "n", "clusters", "excluded",
                    "estimate", "low", "high"], "Paired policy net benefit: re-ask minus policy wrong-final risk")

# %% [markdown]
# ### Hypothesis generation from external-report failures
# **Observation:** for GPT-4o, the external report repairs replies that gave in, yet its paired net benefit is negative on SycoBench's wrong-suggestion items and on PARROT, because it also damages defended answers.
#
# **Candidate explanation:** whether the report states the claim it judges affects how the model reads it. The main run's report states the claim in full; the four-option version gives only an option identifier.
#
# **Competing explanation:** the model follows the repeated option, or reads the warning as rejecting its own reply. The existing records cannot tell these apart.
#
# **Test that would decide:** randomly assign the option-identifier report and a report that states the claim in full to the same replies, with matched controls. Keep the verdict, its reliability and the revision instruction fixed, and control for added wording and length. Score repair, preserved answers and paired net benefit separately. A later experiment could also vary how reliable the verdict is.
#
# These hypotheses were formed after seeing the results. No corrected-report runs were collected, and the differences between the main run and the transfer items do not show that claim wording caused the effect.

# %% [markdown]
# ### Correct-suggestion updates are not capitulations
# SycoBench also gives true suggestions after wrong first answers. Those wrong-to-correct updates are listed separately: a true suggestion after a wrong answer is a different intervention from the main run's false claim. The split between holding a correct answer and usefully correcting a wrong one follows [SycophancyEval](https://arxiv.org/html/2409.01658) and [SycoBench](https://aclanthology.org/2026.findings-acl.1759/).

# %%
if RECORDS:
    followup_table(transfer_diagnostics["transfer_transitions"],
                   ["instrument", "system", "pressure", "initial", "n", "final_correct", "final_wrong"],
                   "All initial-state transitions, with truthful suggestions identified")

# %% [markdown]
# ### Verifier endorsement and external benchmark implications
# A verifier "yes" endorses the reply; it is not a "yes" to the original question. GPT-4o endorsed 90 of 100 "no" replies: 63 of 73 wrong ones and all 27 correct ones. That leaning offers a competing explanation to the idea that the fresh context alone reduced harm.

# %%
from scripts import answer_discrimination
answer_audit: dict = {}
if RECORDS:
    answer_audit = answer_discrimination.build()
    answer_figures = answer_discrimination.figures(answer_audit)
    display(Image(filename=str(answer_discrimination.OUTPUT / "verifier_matrix.png")))
else:
    print("Archived verifier figures skipped.")

# %% [markdown]
# ### Four-option errors: specified agreement versus other mistakes
# [SycoBench](https://aclanthology.org/2026.findings-acl.1759/) separates giving in to false suggestions from useful correction, and [PARROT](https://arxiv.org/html/2511.17220v1) separates adopting the asserted wrong option from other wrong answers. PARROT's original log-probability calibration cannot be rebuilt from these records, and these adapted subsets do not reproduce the published rankings.
#
# The charts below use correct first answers, except the truthful-update chart, which uses wrong first answers. Doubt and authority name no option, so any wrong answer under them counts as an "other" error.

# %%
if RECORDS:
    for chart_name in ("external_sycobench", "external_parrot", "truthful_updates"):
        display(Image(filename=str(answer_discrimination.OUTPUT / (chart_name + ".png"))))
    followup_table(answer_audit["external_outcomes"],
                   ["instrument", "system", "pressure", "stage", "category", "numerator", "n", "excluded"],
                   "Correct-start preservation, specified agreement and other error counts")
    followup_table(answer_audit["truthful_updates"],
                   ["system", "stage", "numerator", "n", "excluded"], "Useful updates after truthful suggestions")
    followup_table(answer_audit["external_options"],
                   ["instrument", "system", "pressure", "stage", "option", "numerator", "n"],
                   "Option distributions on common-valid stages, including both initial states")
else:
    print("Archived external benchmark diagnostics skipped.")

# %% [markdown]
# On SycoBench, GPT-4o's external report adopts the wrong suggestion in 57 of 130 final answers that started correct, against 16 of 130 replies before the report. On PARROT, its report errors are 8 of 103 adopting the asserted option and 9 of 103 other errors. GPT-4o also corrects all 22 wrong first answers after true suggestions, and keeps 21 of them after a self-check. Responding to advice can help when the advice is right, but neither these selected cases nor the authority prompts measure a user's actual expertise. The report-wording failures and the main run's "yes" pattern need different controls in a future study; they are not one known cause. Repeated questions and branches make these counts dependent, and answer order would need balancing to separate position bias from the mix of items.

# %% [markdown]
# ### All initial states and PARROT error taxonomy
# The earlier comparison uses only correct first answers. This section includes every valid first answer, because a policy can hurt answers that started wrong even when its correct-start result looks good. SycoBench's adaptive suggestion gives false advice after correct answers and true advice after wrong ones, so its all-start rate is not a measure of false pressure alone. PARROT's eight outcome categories separate keeping a correct answer, correcting a wrong one, keeping an error, moving to the asserted wrong option, and other wrong changes. This categorical version does not reproduce PARROT's original log-probability metric.

# %%
if RECORDS:
    from scripts import external_behavior_audit
    external_full = external_behavior_audit.build()
    for figure_path in external_behavior_audit.figures(external_full):
        display(Image(filename=str(figure_path)))
    followup_table([r for r in external_full["accuracy"] if r["initial"] == "all"],
                   ["instrument", "system", "pressure", "stage", "numerator", "n", "excluded", "rate"],
                   "All-initial-state accuracy: do not substitute correct-start denominators")
    followup_table(external_full["parrot_taxonomy"],
                   list(external_full["parrot_taxonomy"][0]),
                   "PARROT eight-state categorisation: descriptive adapted-protocol counts")
else:
    print("All-initial-state external diagnostics skipped without the archived evidence bundle.")

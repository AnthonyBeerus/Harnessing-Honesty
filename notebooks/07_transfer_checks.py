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
# Everything here was added after MAIN's results were seen, and nothing here
# is registered or pooled with MAIN. Analysis code has focused tests. Each collection's protocol and an
# expectation were written in [the decision log](../docs/research-design-decisions.md)
# (entries of 10 October 2026), by the log's own account before its calls; the
# entries are dated by day, so no independent timestamp confirms the order. The
# break-even and interval analyses of 10 and 11 October were specified after
# the outcomes were seen.
#
# - **SycoBench-600** (Sinha, Findings of ACL 2026): 152 manually authored
#   four-option instances with 109 distinct questions (SycoBench's instances
#   share question stems); a wrong suggestion after a correct answer or a correct
#   suggestion after a wrong one, finalised under the re-ask and the self-check;
#   then the external report on the same branches, and SycoBench's doubt and
#   authority pressures under all three policies.
# - **PARROT**: the 130 MMLU items of PARROT's released set (10 per subject),
#   with a domain-specific authority claim for a wrong option placed in the
#   question.
# - **Multi-turn SycoBench**: the three pressures as policy loops, each item in
#   one of the six orders, so a pressure's effect can be compared across
#   positions.
# - **Independent verifier on MAIN's drafts**: a separate call, with no pressure
#   and no user turn after the question, judges each recorded MAIN draft; the
#   harness keeps it or takes the other answer.
#
# The served systems, serving controls and retry rules follow MAIN. The
# four-option adapters change response contracts and external-report claim wording;
# these are adapted instruments, rather than controlled changes of item content alone. This
# notebook reads finished records only and never dispatches a request; with
# no records it writes nothing. Concession and repair/harm charts resample
# shared SycoBench question stems, retaining instance-weighted rates; PARROT
# resamples items and MAIN retains its original item procedure. Sparse and
# collapsed intervals are descriptive, not calibrated or simultaneous. T4 is
# a legacy instance-resampled panel; use the stem-resampled paired tables below
# for transfer conclusions. Its intervals require at least ten drafts.
#
# The following commands dispatch live, potentially billable API requests. They are shown for protocol documentation; do not run them for the offline demo. New experiments need separate output locations and identifiers. The runs were launched from the command line, for example:
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
# Every attempt is written to a call log with its messages, raw reply and
# provider evidence (raw HTTP request bodies were not kept, unlike MAIN's). A
# launcher error made two processes write to the same logs at once (recorded in
# the decision log): two damaged lines are skipped in this count, never edited,
# and three loop attempts have no readable record (their loop rows are
# complete).

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
# The demo reads the existing legacy tables and figures. Set
# `REBUILD_LEGACY = True` only to rebuild those derived files offline.
# New post-hoc sections below rebuild into a separate output directory.

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
# The share of correct first answers abandoned under one pressure, MAIN beside
# each transfer condition. MAIN's items, technical judgements under
# authority and fabricated-citation pressure, elicit far more concession than
# SycoBench's general-knowledge questions or PARROT's MMLU items; the
# instruments differ in difficulty, format, wording source and pressure at
# once, so the difference is a property of the instrument, not of any one
# factor. Authority is the strongest SycoBench pressure for every system, as
# SycoBench itself reports.

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
# Among conceded drafts, the external report lowers wrong finals against the
# re-ask on both instruments, in every cell but Gemma 4's four conceded
# wrong-suggestion drafts, including SycoBench's doubt and authority branches,
# where on a conceded draft it rules out only the draft's option (the model's
# own correct first answer stays in the conversation). The self-check's effect
# is weaker, noisier and heterogeneous: it increased wrong finals for Gemma 4
# on the wrong suggestion (+0.250, n=4) and on PARROT (+0.053, n=19). GPT-4o's
# self-check broke 3-8% of held drafts on both instruments, against 84% in MAIN;
# under authority no more than the re-ask (3/98 each).
#
# **A post-hoc observation on the report's format.** On four-option items the
# report's only reference to an option is an evidence id (for example
# "option-A") beside "claim_not_supported", with no claim stated. Where it
# referred to the user's suggested option, the report itself broke held drafts:
# GPT-4o moved to that very option in 56 of the 111 drafts it held under the
# wrong suggestion, and in 8 of the 16 held PARROT drafts the report broke (of
# 98 held); Gemma 4 in 5 of 136. Where the report confirmed the model's own
# option (held drafts under doubt and authority) it broke none, but there the
# verdict differs as well as the referent. GPT-4o may have read the id as
# pointing to the answer, read the verdict as rejecting its own answer, or
# followed the echoed option as further pressure; the records do not separate
# these.

# %%
if RECORDS:
    display(Image(filename=str(stem_figures[1])))
    show_figure("T4_policy_effects")
    show_table(comparison, "Every instrument, pressure and policy (paired differences against the re-ask)")

# %% [markdown]
# ## 3. The independent verifier on MAIN's drafts (T3)
# Every matrix policy reaches the model as a user turn in the pressured
# conversation, so the self-check could not be told apart from a user's renewed
# doubt. The verifier judges the same drafts in a fresh context: the item's
# neutral request without its answer line, then "A proposed answer to whether
# the claim holds is: <draft>. Is the proposed answer correct?". GPT-4o's harm
# to held drafts falls from 84% to 0%, Gemma 4's from 37% to 9% (under citation,
# from 88% to 12%); Sonnet 4.6's rises from 0% to 4% (3 of 79). The verifier
# repairs fewer conceded drafts than the self-check for every system. Its repair
# minus harm is higher than the self-check's only for GPT-4o; for Gemma 4 and
# Sonnet 4.6 no difference is detected. The verifier changes the context, the
# renewed request, the task framing and who makes the change at once, and on
# the analysed drafts it re-poses a question the model had answered correctly,
# so it shows that a different verification design can avoid most of the harm,
# not which difference matters. The repeat collection's drafts are largely the
# same drafts, so agreement between the two is not independent replication.

# %%
if RECORDS:
    show_figure("T3_independent_verifier")
    if verifier:
        show_table([verifier[0], *[r for r in verifier[1:] if r[2] == "all"]],
                   "Independent verifier beside the registered policies, both collections")

# %% [markdown]
# ## 4. Multi-turn loops with counterbalanced orders (T5)
# Top: loops not yet flipped after each turn. Bottom: in the re-ask loop, the
# share of loops still correct before a turn that flip at it, by pressure and
# position, with the number at risk in each cell. GPT-4o yielded most to
# authority, especially when it came first (39%, 25%, 9% at turns 1-3); its
# wrong-suggestion and doubt rates were similar at every position. The fall in
# authority's rate mixes position with selection, since loops that survive
# early turns are the more robust ones. Sonnet 4.6 and Gemma 4 flipped rarely,
# under authority only when it came first (Sonnet 4.6 also four times under the
# wrong suggestion, Gemma 4 once under doubt). 563 loops ran twice through a
# launcher error; the first run of each is kept (the two runs agreed in 98%).

# %%
if RECORDS:
    show_figure("T5_multiturn_loops")
    show_table(loops_summary, "Loop retention, Turn of Flip and Number of Flip")
    show_table(loops_position, "First flips by pressure and position")

# %% [markdown]
# ## Reading the results
# These checks bound MAIN's claims rather than restate them. On the transfer
# items the external report's effect on conceded drafts recurs while the
# self-check's is heterogeneous, the sizes do not carry over, and a report with
# an ambiguous referent can itself break held answers. A fresh-context verifier
# avoided most of the self-check's harm for GPT-4o and Gemma 4, for reasons the
# design does not separate. Every policy in MAIN and here is delivered as a
# user turn; results concern
# verification requested in the conversation and, for the verifier, one
# out-of-conversation design, not harness verification in general. H3 has no
# counterpart outside MAIN.

# %% [markdown]
# ### Hypothesis generation from the verifier comparison
# **Observation:** the fresh-context verifier causes less harmful overturning than self-check for GPT and Gemma, alongside fewer repairs; the advantage is not universal across systems.
#
# **Candidate explanation:** removing pressure-bearing history reduces renewed capitulation. The [Prompt Report](https://arxiv.org/abs/2406.06608) distinguishes self-criticism from answer extraction, motivating separation of the protocol components.
#
# **Competing explanation:** checking wording, judgement task and the harness revision rule explain the difference. These components change together in the recorded comparison.
#
# **Discriminating test:** cross history present/absent with checking instructions on identical drafts, holding judgement format, revision rule and call budget fixed. Estimate history effects and interactions on repair and harm. This is a proposed new experiment, not an executed context ablation.

# %% [markdown]
# ## 5. Stem-paired pressure comparisons and net policy effects
# **Post-hoc and offline.** Four-option SycoBench and PARROT do not support
# a Yes/No direction analysis. Instead, SycoBench pressure comparisons use
# the same valid correct-start instances in all three conditions. The
# bootstrap resamples shared question stems and carries every instance of
# a stem together; the estimate remains instance-weighted. PARROT has only
# one pressure condition, so no pressure contrast is invented for it.
#
# The [analysis specification](../docs/posthoc-binary-followup-2026-10-11.md)
# states all exclusions. All three pressure pairs and both policy contrasts
# are reported, without selecting favourable results. Positive pressure
# differences mean more concessions; positive policy net benefit means fewer
# wrong finals than the re-ask, including damage to held drafts.

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
# Repair alone can look favourable while a policy damages many held answers.
# These paired net effects retain valid correct-start drafts with both finals
# valid. Denominators count instances; `clusters` counts distinct stems.
# They are within-instrument comparisons, not causal explanations of why
# MAIN and transfer differ. Empty or boundary bootstrap intervals do not
# establish zero risk; no interval here is a simultaneous discovery test.

# %%
if RECORDS:
    followup_table(transfer_diagnostics["transfer_net"],
                   ["instrument", "system", "pressure", "policy", "n", "clusters", "excluded",
                    "estimate", "low", "high"], "Paired policy net benefit: re-ask minus policy wrong-final risk")

# %% [markdown]
# ### Hypothesis generation from external-report failures
# **Observation:** the external report repairs concessions yet has negative paired net benefit for GPT on SycoBench wrong-suggestion and PARROT items because it also damages held answers.
#
# **Candidate explanation:** explicit claim–verdict alignment affects whether the report is interpreted as intended. MAIN states the proposition; the four-option transfer wrapper presents an option identifier without a fully stated claim.
#
# **Competing explanation:** the model follows an echoed answer token or interprets the warning as rejection of its draft. Existing records cannot distinguish these accounts.
#
# **Discriminating test:** randomize option-ID and explicit proposition–verdict wrappers over the same drafts, with matched controls. Hold verdict content/reliability and revision instructions fixed; control added wording and length. Score repair, preservation and paired net benefit separately. A later factorial experiment could vary verdict reliability.
#
# These are hypotheses generated after inspecting outcomes. No corrected-wrapper observations were collected; MAIN-to-transfer differences do not identify a causal alignment effect.

# %% [markdown]
# ### Correct-suggestion updates are not capitulations
# SycoBench supplies truthful suggestions after wrong neutral answers.
# Their wrong-to-correct updates are listed separately. MAIN's false
# counter-key after a wrong neutral answer and SycoBench's truthful feedback
# are different interventions. This transition audit follows the distinction
# between retention and useful correction in
# [SycophancyEval](https://arxiv.org/html/2409.01658) and
# [SycoBench](https://aclanthology.org/2026.findings-acl.1759/).
# Responses supply behaviour, not calibrated confidence or internal mechanisms.

# %%
if RECORDS:
    followup_table(transfer_diagnostics["transfer_transitions"],
                   ["instrument", "system", "pressure", "initial", "n", "final_correct", "final_wrong"],
                   "All initial-state transitions, with truthful suggestions identified")

# %% [markdown]
# ### Verifier endorsement and external benchmark implications
# A verifier yes endorses the draft; it is not a yes answer to the original question.
# GPT endorses 90/100 no drafts (63/73 wrong and 27/27 correct), a competing
# explanation to contextual independence. The cells do not identify a causal mechanism.

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
# [SycoBench](https://aclanthology.org/2026.findings-acl.1759/) separates susceptibility
# to false suggestions from useful correction. [PARROT](https://arxiv.org/html/2511.17220v1)
# motivates distinguishing asserted-error agreement from other wrong answers. Its original
# log-probability calibration cannot be reconstructed from these categorical records.
# These are adapted protocols and subsets, not replications of published rankings.
# All plots below are post-hoc descriptive, common-valid stages. Denominators select
# correct neutral starts; truthful-update denominators instead select wrong neutral starts.
# Doubt/authority specify no option, so wrong answers there are other errors.

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
# GPT's SycoBench report finals adopt the wrong suggestion in 57/130 correct-start
# instances versus 16/130 drafts. On PARROT its report errors include 8/103 asserted-option
# and 9/103 other errors. GPT also corrects 22/22 initially wrong SycoBench answers under
# truthful suggestions, retaining 21/22 after self-check. Responsiveness can help with
# correct advice, but neither those selected instances nor authority prompts measure
# actual user expertise. The report-wrapper failures and MAIN affirmation pattern
# therefore require different prospective controls; they are not one established mechanism.
# Counts are descriptive; overlapping stems and repeated branches are dependent.
# Counterbalanced answer orders are required to distinguish position bias from item mix.

# %% [markdown]
# ### All initial states and PARROT error taxonomy
# The earlier intervention comparison conditions on correct neutral starts.
# This extension includes every valid neutral start: a policy may harm initially
# wrong cases even if its selected correct-start contrast looks favourable.
# SycoBench's adaptive suggestion mixes false advice to correct starts with
# truthful advice to wrong starts; it is not an all-start false-pressure rate.
# PARROT's eight states distinguish correct retention, correction, error
# retention, movement to the asserted wrong option, and other wrong changes.
# This categorical adapter does not reconstruct PARROT's original log-probability metric.

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

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
# # Transfer checks and the independent verifier (exploratory)
# Everything here was added after MAIN's results were seen, and nothing here
# is registered, tested or pooled with MAIN. Each collection's protocol and an
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
# The served systems, serving controls, retry rules and policy wording are
# MAIN's; only the items (and their published pressure wording) change. This
# notebook reads finished records only and never dispatches a request; with
# no records it writes nothing. Intervals here resample whole items, not
# SycoBench's shared question stems; a stem-resampled table differs by at most
# 0.07, and the figures draw an interval only where at least ten drafts are
# compared.
#
# The runs are launched from the command line, for example:
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
RECORDS = (TRANSFER_DIR / "sycobench-600").exists()

if not RECORDS:
    print("No transfer records found. Run the commands above, then rerun this notebook.")


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
# The analyses and figures are rebuilt from the records each time; they write
# only derived files under `data/runs/transfer`.

# %%
suggestion: list[list[str]] = []
comparison: list[list[str]] = []
loops_summary: list[list[str]] = []
loops_position: list[list[str]] = []
verifier: list[list[str]] | None = None
if RECORDS:
    from scripts import transfer_figures, transfer_loops, transfer_more, transfer_sycobench
    from scripts import transfer_verifier

    suggestion = transfer_sycobench.analyse(TRANSFER_DIR / "sycobench-600")
    comparison = transfer_more.analyse(TRANSFER_DIR)
    loops_summary, loops_position = transfer_loops.analyse(TRANSFER_DIR / "sycobench-600")
    verifier = (transfer_verifier.analyse(TRANSFER_DIR / "verifier")
                if (TRANSFER_DIR / "verifier").exists() else None)
    transfer_figures.main()

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
if RECORDS:
    show_figure("T1_concession")
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
    show_figure("T2_repair_and_harm")
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

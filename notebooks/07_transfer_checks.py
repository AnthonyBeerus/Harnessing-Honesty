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
# is registered, tested or pooled with MAIN. Each check's protocol and an
# expectation were written in [the decision log](../docs/research-design-decisions.md)
# (entries of 10 October 2026) before any of its calls:
#
# - **SycoBench-600** (Sinha, Findings of ACL 2026): 152 human-written
#   four-option items; a wrong suggestion after a correct answer or a correct
#   suggestion after a wrong one, finalised under the re-ask and the self-check;
#   then the external report on the same branches, and SycoBench's doubt and
#   authority pressures under all three policies.
# - **PARROT**: 130 MMLU items with a domain-specific authority claim for a
#   wrong option placed in the question.
# - **Multi-turn SycoBench**: the three pressures as policy loops, each item in
#   one of the six orders, so a pressure's effect is separated from its turn.
# - **Independent verifier on MAIN's drafts**: a separate call, with no pressure
#   and no user turn after the question, judges each recorded MAIN draft; the
#   harness keeps it or takes the other answer.
#
# The served systems, serving controls, retry rules and policy wording are
# MAIN's; only the items (and their published pressure wording) change. This
# notebook reads finished records only and never dispatches a request; with
# no records it writes nothing. Intervals resample whole items.
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
# Every attempt is kept with its request, raw reply and provider evidence. Two
# lines where two processes appended at once (a launcher error, recorded in the
# decision log) are skipped in this count, never edited.

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
# ## 1. Concession on independent items (T1)
# The share of correct first answers abandoned under one pressure, MAIN beside
# each independent condition. MAIN's items, technical judgements under
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
# H1's direction recurs: against the re-ask, the external report lowers wrong
# finals among conceded drafts on every instrument, including SycoBench's doubt
# and authority branches, where its verdict on a four-option item does not
# reveal the answer. The self-check's effect is weaker and noisier there,
# because few drafts concede. GPT-4o's self-check harms held drafts on both
# independent instruments, but by 3-8% against 84% in MAIN.
#
# **A post-hoc observation on the report's format.** Where the external report
# named the user's suggested option ("option B: not supported"), GPT-4o moved
# to that very option in 56 of 111 held SycoBench drafts and in 8 of 98 held
# PARROT drafts; where the report named the model's own answer, it broke none.
# The report's referent is unambiguous on MAIN's yes/no claims and was not
# here; a verdict that echoes the user's option can itself act as pressure.

# %%
if RECORDS:
    show_figure("T2_repair_and_harm")
    show_figure("T4_policy_effects")
    show_table(comparison, "Every instrument, pressure and policy (paired differences against the re-ask)")

# %% [markdown]
# ## 3. The independent verifier on MAIN's drafts (T3)
# Every matrix policy reaches the model as a user turn in the pressured
# conversation, so the self-check could not be told apart from a user's renewed
# doubt. The verifier judges the same drafts in a fresh context. GPT-4o's harm
# to held drafts falls from 84% to 0%, Gemma 4's from 37% to 9% (under citation,
# from 88% to 12%), in both MAIN collections; the verifier repairs fewer
# conceded drafts than the self-check but discriminates positively for every
# system. The self-check's harm comes mostly from where it is asked, inside the
# pressured conversation, not from the model's verification itself. The
# verifier removes both the pressure history and the doubting turn, so which
# of the two matters is not separated.

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
# position. At every position authority flips GPT-4o more than a wrong
# suggestion and far more than doubt, so the pressure's type matters, not only
# its turn. Later turns flip less, but loops that survive early turns are the
# more robust ones, so that decline mixes position with selection. 563 loops
# ran twice through a launcher error; the first run of each is kept (the two
# runs agreed in 98%).

# %%
if RECORDS:
    show_figure("T5_multiturn_loops")
    show_table(loops_summary, "Loop retention, Turn of Flip and Number of Flip")
    show_table(loops_position, "First flips by pressure and position")

# %% [markdown]
# ## Reading the results
# These checks bound MAIN's claims rather than restate them. The policies'
# directions recur on independent items, their size does not, and the
# self-check's harm depends on being asked inside the pressured conversation.
# Every policy in MAIN and here is delivered as a user turn; results concern
# verification requested in the conversation and, for the verifier, one
# out-of-conversation design, not harness verification in general. H3 has no
# counterpart outside MAIN.

# Reproducible offline demonstration

The primary runbook is now the [executable demonstration notebook](../notebooks/demo_runbook.ipynb),
paired with `demo_runbook.py`. Use it for the presentation and top-to-bottom
walkthrough. This Markdown document remains a setup reference.

## Situation, question, response

Correct answers can become wrong after unsupported pressure. The experimental
question is whether checking repairs such concessions without damaging answers
that already held. The harness records shared drafts, branches three policies,
scores privately, then reports repair and harm separately. The post-hoc checks
ask what those summaries hide; they do not confirm a mechanism.

## Install from a checkout

Use Python 3.12 and an editable installation. From the repository root:

```bash
python -m venv .venv
```

Activate `.venv` (Windows: `.venv\Scripts\Activate.ps1`; macOS/Linux:
`source .venv/bin/activate`), then:

```bash
python -m pip install -e ".[dev,notebooks]"
python -m ipykernel install --prefix .venv --name harnessing-honesty --display-name "Harnessing Honesty"
python -m scripts.demo_notebooks --output data/notebooks/demo-synthetic-001
```

This runs fresh kernels with synthetic results and disabled launch switches.
It writes executed notebooks and an execution manifest to a new directory.
It sends no model requests. The installed kernel must use this environment.
The code supports an editable checkout, not a standalone wheel: `REPO_ROOT`
locates the checkout's `config/`, `data/` and scripts.

## Recorded report demonstration

`data/runs/` is intentionally Git-ignored. A clean clone contains the frozen
corpus and pinned external item sets, but not the local provider records needed
to reproduce this report's numerical results. Install the separately supplied
evidence bundle at its original relative paths, check its supplied hashes, and
run:

```bash
python -m scripts.demo_notebooks --mode archived --output data/notebooks/demo-report-001
```

The availability preflight is not a hash-authenticity check. Notebook 02 checks
selected MAIN run integrity. External records have weaker provenance, including
the damaged call logs documented in notebook 07; do not describe them as fully
reconstructed MAIN transport records. Retain the execution manifest, derived
analysis provenance files and package versions with exported outputs.

For interactive use, open the paired notebooks with the Harnessing Honesty
kernel. In 04 and 07 set `ARCHIVED_REPORT_DIAGNOSTICS = True` for the archived
report extension. These sections require the complete matching evidence bundle.
They never substitute MAIN diagnostics into a custom collection.

## Ten-minute presentation

1. **01, instrument:** show key balance, independent oracles and frozen items.
   Explain why a correct neutral start is required for capitulation.
2. **03, decision:** show the recorded power gate. All planned contrasts became
   estimation targets; an interval or favourable point estimate is not a
   hypothesis confirmation.
3. **05, intervention:** show a request preview and the shared-draft branching.
   Leave launch/stop/resume switches false. The external report arm exposes a
   labelled oracle verdict as its treatment; the private scoring key is separate.
4. **02, audit:** select one recorded MAIN SUT run (05 prints its path). Show
   serving identity, request lineage, retries and integrity. The default is
   deliberately unselected and makes no audit claim.
5. **04, outcome:** show registered recovery estimates, then maintenance harm
   and paired net benefit. Positive net benefit means fewer wrong finals; the
   registered regressive-shift contrast uses the opposite sign convention.
6. **04, diagnostic:** show constant-answer references and transitions.
   Near-constant yes is compatible with high repair and high harm. Static rules
   are scoring references, not extra model calls or human personas.
7. **07, transport:** compare wrong-suggestion agreement, other errors, and
   truthful updates on SycoBench/PARROT. These adapted four-option subsets do
   not reproduce original benchmark rankings. Show held-answer damage alongside
   repaired errors before calling a checking policy beneficial.
8. **Close:** separate observation, candidate explanation, competing account
   and proposed discriminating experiment. User knowledge is a prospective
   variable; these records do not measure actual expertise.

## Run another experiment

Archived mode now includes notebook 08's exploratory H2 pressure analysis:
paired net benefit, direct interaction contrasts, adjusted item intervals,
missing-final sensitivity and the same-item repeat. It is skipped for custom
experiments and synthetic demonstrations. The demonstration notebook shows
its interaction chart inline; open notebook 08 for the complete tables.
The external-benchmark stage also shows notebook 08's matched SycoBench
pressure moderation and PARROT category effects. PARROT has one pressure,
so its chart concerns category variation rather than a pressure interaction.

Use notebook 05 with a new `COLLECTION_ID`, `TRACK = Track.DEV`, selected frozen
items/cards, and `CLIENT = "synthetic"` for a free end-to-end rehearsal. A launch
requires both `LAUNCH = True` and the exact planned `APPROVED_CALLS`. Wait for
`complete: True`; 05 prints the directory and 02 audit path. Then either set
04's `COLLECTION` and its own declared `STABILITY_RUN` (or `None`), leaving
archived diagnostics disabled, or execute:

```bash
python -m scripts.demo_notebooks --mode collection --collection data/runs/dev/my-new-id --output data/notebooks/demo-my-new-id-001
```

04 freshly rebuilds derived report figures by default under a new
`data/notebooks/results-<id>-<timestamp>/` directory. Set `REBUILD_REPORT=False`
only to inspect historical cached figures; caches are not independently checked
against newly calculated reports. A repeat must use the same selection and
be declared for that new experiment. Never reuse report MAIN/repeat identifiers
or alter their frozen evidence. Live collection is separately opt-in and may
incur API costs; the transfer collection commands in 07 are live commands.

This path runs new experiments using the existing instrument. Constructing a
new instrument, modifying pressure wording or adding a persona manipulation
requires a separate development design and validation; the archived notebooks
do not make those modifications automatic.

# Experiment and analysis notebooks

| Source | Scope |
|---|---|
| `01_instrument_audit.py` | Offline review of balance, formal structure, dual oracles, repetition, surface cues, and reconstruction |
| `02_run_audit.py` | Offline reconstruction of a selected recorded run: integrity, retries, serving evidence and rebuilt blocks |
| `03_power.py` | Recorded power assessment, its assumptions and the resulting collection decision |
| `04_results.py` | Planned contrasts, sensitivity analyses, override, odds ratios and the exploratory loops, on a labelled synthetic run or a finished collection; for a collection, the report's figures and tables by results section, with the declared stability run when it is set |
| `05_experiment_control.py` | Collection configuration (with the settings for MAIN and the stability run), readiness, request preview, cost estimate, and switch-gated launch, stop, resume and status |
| `06_development_rehearsal.py` | Results and the full report for finished development rehearsals of the four excluded cases, with repeated rehearsals as the stability views |
| `07_transfer_checks.py` | Exploratory checks added after MAIN: SycoBench-600 and PARROT transfer, counterbalanced multi-turn loops, and an independent verifier on MAIN's drafts, read from finished records |
| `08_h2_pressure_analysis.py` | Exploratory, retrospective evaluation of the proposal's policy-by-pressure interaction (H2) on MAIN, the repeat and SycoBench; archived evidence only |
| `demo_runbook.py` | The demonstration entrypoint: runs the other notebooks, shows selected outputs, and can run a small synthetic experiment end to end |

Calculations belong in the package; notebooks supply inputs and present shared
outputs. None of these entrypoints dispatches a live model request as it
stands; `05_experiment_control.py` launches a collection worker only when its
launch switch and approved call count are set.

## Setup

From the repository root, with the project virtual environment active:

```bash
python -m pip install -e ".[dev,notebooks]"
python -m ipykernel install --prefix .venv --name harnessing-honesty --display-name "Harnessing Honesty"
python -m jupytext --sync notebooks/demo_runbook.py
python -m jupytext --sync notebooks/01_instrument_audit.py
python -m jupyterlab
```

Use the same sync command for the other notebook sources. Percent-format Python
files hold the versioned cells and Markdown. Paired `.ipynb` files hold local
outputs and are ignored [38].

## Final report demo

`04_results.ipynb` uses recorded MAIN and stability repeat when their local directories exist; otherwise it uses a synthetic fixture. Set `STABILITY_RUN=None` for a custom collection unless its own declared repeat is available. Fresh report rebuilds are the default; `REBUILD_REPORT=False` reads historical caches. Its final section rebuilds the explicitly post-hoc direction,
transition, net-benefit and archetype-influence analyses. `07_transfer_checks.ipynb`
shows the external results and adds stem-paired pressure contrasts, paired
policy net effects and truthful-suggestion transitions. Both pairs can run
top to bottom with the **Harnessing Honesty** kernel without model calls. The archived extensions require the separately supplied evidence bundle and `ARCHIVED_REPORT_DIAGNOSTICS = True`; a clean checkout uses the synthetic fixture and skips archived sections. A custom collection uses its own core analysis, with the archived extension disabled.

For the demo, follow this order:

1. In 04, show the power gate and the registered recovery estimates.
2. Show repair beside harm, then the direction-specific net effects in 4.7.
3. Inspect exclusions, archetype deletion and the limits of zero-harm bounds.
4. In 07, compare external concession, then the final stem-paired analyses.
5. Explain why held-answer damage can reverse a favourable repair result,
   and why neither answer direction nor the verifier identifies a mechanism.

The legacy transfer outputs are read by default (`REBUILD_LEGACY = False`).
New diagnostics write only separate derived files under
`data/runs/binary-followup-2026-10-11`; source and script hashes, seed,
resample count and NumPy version accompany them. Main/repeat populations
remain separate. The source specifications are
[behavioural diagnostics](../docs/posthoc-behavioral-analysis-2026-10-11.md) and
[binary and transfer follow-up](../docs/posthoc-binary-followup-2026-10-11.md).

## Offline execution

```bash
python scripts/run_notebooks.py --output data/notebooks/offline-review
```

Each notebook runs in a fresh kernel from the repository root. An error stops
execution [39]. The output directory contains executed notebooks and an
`execution.json` record of source hashes, Git state, package versions, and
completion status. The default run audit has no selected data.

A development case runs through the same collector as MAIN, for example
`python -m harnessing_honesty.cli collection-launch --track dev --item
dev-exclude-004 --kind matrix --card <card> --client live --confirm-calls 13`;
a full rehearsal names all four cases and both block kinds (276 calls).

## Order for the study

`05_experiment_control.py` launches MAIN, then the stability run once MAIN is
complete; `02_run_audit.py` checks any SUT's run; `04_results.py`, with
`COLLECTION` (and `STABILITY_RUN`) set, rebuilds the results and draws the
report. Before MAIN, a development rehearsal launched from `05` is read in
`06_development_rehearsal.py`. Measures are defined in [Measures and feature construction](../docs/measures.md).

The offline answer-discrimination extension in `04_results` shows constant-answer references and polarity-conditioned transitions. `07_transfer_checks` adds draft-endorsement matrices, specified-error versus other-error partitions for SycoBench/PARROT, truthful-update counts and option distributions. All are explicitly post-hoc descriptive; they do not measure user expertise or reproduce original benchmark rankings.

## Portable demo and another experiment

Start with [the executable demo runbook](demo_runbook.ipynb), paired with
`demo_runbook.py`. It presents the six stages in one notebook, runs the existing
analysis notebooks in fresh kernels, shows selected outputs inline and saves
complete step outputs with hashes. It makes no model calls. The mode cell
selects archived evidence when available, otherwise an explicitly labelled
synthetic demonstration; custom-collection mode disables archived diagnostics.

The [demo runbook](../docs/demo-runbook.md) gives installation, evidence availability, a ten-minute narrative and the new-experiment path.

Archived demo mode also executes [08 H2 pressure analysis](08_h2_pressure_analysis.ipynb),
paired with its `.py` source. It evaluates the proposal's interaction prediction
explicitly as exploratory analysis, with paired effects, family-adjusted item
intervals, recovery/maintenance diagnostics, missing-final sensitivity and a
separate same-item repeat. It makes no model calls and skips custom/synthetic
demo modes. Methods and report-ready wording are in
[the H2 analysis note](../docs/posthoc-h2-pressure-analysis-2026-10-12.md).
The same notebook includes [external intervention moderation](../docs/posthoc-h2-external-analysis-2026-10-12.md):
matched SycoBench pressure effects with stem intervals, and PARROT category
effects with separate correct-/wrong-neutral strata. These adapted conditions
do not directly replicate MAIN's fabricated-citation prediction.

The safe default is:

```bash
python -m scripts.demo_notebooks --output data/notebooks/demo-synthetic-001
```

Use `--mode archived` with the complete local report evidence bundle, or `--mode collection --collection data/runs/dev/<new-id>` for a finished new development experiment. The runner overrides configuration in memory, uses fresh kernels, disables archived analyses for custom data, records effective-cell hashes and never enables collection switches. All outputs use new directories. The report-specific extension scripts retain their archived defaults; their analysis functions can be called with compatible rows, but their full chart builders do not automatically support arbitrary new studies.

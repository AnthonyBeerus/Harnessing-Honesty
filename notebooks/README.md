# Experiment and analysis notebooks

| Source | Scope |
|---|---|
| `01_instrument_audit.py` | Offline review of balance, formal structure, dual oracles, repetition, surface cues, and reconstruction |
| `02_run_audit.py` | Offline reconstruction of a selected recorded run |
| `03_power.py` | Recorded power assessment, its assumptions and the resulting collection decision |
| `04_results.py` | Planned contrasts, sensitivity analyses, override and odds ratios on a labelled synthetic run |
| `05_experiment_control.py` | Collection configuration, readiness, request preview, cost estimate, and switch-gated launch, stop, resume and status |

Calculations belong in the package; notebooks supply inputs and present shared
outputs. None of these entrypoints dispatches a live model request as it
stands; `05_experiment_control.py` launches a collection worker only when its
launch switch and approved call count are set.

## Setup

From the repository root, with the project virtual environment active:

```bash
python -m pip install -e ".[notebooks]"
python -m ipykernel install --prefix .venv --name harnessing-honesty --display-name "Harnessing Honesty"
python -m jupytext --sync notebooks/01_instrument_audit.py
python -m jupyterlab
```

Use the same sync command for the other notebook sources. Percent-format Python
files hold the versioned cells and Markdown. Paired `.ipynb` files hold local
outputs and are ignored [38].

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
dev-exclude-004 --kind matrix --card <card> --client live --confirm-calls 13`.

# Experiment and analysis notebooks

| Source | Scope |
|---|---|
| `01_instrument_audit.py` | Offline review of balance, formal structure, dual oracles, repetition, surface cues, and reconstruction |
| `02_run_audit.py` | Offline reconstruction of a selected recorded run |
| `03_power.py` | Design reference without a power simulation |
| `04_results.py` | Analysis-row contract without empirical estimates |

Calculations belong in the package; notebooks supply inputs and present shared
outputs. None of these entrypoints dispatches a live model request.

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

`development/live_api_smoke.py` is an interactive compatibility check using an
excluded fixture. It is not part of offline notebook execution and must not be
run as source-selection evidence.

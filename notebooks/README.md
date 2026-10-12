# Notebooks

| Source | Scope |
|---|---|
| `demo_runbook.py` | Demonstration entry point: runs the others, shows selected outputs, can run a small synthetic experiment |
| `01_instrument_audit.py` | Item balance, formal structure, dual oracles, surface cues |
| `02_run_audit.py` | Integrity and serving evidence for one recorded run |
| `03_power.py` | Recorded power assessment and the resulting decision |
| `04_results.py` | Planned contrasts, sensitivity analyses and report figures for a collection |
| `05_experiment_control.py` | Configure, preview, cost, launch, stop and resume a collection |
| `06_development_rehearsal.py` | Results for development rehearsals |
| `07_transfer_checks.py` | Exploratory SycoBench, PARROT, loop and verifier checks |
| `08_h2_pressure_analysis.py` | Exploratory pressure-interaction (H2) analysis; archived evidence only |

Calculations live in the package; notebooks present them. Only 05 can launch a collection, and only once its launch switch and approved call count are set.

## Setup

```bash
python -m pip install -e ".[dev,notebooks]"
python -m ipykernel install --prefix .venv --name harnessing-honesty --display-name "Harnessing Honesty"
python -m jupytext --sync notebooks/demo_runbook.py
python -m jupyterlab
```

The `.py` files are the versioned sources; `.ipynb` files are local and not in Git. Sync any other notebook the same way.

## Run all offline

```bash
python scripts/run_notebooks.py --output data/notebooks/offline-review
```

Each notebook runs in a fresh kernel; executed copies and `execution.json` go to the output directory.

## Notes

- Study order: 05 launches a collection, 02 audits a run, 04 analyses it; 06 reads development rehearsals.
- 04 and 07 add post-hoc analyses when `ARCHIVED_REPORT_DIAGNOSTICS = True` and the evidence bundle is installed. Their specifications are in `docs/posthoc-*.md`.
- Measures are defined in [docs/measures.md](../docs/measures.md).

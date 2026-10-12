# Harnessing Honesty

A recorded evaluation harness that tests whether checking repairs correct answers a language model abandons under false user pressure, and what checking does to the answers it defended.

**Design.** 60 frozen yes/no technical items, each keyed by two independent oracles, on three pinned models. Each item gets one neutral answer, three pressures (contradiction, authority, citation) and, on each pressured draft, three finalisation policies (re-ask, self-check, labelled external report): 13 calls. An exploratory fixed-order loop adds 10.

**Evidence.** Every request, raw response and event is saved; scores are recomputed from these files. The answer key never reaches the model.

**Results.** Per model, repair (conceded drafts) and harm (held drafts) are reported separately, with scenario-bootstrap intervals.

## Start here

Python 3.12. The entry point is `notebooks/demo_runbook.ipynb`. It runs offline and needs no API key.

| Mode | Use | Needs |
|---|---|---|
| `synthetic` | Try the workflow | A clean checkout; numbers are illustrative |
| `archived` | Reproduce the report | The OSF evidence bundle (step 2) |
| `collection` | Analyse your own experiment | A finished development collection |

### 1. Install

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Then:

```bash
python -m pip install -e ".[dev,notebooks]"
python -m ipykernel install --prefix .venv --name harnessing-honesty --display-name "Harnessing Honesty"
python -m jupytext --sync notebooks/demo_runbook.py
python -m jupyterlab notebooks/demo_runbook.ipynb
```

Select the **Harnessing Honesty** kernel and use **Restart Kernel and Run All Cells**; the setup cell prints the mode. VS Code works too: open the same `.ipynb`. Notebooks are not stored in Git; `jupytext --sync` creates them from their `.py` sources.

To watch an experiment run, set `RUN_EXPERIMENT = True` in **Run a small experiment** first. It plans, runs, audits and analyses a two-item synthetic collection at no cost.

### 2. Install the report evidence

Download `harnessing-honesty-evidence-38c7287.zip` from the [OSF deposit](https://doi.org/10.17605/OSF.IO/HMXSJ) into the repository root. Its SHA-256 is `6dcd709c90dfda8862e109c512fa9a58b3278fac5980214c42ce36437fb37cd3`.

```powershell
Get-FileHash -LiteralPath .\harnessing-honesty-evidence-38c7287.zip -Algorithm SHA256
Expand-Archive -LiteralPath .\harnessing-honesty-evidence-38c7287.zip -DestinationPath .\evidence-deposit
Copy-Item -LiteralPath .\evidence-deposit\evidence\data\runs -Destination .\data -Recurse
```

On macOS/Linux, copy `evidence/data/runs` to `data/runs`. The result must be `data/runs/main/main-2026-10-09/`. Rerun the demo and confirm `Mode: archived`. The bundle's `README.txt` explains its contents, including three redacted records.

### 3. Without Jupyter

```bash
python -m scripts.demo_notebooks --mode synthetic --output data/notebooks/demo-synthetic-001
python -m scripts.demo_notebooks --mode archived --output data/notebooks/demo-report-001
```

Each writes executed notebooks and `execution.json` to a new directory. In VS Code, the `.py` sources also run cell by cell.

## Run your own experiment

Use notebook 05 (`python -m jupytext --sync notebooks/05_experiment_control.py`) or the terminal:

```bash
python -m harnessing_honesty.cli collection-plan --id my-demo-001 --first 2
python -m harnessing_honesty.cli collection-launch --id my-demo-001 --first 2 --client synthetic --confirm-calls 138
python -m harnessing_honesty.cli collection-status --id my-demo-001
python -m scripts.demo_notebooks --mode collection --collection data/runs/dev/my-demo-001 --output data/notebooks/demo-my-demo-001
```

Use the call count your plan prints. For CSV, results and figures:

```bash
python -m scripts.export_rows data/runs/dev/my-demo-001 --output demo-results
python -m harnessing_honesty.analysis.collected data/runs/dev/my-demo-001 --output demo-results/results.json
python -m scripts.report demo-results --output demo-report --collection data/runs/dev/my-demo-001
```

Live runs cost money: copy [`.env.example`](.env.example) to `.env` and set `OPENROUTER_API_KEY`. Synthetic and archived runs need no `.env`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Installation rejects the Python version | Recreate `.venv` with Python 3.12 |
| PowerShell blocks `Activate.ps1` | Use `.\.venv\Scripts\python.exe` instead of `python` |
| Notebook cannot import the package | Select the Harnessing Honesty kernel; reinstall with `python -m pip install -e ".[dev,notebooks]"` |
| Setup cell prints `Mode: synthetic` after installing evidence | Check the path is `data/runs/main/main-2026-10-09/` |
| Output directory already exists | Use a new output directory |

## More

- [Notebooks](notebooks/README.md) and [demonstration reference](docs/demo-runbook.md)
- [Design decisions](docs/research-design-decisions.md), [measures](docs/measures.md), [architecture](docs/architecture-boundaries.md)
- [Method sources](docs/method-sources.md) and [references](docs/references.md)
- Tests: `python -m pytest -q`

## Use of AI tools

Claude Code and Codex supported code, tests, notebooks, documentation, and source finding and checking, including the task generators, deterministic oracles and the evaluation harness. A separate construction model wrote candidate task wording after formal inputs and keys were fixed, under the documented [review protocol](docs/research-design-decisions.md). The researcher set the questions and design, made methodological decisions, reviewed the implementations, rated and repaired task wording, and remains responsible for the work.

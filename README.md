# Harnessing Honesty

A controlled evaluation harness for how harness design shapes epistemic sycophancy: a correct first answer that becomes incorrect after unsupported user pressure.

**Question.** Does a model abandon a correct answer under false pressure, and can the harness repair it?

**Design.** 60 frozen yes/no reasoning items, each checked by two independent oracles, on three models over pinned routes. Each item gets one neutral answer, three pressures (contradiction, authority, citation) and, after each pressure, three policies (none, an intrinsic self-check, a labelled external check report): 1 + 3 + 9 = 13 calls. The neutral answer is shared, and within each pressure the three finals share that pressure's draft, so they differ only in their policy. An exploratory loop, added after registration, also runs each policy through the three pressures, always in the same order, on a transcript of its own (10 calls); it tests no contrast.

**Run.** A collection is planned, checked for readiness and costed, then run by one worker process that can be stopped and resumed; status is read from its files.

**Evidence.** Every attempt is saved: the exact request, the raw provider response and an append-only event log. Scores are recomputed from these files, never stored. The scorer's private answer key is never passed to the model; the external-check policy deliberately shows a labelled verdict on the claim, which is that arm's treatment. A MAIN collection runs only against the served models, and every answer it records carries the provider's response.

**Results.** Per model: recovery (the draft conceded) and maintenance (the draft held) are reported separately, with scenario-bootstrap intervals and Holm-adjusted tests.

## Start here

Use **Python 3.12**; the package requires `>=3.12,<3.13`. The recommended
entrypoint is [notebooks/demo_runbook.ipynb](notebooks/demo_runbook.ipynb): one
notebook walks through the instrument, power gate, architecture, evidence
audit, repair/harm and external results, and can run a small synthetic
experiment end to end. Offline demonstrations need no API key.

| Goal | Mode | Evidence needed |
|---|---|---|
| Try the workflow offline | `synthetic` | A clean source checkout; numbers are illustrative |
| Reproduce the report and prepare the demo | `archived` | The public evidence deposit installed below |
| Analyse your own finished experiment | `collection` | Your own completed development collection |

### 1. Install the project and notebook kernel

Open a terminal in the repository root, the directory containing
`pyproject.toml`. If you need the source, clone
[the repository](https://github.com/AnthonyBeerus/Harnessing-Honesty), or use
the deposited source tree described below.

**Windows PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

**Then, on either platform:**

```bash
python -m pip install -e ".[dev,notebooks]"
python -m ipykernel install --prefix .venv --name harnessing-honesty --display-name "Harnessing Honesty"
python -m jupytext --sync notebooks/demo_runbook.py
python -m jupyterlab notebooks/demo_runbook.ipynb
```

The `.ipynb` notebooks are not stored in Git; the `jupytext` command creates
`demo_runbook.ipynb` from its paired `.py` source. The demo runs the other
notebooks from their `.py` sources, so they need no `.ipynb`. In VS Code, open
`notebooks/demo_runbook.ipynb` instead of starting JupyterLab and select the
same kernel.

In JupyterLab, select the **Harnessing Honesty** kernel. Use **Restart Kernel
and Run All Cells**. Allow several minutes for the step notebooks to finish;
their charts appear in the runbook, with full executed outputs and an execution
manifest saved under `data/notebooks/`.

The setup cell prints `Mode: synthetic` in a clean checkout, or `Mode: archived`
when the required local records are available. Set `MODE = "synthetic"` in that
cell if you want an illustrative run even when archived evidence is installed.
Both modes run offline. Archived mode executes seven step notebooks; synthetic
mode executes six and skips the report-specific extensions.

To watch the harness run an experiment, set `RUN_EXPERIMENT = True` in the
**Run a small experiment** section before running all cells. It plans, launches,
audits and analyses a two-item collection with the synthetic client: no model
calls and no cost, so its rates test the pipeline rather than any model. Paid
collections are launched only from notebook 05.

### 2. Install the evidence for the report demo

Download `harnessing-honesty-evidence-38c7287.zip` from the
[public OSF deposit](https://doi.org/10.17605/OSF.IO/HMXSJ).
`data/runs/` is Git-ignored, so cloning alone cannot reproduce the report's
recorded results.

The ZIP contains `README.txt`, `MANIFEST.sha256`, `REDACTIONS.json`, the records
under `evidence/`, and `source-38c7287.zip`, the matching source snapshot.
For reproduction against the deposited source, extract that inner ZIP into a
new directory and perform step 1 there.

For a fresh checkout, place the downloaded outer ZIP in the repository root
and run these **PowerShell** commands:

```powershell
Get-FileHash -LiteralPath .\harnessing-honesty-evidence-38c7287.zip -Algorithm SHA256
Expand-Archive -LiteralPath .\harnessing-honesty-evidence-38c7287.zip -DestinationPath .\evidence-deposit
Copy-Item -LiteralPath .\evidence-deposit\evidence\data\runs -Destination .\data -Recurse
```

The ZIP's SHA-256 is:

```text
6dcd709c90dfda8862e109c512fa9a58b3278fac5980214c42ce36437fb37cd3
```

On macOS/Linux, extract the ZIP with your archive tool and copy
`evidence/data/runs` into the checkout's `data/` directory. The resulting path
must be **`data/runs/main/main-2026-10-09/`**, not
`data/evidence/data/runs/`. Install into a fresh checkout so existing experiment
records are preserved. Retain the extracted manifest and redaction record.

Restart and run the demo notebook. Confirm **`Mode: archived`** before using
its numbers in a presentation, and wait for **all seven steps completed**.
The availability check lists missing paths; it does not authenticate hashes.

The public copy redacts an account identifier in three provider-error
envelopes. Their saved event-log hashes therefore differ from the deposited
envelopes; `REDACTIONS.json` records the original and deposited hashes. Read
the bundle's `README.txt` when interpreting these expected mismatches.
Exploratory records have the separate provenance limitations documented in
[the demo setup reference](docs/demo-runbook.md).

### 3. Run without opening JupyterLab

The notebooks are optional. Without Jupyter, run every step from the
terminal; for the full experiment workflow without notebooks, see
[Run your own experiment](#run-your-own-experiment). In VS Code, the `.py`
sources also run directly: each `# %%` block offers **Run Cell** in the
Interactive Window, so no `.ipynb` is needed.

From the same activated environment, choose one command:

```bash
python -m scripts.demo_notebooks --mode synthetic --output data/notebooks/demo-synthetic-001
python -m scripts.demo_notebooks --mode archived --output data/notebooks/demo-report-001
```

Each command writes executed step notebooks and `execution.json`. Use a new
output directory each time, for example `demo-report-002` on the next run.
For a screen recording, open and run `demo_runbook.ipynb`; the command-line
runner saves the individual steps rather than the combined presentation.

## Run your own experiment

Start with [05_experiment_control.ipynb](notebooks/05_experiment_control.ipynb),
created with `python -m jupytext --sync notebooks/05_experiment_control.py`.
Choose a new collection ID, development track, and `CLIENT = "synthetic"` for
an offline rehearsal. The notebook previews requests and the workload before
its explicit launch switches. The
[new-experiment walkthrough](docs/demo-runbook.md#run-another-experiment)
explains launch, status, continuation and analysis. Live collection is a
separate opt-in path requiring an OpenRouter key and paid provider requests;
it is not needed for either demo mode. For live runs, copy
[`.env.example`](.env.example) to `.env`, which Git ignores, and set
`OPENROUTER_API_KEY`; the harness reads it when a live client starts.
Synthetic and archived runs need no `.env`.

An equivalent two-item offline rehearsal from the terminal is:

```bash
python -m harnessing_honesty.cli collection-plan --id my-demo-001 --first 2
python -m harnessing_honesty.cli collection-launch --id my-demo-001 --first 2 --client synthetic --confirm-calls 138
python -m harnessing_honesty.cli collection-status --id my-demo-001
```

The plan is 2 items × 3 systems × 23 matrix/loop calls = 138 planned calls.
Use the call count printed by your own plan if you change the selection.
Wait for collection completion before analysing
`data/runs/dev/my-demo-001/`:

```bash
python -m scripts.demo_notebooks --mode collection --collection data/runs/dev/my-demo-001 --output data/notebooks/demo-my-demo-001
```

This analyses your collection with archived extensions disabled. Direct CSV,
analysis and figure exports are also available:

```bash
python -m scripts.export_rows data/runs/dev/my-demo-001 --output demo-results
python -m harnessing_honesty.analysis.collected data/runs/dev/my-demo-001 --output demo-results/results.json
python -m scripts.report demo-results --output demo-report --collection data/runs/dev/my-demo-001
```

[Measures](docs/measures.md) defines the outputs. See
[the notebook guide](notebooks/README.md) for individual notebooks and source
pairing, and [the demo setup reference](docs/demo-runbook.md) for full controls.

## Setup troubleshooting

| Symptom | Fix |
|---|---|
| Installation rejects the Python version | Run `python --version`; recreate `.venv` using Python 3.12 |
| PowerShell blocks `Activate.ps1` | Use `.\.venv\Scripts\python.exe` instead of `python` for the commands above; activation is optional |
| Notebook cannot import the package | Select the Harnessing Honesty kernel and install from this checkout with `python -m pip install -e ".[dev,notebooks]"` |
| Archived evidence is missing | Check the listed paths and the extraction layout; confirm the mode before presenting results |
| Output directory already exists | Choose a new output directory rather than replacing previous outputs |

For development validation, run `python -m pytest -q` from the activated
environment. Tests are separate from running the demo.

Design choices are recorded in [docs/research-design-decisions.md](docs/research-design-decisions.md) as they become concrete in code.

See [Sources for the methods](docs/method-sources.md) for the literature behind
the methodological comparisons, and [References](docs/references.md) for the
IEEE reference list and BibTeX metadata.

The [surface-model pilot audit](docs/surface-model-pilot-audit.md) points to the
local blinded review CSV and records a provisional, non-adjudicating quality
check. Pilot candidates are not part of the accepted instrument.

## Use of AI tools

Claude Code and Codex supported code, tests, notebooks, documentation, and
source finding and checking. Their work included task generators,
deterministic oracles and the recorded evaluation harness. A separate
construction model wrote candidate task wording after formal inputs and keys
were fixed, under the documented
[review protocol](docs/research-design-decisions.md).

The researcher set the questions and design, made methodological decisions,
reviewed the implementations, rated and repaired task wording, and remains
responsible for the work. Research tooling and the construction model are
distinct from the systems under test.

## Repository structure

One case travels one route: configuration → cases → messages → provider →
raw attempts → scores → analysis. In `src/harnessing_honesty/`, `compiler/`
builds and freezes the cases, `runtime/` renders messages and runs the
treatment, `models/` reaches the provider, `observability/` records raw
attempts, `scoring/` scores them and `analysis/` estimates; `evaluation/`
specifies, runs and resumes collections, and `domain/` holds the shared
contracts. The [harness architecture](docs/architecture-boundaries.md)
explains the route, the patterns it follows (layers, pipes and filters,
information hiding, ports and adapters, event sourcing) and the import rules
that `tests/architecture/` enforces.

See [Analysis notebooks](notebooks/README.md) for the optional Jupyter setup,
the entrypoints and their scope.

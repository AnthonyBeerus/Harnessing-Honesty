# Experiment and analysis notebooks

| Source | Current scope |
|---|---|
| `01_instrument_audit.py` | Complete 60-case formal-structure, repetition, cue, and construction review |
| `02_run_audit.py` | Existing event reconstruction for a selected local run |
| `03_power.py` | Design reference; no power simulation |
| `04_results.py` | Analysis-row contract; no empirical estimates |

These are initial entrypoints. The instrument review is implemented; later
scientific checks and estimators are not. Calculations belong in the package;
notebooks supply inputs and present outputs.

## Planned experiment-control notebook

A fifth notebook will provide an interface for operating the experiment.
The collector and this notebook are not yet implemented. The intended workflow is:

| Operation | Information presented |
|---|---|
| Select configuration | Registered conditions, scenario inventory, serving configuration and output location |
| Check readiness | Passed and failed collection checks, planned call count and estimated cost with assumptions |
| Preview | Representative requests and the planned condition schedule |
| Launch | Explicit start of an approved run using the validated configuration |
| Monitor | Recorded progress, usage, serving failures and worker status |
| Stop or resume | Persisted run identity, interrupted attempts and the permitted continuation |
| Inspect artifacts | Saved records for the run-audit notebook |

Both notebook and CLI will use the same collection interface described in
[Harness architecture](../docs/architecture-boundaries.md#notebook-operation).
Bluesky's RunEngine provides a precedent for separating interactive operation
from experiment execution [47, Sec. "The RunEngine"]. Pydantic Evals exposes
evaluation through Python calls and report objects [48, Sec. "Code-First Evaluation"].
These precedents support the interface design; they do not establish the
validity of this study's procedure.

Opening, synchronizing or rendering the notebook will not start collection.
Automated checks will use offline fixtures. Live launch will require a separate,
explicit operation after approval of the concrete call and cost plan.
Monitoring will expose operational progress without using interim outcomes
to determine which trials execute or when collection stops.

## Setup

From the repository root, with the project virtual environment active:

```bash
python -m pip install -e ".[notebooks]"
python -m ipykernel install --prefix .venv --name harnessing-honesty --display-name "Harnessing Honesty"
python -m jupytext --sync notebooks/01_instrument_audit.py
python -m jupyterlab
```

Open the generated `.ipynb` file and select the **Harnessing Honesty** kernel.
Use the same sync command for the other source files. After editing a generated
notebook, sync it again to retain its changes in the Python source [38].

Jupytext percent-format files hold the authored cells and Markdown in Git.
The paired `.ipynb` files contain local outputs and are ignored. This separates
editable sources from executed artifacts [38].

## Execute all four

```bash
python scripts/run_notebooks.py --output data/notebooks/check-001
```

Choose a new output directory for each execution. Each notebook runs in a fresh
kernel from the repository root; an error stops execution [39]. The directory
contains executed notebooks and `execution.json`, recording source hashes,
the Git revision and working-tree status, package versions, and completion
status. This is execution provenance, not a complete research-data archive.
The default run audit has no selected data and reports that no audit occurred.

Notebook dependencies are optional and separate from collection dependencies.
No live model calls are made by these entrypoints.

## Development live smoke

`development/live_api_smoke.py` is an interactive check of the existing live
adapter and shared-draft runtime. `FAMILY` selects an independently checked,
excluded fixture for a family whose variation substep is complete. Systems,
pipelines, programs and logic are available; the tracked selection is the most
recently varied family. One execution sends five requests per SUT:
neutral, pressure draft, and one final for each policy.
Its tracked switch is off, and the release notebook batch does not include the
development directory. This preserves the no-dispatch default recommended for
reviewable computational notebooks [[26]](../docs/references.md#rule2019notebooks).

Generate and open the local notebook with:

```bash
python -m jupytext --sync notebooks/development/live_api_smoke.py
python -m jupyterlab notebooks/development/live_api_smoke.ipynb
```

Review `FAMILY` and the request preview, change `RUN_LIVE_API` to `True`, and run
the launch cell. Each execution with the switch enabled sends 15 paid API
requests. The notebook invokes
`python -m harnessing_honesty.cli run-live-policy-path` in a child process, so
it uses the same adapter as the CLI and avoids an active event-loop conflict.
The smoke checks the three policy paths and classified provider envelopes only;
it does not validate policy effects, scoring, reconstruction or the collector.

## References

IEEE numbers follow the [project bibliography](../docs/references.md).

[38] Jupytext contributors, “Jupytext.” Accessed: Sep. 4, 2026. [Online].
Available: https://github.com/jupytext/jupytext.

[39] Jupyter contributors, “Executing notebooks.” Accessed: Sep. 4, 2026.
[Online]. Available: https://nbclient.readthedocs.io/en/latest/client.html.

[47] Bluesky Project, “Tutorial,” *Bluesky 1.13.1 Documentation*, sec. “The RunEngine.”
Accessed: Sep. 4, 2026. [Online]. Available: https://blueskyproject.io/bluesky/v1.13.1/tutorial.html.

[48] Pydantic, “Pydantic Evals,” sec. “Code-First Evaluation.” Accessed: Sep. 4, 2026.
[Online]. Available: https://pydantic.dev/docs/ai/evals/evals/.

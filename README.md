# Harnessing Honesty

A controlled evaluation harness for how harness design shapes epistemic sycophancy: a correct first answer that becomes incorrect after unsupported user pressure.

**Question.** Does a model abandon a correct answer under false pressure, and can the harness repair it?

**Design.** 60 frozen yes/no reasoning items, each checked by two independent oracles, on three models over pinned routes. Each item gets one neutral answer, three pressures (contradiction, authority, citation) and, after each pressure, three policies (none, an intrinsic self-check, a labelled external check report): 1 + 3 + 9 = 13 calls. The neutral answer is shared, and within each pressure the three finals share that pressure's draft, so they differ only in their policy. An exploratory loop, added after registration, also runs each policy through the three pressures, always in the same order, on a transcript of its own (10 calls); it tests no contrast.

**Run.** A collection is planned, checked for readiness and costed, then run by one worker process that can be stopped and resumed; status is read from its files.

**Evidence.** Every attempt is saved: the exact request, the raw provider response and an append-only event log. Scores are recomputed from these files, never stored. The scorer's private answer key is never passed to the model; the external-check policy deliberately shows a labelled verdict on the claim, which is that arm's treatment. A MAIN collection runs only against the served models, and every answer it records carries the provider's response.

**Results.** Per model: recovery (the draft conceded) and maintenance (the draft held) are reported separately, with scenario-bootstrap intervals and Holm-adjusted tests.

## Setup

Python 3.12, venv on, from the repo root:

```bash
pip install -e ".[dev]"
pytest -q
python -m harnessing_honesty.cli collection-plan --id demo --first 2
python -m harnessing_honesty.cli collection-launch --id demo --first 2 --client synthetic --confirm-calls 138
python -m harnessing_honesty.cli collection-status --id demo
```

The plan prints the selection, readiness and expected cost; the launch runs two items on the three models with an offline synthetic client, so nothing is sent to a provider. The run's files appear under `data/runs/dev/demo/`. When it is complete, three commands give the results:

```bash
python -m scripts.export_rows data/runs/dev/demo --output demo-results
python -m harnessing_honesty.analysis.collected data/runs/dev/demo --output demo-results/results.json
python -m scripts.report demo-results --output demo-report --collection data/runs/dev/demo
```

The first writes the matrix and loop rows as CSV, the second each model's report beside them, and the third the report's figures and tables by results section, indexed in `demo-report/figures.md` (`--replicate` and `--stability` add the views that need repeated runs). [docs/measures.md](docs/measures.md) defines every measure and column.

Design choices are recorded in [docs/research-design-decisions.md](docs/research-design-decisions.md) as they become concrete in code.

See [Sources for the methods](docs/method-sources.md) for the literature behind
the methodological comparisons, and [References](docs/references.md) for the
IEEE reference list and BibTeX metadata.

The [surface-model pilot audit](docs/surface-model-pilot-audit.md) points to the
local blinded review CSV and records a provisional, non-adjudicating quality
check. Pilot candidates are not part of the accepted instrument.

## Use of AI tools

This project was developed with two AI coding agents, Claude Code
(Anthropic) and Codex (OpenAI), each running frontier models more capable
than the systems under test. They drafted and revised the harness, its tests,
the notebooks and the documentation, and helped ground design choices in the
relevant research by finding, reading and checking sources.

The work followed the practices these tools' developers recommend [110],
[112]. Each change was explored and planned before code was written, so the
research question it served was stated first; written plans and persistent
project instructions carried decisions across sessions; long sessions were
compacted to summaries and focused investigations ran in separate contexts
[111]; and changes were checked against the test suite before review, many
also against deliberately injected faults. Context and plan files of this
kind are a documented practice in agentic coding [113], [114].

The author set the research questions and the design, made every
methodological choice, reviewed each change and committed it, and is
responsible for all of it. Every result can be checked against the tests and
recorded runs in this repository. The tools are separate from the language
models under study, which are reached only through the pinned serving cards
in `config/`. Two of those models come from the same providers as the tools
(Anthropic and OpenAI); the tools were never used as systems under test.

References are numbered as in [References](docs/references.md).

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

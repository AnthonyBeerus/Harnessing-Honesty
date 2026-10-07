# Harnessing Honesty

A controlled evaluation harness for how harness design shapes epistemic sycophancy: a correct first answer that becomes incorrect after unsupported user pressure.

Development episodes share one neutral response, then fork into isolated pressure branches. That stops sampling noise in the first answer from being mistaken for a treatment effect. Branch order is a seeded permutation of IDs only; clones are structural, not mutate-and-rollback.

The controller scores the public answers. Prompt rendering receives only `PromptView`; the private `AnswerKey` is reachable from the checker and nowhere on the message path.

The development condition is a 3x3 matrix: three pressure families (contradiction, authority, citation) by three policies (none, intrinsic recheck, labelled external ceiling). One neutral answer and one draft per pressure are shared, so a matrix run is 13 model calls rather than nine episodes. An exploratory multi-turn substudy, added after registration, runs one loop per policy, three escalating pressure turns on an accumulating transcript; it is descriptive, tests no contrast and never becomes a matrix cell.

## Setup

Python 3.12, venv on, from the repo root:

```bash
pip install -e ".[dev]"
pytest -q
python -m harnessing_honesty.cli show-matrix
```

`show-matrix` renders the nine development requests side by side with the symmetry checks, then the policy loops.

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

The [harness architecture](docs/architecture-boundaries.md) explains the
component boundaries and their methodological basis. In `src/harnessing_honesty/`,
`runtime/` contains context and finalization logic, `models/` contains provider
interaction, and `evaluation/` contains trial scheduling and qualification.
`domain/` defines shared contracts; `compiler/`, `scoring/`, `observability/`
and `analysis/` separate construction, measurement, recording and estimation.
Tests follow the same component structure, with dependency checks in
`tests/architecture/`.

See [Analysis notebooks](notebooks/README.md) for the optional Jupyter setup,
the four entrypoints and their current scope.

# Harnessing Honesty

A controlled evaluation harness for how harness design shapes epistemic sycophancy: a correct first answer that becomes incorrect after unsupported user pressure.

Development episodes share one neutral response, then fork into isolated pressure branches. That stops sampling noise in the first answer from being mistaken for a treatment effect. Branch order is a seeded permutation of IDs only; clones are structural, not mutate-and-rollback.

The controller scores the public answers. Prompt rendering receives only `PromptView`; the private `AnswerKey` is reachable from the checker and nowhere on the message path.

The development condition is a 3x3 matrix: three pressure families (contradiction, authority, citation) by three policies (none, intrinsic recheck, labelled external ceiling). One neutral answer and one draft per pressure are shared, so a matrix run is 13 model calls rather than nine episodes. Seeded multi-turn orderings are a separate descriptive path and never become a matrix cell.

## Setup

Python 3.12, venv on, from the repo root:

```bash
pip install -e ".[dev]"
pytest -q
python -m harnessing_honesty.cli run-fake
python -m harnessing_honesty.cli show-matrix
```

`run-fake` prints public transcripts next to private scores. `show-matrix` renders the nine development requests side by side with the symmetry checks, then the multi-turn spine.

Design choices are recorded in [docs/research-design-decisions.md](docs/research-design-decisions.md) as they become concrete in code.

See [Sources for the methods](docs/method-sources.md) for the literature behind
the methodological comparisons, and [References](docs/references.md) for the
IEEE reference list and BibTeX metadata.

## Repository structure

The [harness architecture](docs/architecture-boundaries.md) explains the
component boundaries and their methodological basis. In `src/harnessing_honesty/`,
`runtime/` contains context and finalization logic, `models/` contains provider
interaction, and `evaluation/` contains trial scheduling and qualification.
`domain/` defines shared contracts; `compiler/`, `scoring/`, `observability/`
and `analysis/` separate construction, measurement, recording and estimation.
Tests follow the same component structure, with dependency checks in
`tests/architecture/`.

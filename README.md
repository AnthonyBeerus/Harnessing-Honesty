# Harnessing Honesty

A controlled evaluation harness for how harness design shapes epistemic sycophancy: a correct first answer that becomes incorrect after unsupported user pressure.

Development episodes share one neutral response, then fork into isolated pressure branches. That stops sampling noise in the first answer from being mistaken for a treatment effect. Branch order is a seeded permutation of IDs only; clones are structural, not mutate-and-rollback.

## Setup

Python 3.12, venv on, from the repo root:

```bash
pip install -e ".[dev]"
pytest -q
"""The report's figures and tables, organised by the sections of its results.

``python -m scripts.report RESULTS --output OUT`` draws every figure and
table that its inputs allow, writes each figure as PNG and PDF and each table
as CSV, and indexes them by section in ``figures.md`` and ``tables.md``.
``RESULTS`` holds ``results.json``, ``matrix-rows.csv`` and ``loop-rows.csv``
(written by ``harnessing_honesty.analysis.collected`` and
``scripts.export_rows`` for MAIN, or by ``scripts.development_results``).
Optional inputs add the views that need them: ``--collection`` the recorded
calls (bootstrap distributions, retries, cost), ``--replicate`` the results
folders of repeated runs (estimate stability, pass^k), and ``--stability``
the agreement written by ``scripts.compare_runs``.

4.1 Sycophancy: does a correct answer collapse under false pressure?
4.2 Harness repair: the policies compared (H1)
4.3 Task structure and pressure (H3, H2)
4.4 Multi-turn pressure and alternative usage (exploratory)
4.5 Robustness
4.6 Harness cost

Everything was chosen before MAIN and only counts, redraws or replays values
the analysis already reports; views beyond the registered analysis are
descriptive and test nothing.
"""

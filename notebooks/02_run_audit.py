# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     notebook_metadata_filter: kernelspec,language_info
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
# ---

# %% [markdown]
# # Run audit
# This entrypoint reads an explicitly selected local run directory.
# Event reconstruction currently checks sequence continuity and the summary
# identifier. It does not establish complete request reconstruction or serving
# equivalence; see [Sources for the methods](../docs/method-sources.md#scoring-inference-and-records).

# %%
from pathlib import Path

from harnessing_honesty.observability.reconstruct import reconstruct_run

root = next(path for path in (Path.cwd(), *Path.cwd().parents)
            if (path / "pyproject.toml").is_file()
            and (path / "config/freeze.json").is_file())
run_directory = None  # Set an explicit Path relative to the repository root.

# %% [markdown]
# ## Recorded execution
# With no selected run, no audit is performed. The request count is the number
# of recorded `request_sent` events, not verified successful provider responses.

# %%
if run_directory is None:
    print("No run selected. No audit results are available.")
else:
    run_path = root / run_directory
    reconstructed = reconstruct_run(run_path)
    print(f"Input: {run_path}")
    print(f"Run: {reconstructed.record.run_id}")
    print(f"Recorded requests: {reconstructed.complete_calls}")
    print(f"Marked incomplete: {reconstructed.interrupted}")

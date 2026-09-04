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
# # Results
# This entrypoint exposes the current analysis-row contract. No empirical
# dataset is loaded. The analysis package currently supplies descriptive rates
# and point contrasts, without the planned model fitting or confidence intervals.
# These limits are described in [Sources for the methods](../docs/method-sources.md#scoring-inference-and-records).

# %%
from harnessing_honesty.analysis.rows import AnalysisRow

# %% [markdown]
# ## Analysis inputs
# A validated reconstruction and estimator are required before reporting the
# registered contrasts. Listing the required fields does not validate data.

# %%
print("Current analysis-row fields:")
for name in AnalysisRow.model_fields:
    print(f"  {name}")
print("No empirical results are available in this notebook.")

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
# # Power analysis
# This entrypoint identifies the working design. Power simulation and estimator
# validation are not implemented. No power estimate is produced.
# The [working preregistration](../docs/preregistration-template.md) specifies
# the planned inference; a manifest count alone cannot establish adequate power.

# %%
import json
from pathlib import Path

root = next(path for path in (Path.cwd(), *Path.cwd().parents)
            if (path / "pyproject.toml").is_file()
            and (path / "config/freeze.json").is_file())
manifest = json.loads((root / "config/freeze.json").read_text(encoding="utf-8"))

# %% [markdown]
# ## Design reference
# Scenario dependence, model fitting and missing responses require a validated
# simulation before this notebook can report power.

# %%
print(f"Freeze: {manifest['freeze_id']}")
print(f"Registered items: {len(manifest['item_ids'])}")
print("Power estimate: unavailable; simulation is not implemented.")

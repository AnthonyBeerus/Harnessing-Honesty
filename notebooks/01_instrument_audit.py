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
# # Instrument audit
# This entrypoint reads the working freeze manifest. It reports the registered
# item count; it does not yet audit pressure semantics or oracle independence.
# The methodological basis is documented in [Sources for the methods](../docs/method-sources.md).

# %%
import json
from pathlib import Path

root = next(path for path in (Path.cwd(), *Path.cwd().parents)
            if (path / "pyproject.toml").is_file()
            and (path / "config/freeze.json").is_file())
manifest_path = root / "config/freeze.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

# %% [markdown]
# ## Registered inventory
# The count below describes the manifest, not evidence that each item is valid.

# %%
print(f"Input: {manifest_path.relative_to(root)}")
print(f"Freeze: {manifest['freeze_id']}")
print(f"Registered items: {len(manifest['item_ids'])}")
print(f"Unique item identifiers: {len(set(manifest['item_ids']))}")

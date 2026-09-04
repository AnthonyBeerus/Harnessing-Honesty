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
# # Development live API smoke
#
# This notebook sends one excluded development question through the existing
# CLI and live model adapter. It is not a confirmatory run and does not exercise
# pressure, finalization policies, scoring or collection. The response is only
# evidence that this development request reached the configured service path.
#
# OpenRouter routing and observed metadata are assessed against [32] and [34].
# The adapter uses the pinned Pydantic AI interface [43]. IEEE entries are in
# [the project bibliography](../../docs/references.md).

# %%
from pathlib import Path
import subprocess
import sys

from harnessing_honesty.evaluation.fixtures.scenarios import development_scenario
from harnessing_honesty.models.config import load_run_config

root = next(path for path in (Path.cwd(), *Path.cwd().parents)
            if (path / "pyproject.toml").is_file()
            and (path / "config/qualification.example.yaml").is_file())
config_path = root / "config/qualification.example.yaml"
config = load_run_config(config_path)
scenario = development_scenario()

# %% [markdown]
# ## Request preview
#
# This shows the selected public development input and requested route. It does
# not establish the provider that will serve a request.

# %%
print(f"Track: {config.track.value}")
print(f"Scenario: {scenario.prompt.id} (excluded development fixture)")
print(f"Requested model: {config.serving.requested_model}")
print(f"Required provider: {', '.join(config.serving.routing.provider_only)}")
print(f"Question:\n{scenario.prompt.question}")

# %% [markdown]
# ## Explicit live launch
#
# Change the switch to `True`, then run this cell. It starts exactly one
# development smoke call in a child process. The child process avoids running
# Pydantic AI's synchronous interface inside Jupyter's active event loop.
# Re-running the cell with the switch enabled sends another paid request.

# %%
RUN_LIVE_API = False

if not RUN_LIVE_API:
    print("Live API call skipped. Set RUN_LIVE_API = True to send one request.")
else:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "harnessing_honesty.cli",
            "run-live",
            "--config",
            str(config_path),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    if completed.returncode:
        raise RuntimeError(f"Development live smoke failed with exit code {completed.returncode}")

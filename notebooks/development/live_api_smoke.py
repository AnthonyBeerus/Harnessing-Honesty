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
# This notebook sends one excluded case from the selected completed family
# through the shared-draft path for all three registered SUTs and all three
# finalization policies. It is not a confirmatory run and does not score or
# collect outcomes. Its 15 answers and provider envelopes are only evidence
# that the proposed path works.
# The selected case is a researcher-authored excluded fixture. A successful
# smoke does not validate the confirmatory pool or its construction.
#
# OpenRouter routing and observed metadata are assessed against [32] and [34].
# Plain-text output uses the pinned Pydantic AI interface [43]. The intrinsic
# and external conditions follow the distinction in [15] and [16]; displayed
# rationales are omitted because they can rationalize biased answers [68].
# IEEE entries are in
# [the project bibliography](../../docs/references.md).

# %%
from pathlib import Path
import subprocess
import sys

from harnessing_honesty.evaluation.fixtures.scenarios import (
    development_logic_scenario,
    development_pipeline_scenario,
    development_program_scenario,
    development_systems_scenario,
)
from harnessing_honesty.models.config import load_run_config

root = next(path for path in (Path.cwd(), *Path.cwd().parents)
            if (path / "pyproject.toml").is_file()
            and (path / "config/qualification.example.yaml").is_file())
config_paths = [
    root / "config/qualification.sonnet.anthropic.yaml",
    root / "config/qualification.gpt4o.openai.yaml",
    root / "config/qualification.gemma4.deepinfra.yaml",
]
configs = [load_run_config(path) for path in config_paths]
FAMILY: str = "logic"
if FAMILY == "systems":
    scenario = development_systems_scenario()
elif FAMILY == "pipelines":
    scenario = development_pipeline_scenario()
elif FAMILY == "programs":
    scenario = development_program_scenario()
elif FAMILY == "logic":
    scenario = development_logic_scenario()
else:
    raise ValueError(f"No excluded live-smoke fixture is ready for {FAMILY!r}")

# %% [markdown]
# ## Request preview
#
# This shows the selected public development input and requested route. It does
# not establish the provider that will serve a request.

# %%
print(f"Scenario: {scenario.prompt.id} (excluded development fixture)")
for config in configs:
    print(
        f"{config.serving.requested_model} via "
        f"{', '.join(config.serving.routing.provider_only)}"
    )
print(f"Question:\n{scenario.prompt.question}")

# %% [markdown]
# ## Explicit live launch
#
# Change the switch to `True`, then run this cell. It starts exactly 15 paid
# model requests: five shared-path calls for each of three SUTs. The child
# process avoids running
# Pydantic AI's synchronous interface inside Jupyter's active event loop.
# Re-running the cell with the switch enabled sends another paid request.

# %%
RUN_LIVE_API = False

if not RUN_LIVE_API:
    print("Live API calls skipped. Set RUN_LIVE_API = True to send 15 paid model requests.")
else:
    command = [
        sys.executable,
        "-m",
        "harnessing_honesty.cli",
        "run-live-policy-path",
        "--family",
        FAMILY,
        "--confirm-paid-requests",
        "15",
    ]
    for path in config_paths:
        command.extend(["--config", str(path)])
    completed = subprocess.run(
        command,
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

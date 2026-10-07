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
# This notebook sends one excluded case from the selected family through the
# complete collector for each selected SUT: specification, readiness check,
# worker process, recording and resume, as a collection would. Each SUT gets
# one 13-call block (one neutral, three pressure drafts, nine policy finals).
# It is not a confirmatory run and does not score or collect outcomes. Its
# answers and provider envelopes are only evidence that the path works.
# The selected case is a benchmark-grounded excluded fixture. A successful
# smoke does not validate the confirmatory pool or its construction.
#
# OpenRouter routing and observed metadata are assessed against [32] and [34].
# Plain-text output uses the pinned Pydantic AI interface [43]. The intrinsic
# and external conditions follow the distinction in [15] and [16]; displayed
# rationales are omitted because they can rationalize biased answers [68].
# IEEE entries are in
# [the project bibliography](../../docs/references.md).

# %%
import subprocess
import sys

from harnessing_honesty import REPO_ROOT
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation.collection import (
    CALLS_PER_BLOCK,
    block_items,
    preview,
)
from harnessing_honesty.evaluation.fixtures.scenarios import checked_development_blocks
from harnessing_honesty.models.config import load_run_config

root = REPO_ROOT
config_paths = [root / card for card in PRIMARY_SERVING_CARDS]
configs = [load_run_config(path) for path in config_paths]
FAMILY: str = "logic"
scenario = checked_development_blocks()[FAMILY][0]

# %% [markdown]
# ## Request preview
#
# The 13 requests of one block, rendered offline by the collection runner. The
# requested route does not establish the provider that will serve a request.

# %%
print(f"Scenario: {scenario.prompt.id} (excluded development fixture)")
for config in configs:
    print(
        f"{config.serving.requested_model} via "
        f"{', '.join(config.serving.routing.provider_only)}"
    )
record = preview(block_items(Track.DEV)[scenario.prompt.id])
print(f"Neutral request:\n{record.shared.request[-1].content}")
for draft in record.drafts:
    print(f"[{draft.pressure_family}] {draft.snapshot.request[-1].content}")
for branch in record.branches:
    print(f"[{branch.condition.identity}] {branch.snapshot.request[-1].content[:76]}")

# %% [markdown]
# ## Explicit live launch
#
# Change the switch to `True`, then run this cell. It starts one collector
# worker per selected SUT, each sending one block of 13 paid model requests.
# The worker process runs outside Jupyter's active event loop, which Pydantic
# AI's synchronous interface requires. Re-running the cell with the switch
# enabled starts new collections and sends more paid requests.

# %%
RUN_LIVE_API = False
total = CALLS_PER_BLOCK * len(config_paths)

if not RUN_LIVE_API:
    print(f"Live API calls skipped. Set RUN_LIVE_API = True to send {total} paid"
          " model requests.")
else:
    for path in config_paths:
        command = [
            sys.executable,
            "-m",
            "harnessing_honesty.cli",
            "run-development-block",
            "--config",
            str(path),
            "--family",
            FAMILY,
            "--confirm-paid-requests",
            str(CALLS_PER_BLOCK),
        ]
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
            raise RuntimeError(
                f"Development block failed with exit code {completed.returncode}"
            )

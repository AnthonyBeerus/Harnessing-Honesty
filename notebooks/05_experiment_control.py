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
# # Experiment control
# This notebook operates collection through the functions the CLI uses; its
# cells hold selections and show results, never a procedure of their own
# (docs/architecture-boundaries.md, "Notebook operation"). Opening or running
# it as it stands dispatches nothing and writes nothing: every action below is
# off until its switch is set. A worker process, not this kernel, runs a
# collection, so a lost kernel does not stop it, and reopening the notebook
# reconnects by collection id. Bluesky likewise separates interactive control
# from the engine that executes and records [47, Sec. "The RunEngine"].

# %%
from pathlib import Path

from harnessing_honesty import REPO_ROOT
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation import collection, workload
from harnessing_honesty.runtime.live import RUNS_ROOT

root = REPO_ROOT
runs_root = root / RUNS_ROOT

# %% [markdown]
# ## Configuration
# The selection below defines a collection. The development track runs the
# frozen items, or excluded development cases, on any cards; MAIN runs only the
# frozen items on the primary cards under a matching signed freeze. Once a
# collection is accepted its specification is fixed on disk: changing these
# variables afterwards cannot change it, and a launch under the same id with a
# different selection is refused.

# %%
COLLECTION_ID = "synthetic-control"
TRACK = Track.DEV
CARDS = PRIMARY_SERVING_CARDS
ITEM_IDS = tuple(item.item_id for item in confirmatory_pool())
FREEZE_ID: str | None = None

spec = collection.selection(COLLECTION_ID, TRACK, CARDS, ITEM_IDS, freeze_id=FREEZE_ID)
directory = runs_root / TRACK.value / COLLECTION_ID
print(f"Directory: {directory}")

# %% [markdown]
# ## Plan, readiness and cost
# What the selection would run, every reason it may not start, and the
# expected cost from recorded runs only, with the assumptions the estimate
# makes. Nothing is dispatched; the CLI's `collection-plan` prints the same.

# %%
print(workload.plan_text(spec, runs_root))

# %% [markdown]
# ## Request preview
# The first scheduled block of each kind, rendered offline by the collection
# runner: a matrix block's 13 requests and a loop block's 10.

# %%
schedule = collection.block_schedule(spec)
for kind in spec.kinds:
    first = next(block for block in schedule if block.kind == kind)
    item = collection.block_items(spec.track)[first.item_id]
    print(f"First {kind} block: {first.item_id} on {first.card}, "
          f"order seed {first.order_seed}")
    if kind == "matrix":
        record = collection.preview(item, first.order_seed)
        print(f"Neutral: {record.shared.request[-1].content[:300]}")
        for draft in record.drafts:
            text = draft.snapshot.request[-1].content[:90]
            print(f"[{draft.pressure_family}] {text}")
        print("Finals in dispatch order:", ", ".join(record.execution_order))
    else:
        loops = collection.preview_loops(item, first.order_seed)
        for turn in loops.loops[0].turns:
            # The pressure is the message after the model's previous answer.
            request = turn.snapshot.request
            answered = max(n for n, m in enumerate(request) if m.role == "assistant")
            pressure = request[answered + 1].content[:90]
            print(f"[turn {turn.position}, {turn.pressure_family}] {pressure}")
        print("Loops in dispatch order:", ", ".join(loops.execution_order))

# %% [markdown]
# ## Launch
# Set `LAUNCH = True`, `APPROVED_CALLS` to the planned call count and
# `CLIENT` to `"live"` for paid calls or `"synthetic"` for an offline run. The
# collection is created, or reused only if its stored specification is this
# one, and one worker is started. Repeating the cell reports the collection's
# state instead of starting a second worker.

# %%
LAUNCH: bool = False
APPROVED_CALLS: int | None = None
CLIENT = "synthetic"

if LAUNCH:
    if APPROVED_CALLS is None or APPROVED_CALLS != spec.planned_calls:
        raise ValueError(f"set APPROVED_CALLS = {spec.planned_calls} to launch")
    directory = collection.start_or_reuse(runs_root, spec)
    launched = collection.launch(
        directory, approved_calls=APPROVED_CALLS, client=CLIENT
    )
    print(f"Launched or found: owner {launched.owner}, complete {launched.complete}")
else:
    print("No launch requested.")

# %% [markdown]
# ## Status
# Read from the collection's files alone. Indeterminate attempts are calls
# whose provider outcome is unknown; resuming sends each again as its next
# attempt and keeps the uncertain one in the record. A paused SUT waits for
# its route to be restored.

# %%
print(workload.status_text(directory))

# %% [markdown]
# ## Stop, resume and pauses
# A stop takes effect between blocks; nothing is cut mid-call. Resuming
# withdraws the stop request and launches again under the same id. Clearing a
# pause names one card, after its pinned route serves the frozen contract
# again.

# %%
REQUEST_STOP: bool = False
RESUME: bool = False
CLEAR_PAUSE_CARD: str | None = None

if REQUEST_STOP:
    collection.request_stop(directory)
    print("Stop requested.")
if CLEAR_PAUSE_CARD is not None:
    collection.clear_pause(directory, CLEAR_PAUSE_CARD)
    print(f"Pause cleared for {CLEAR_PAUSE_CARD}.")
if RESUME:
    if APPROVED_CALLS is None or APPROVED_CALLS != spec.planned_calls:
        raise ValueError(f"set APPROVED_CALLS = {spec.planned_calls} to resume")
    collection.clear_stop(directory)
    resumed = collection.launch(directory, approved_calls=APPROVED_CALLS, client=CLIENT)
    print(f"Resumed or found: owner {resumed.owner}")
if not (REQUEST_STOP or RESUME or CLEAR_PAUSE_CARD):
    print("No control action requested.")

# %% [markdown]
# ## Audit
# Each SUT's run directory can be opened in the run-audit notebook,
# `02_run_audit.py`, by setting its `run_directory`. Scientific outcomes are
# inspected there and in the results notebook, never here: collection decisions
# do not depend on them.

# %%
for sut in spec.suts:
    run_id = collection.sut_run_id(spec, sut.card)
    print(f"run_directory = {runs_root / TRACK.value / run_id}")

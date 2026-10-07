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

from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation import collection, workload
from harnessing_honesty.models.config import load_run_config
from harnessing_honesty.runtime.live import RUNS_ROOT

root = next(path for path in (Path.cwd(), *Path.cwd().parents)
            if (path / "pyproject.toml").is_file()
            and (path / "config/freeze.json").is_file())
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

spec = collection.build_spec(
    COLLECTION_ID,
    TRACK,
    CARDS,
    ITEM_IDS,
    scheduler_seed=load_run_config(root / CARDS[0]).scheduler_seed,
    freeze_id=FREEZE_ID,
)
directory = runs_root / TRACK.value / COLLECTION_ID
print(f"Collection {spec.collection_id} on track {spec.track.value}")
print(f"{len(spec.item_ids)} items x {len(spec.suts)} SUTs x "
      f"{collection.CALLS_PER_BLOCK} calls = {spec.planned_calls} planned calls")
for sut in spec.suts:
    serving = load_run_config(root / sut.card).serving
    print(f"  {serving.requested_model} via "
          f"{', '.join(serving.routing.provider_only)} ({sut.card})")
print("Environment:", dict(spec.environment))
print(f"Directory: {directory}")

# %% [markdown]
# ## Readiness
# Every reason the collection may not start. Nothing is dispatched. A MAIN
# collection also needs the registered freeze to match the instrument.

# %%
findings = collection.readiness(spec)
print("Ready." if not findings else "\n".join(f"- {f}" for f in findings))

# %% [markdown]
# ## Request preview and cost
# The 13 requests of the first scheduled block, rendered offline by the
# collection runner, and the expected cost from recorded runs only. The
# estimate states what it assumes; no price is typed in here.

# %%
first = collection.block_schedule(spec)[0]
record = collection.preview(
    collection.block_items(spec.track)[first.item_id], first.order_seed
)
print(f"First block: {first.item_id} on {first.card}, order seed {first.order_seed}")
print(f"Neutral: {record.shared.request[-1].content[:300]}")
for draft in record.drafts:
    print(f"[{draft.pressure_family}] {draft.snapshot.request[-1].content[:90]}")
print("Finals in dispatch order:", ", ".join(record.execution_order))

calibration = workload.calibration_run(runs_root)
priced = {
    sut.card: workload.recorded_runs(
        runs_root, load_run_config(root / sut.card).serving.requested_model
    )
    for sut in spec.suts
}
if calibration is None or not all(priced.values()):
    print("No recorded runs to price from; the cost is not estimated.")
else:
    estimate = workload.estimate_cost(spec, priced, calibration)
    for card, cost in estimate.per_card.items():
        print(f"  {card}: {cost:.4f} credits")
    print(f"Expected {estimate.total:.4f} credits; at most "
          f"{estimate.total * estimate.retry_ceiling_factor:.4f} with every retry")
    for assumption in estimate.assumptions:
        print(f"- {assumption}")

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
if not (directory / "spec.json").is_file():
    print("Not started.")
else:
    status = collection.collection_status(directory)
    print(f"Owner: {status.owner}; stop requested: {status.stop_requested}; "
          f"complete: {status.complete}")
    print(f"{'card':48} {'blocks':>9} {'attempts':>9} {'indet.':>7} closed paused")
    for sut in status.suts:
        print(f"{sut.card:48} {sut.recorded_blocks:>4}/{sut.scheduled_blocks:<4} "
              f"{sut.attempts:>9} {sut.indeterminate_attempts:>7} "
              f"{str(sut.closed):6} {sut.paused or ''}")
        run_dir = directory / Path(sut.card).stem
        if run_dir.exists():
            usage = workload.run_usage(run_dir)
            print(f"{'':48} {usage.input_tokens} in, {usage.output_tokens} out, "
                  f"{usage.cost:.6f} credits")
    log = directory / "worker.log"
    if log.is_file():
        print("Worker log:", log.read_text(encoding="utf-8")[-500:])

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
    print(f"run_directory = {Path(RUNS_ROOT) / TRACK.value / run_id}")

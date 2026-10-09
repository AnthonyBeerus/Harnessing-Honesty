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
# This notebook reads one explicitly selected run directory and never
# dispatches a request. It shows run identity and completeness, integrity
# failures, call lineage and retries, serving evidence, hashes, missingness and
# reconstruction discrepancies. Every value comes from
# `harnessing_honesty.observability` and `harnessing_honesty.analysis`.
#
# The record follows the elements Inspect keeps in its evaluation logs: run
# status, each sample's input and output, model usage, and error information,
# with interrupted logs kept for recovery [31]. That comparison supports the
# record's coverage; it did not determine the design. See
# [Sources for the methods](../docs/method-sources.md#scoring-inference-and-records).

# %%
from collections import Counter
from pathlib import Path

from harnessing_honesty import REPO_ROOT
from harnessing_honesty.analysis.reconstruct import (
    loop_record_from_run,
    matrix_record_from_run,
    run_blocks,
)
from harnessing_honesty.domain.matrix import matrix_conditions
from harnessing_honesty.observability.integrity import check_integrity
from harnessing_honesty.observability.reconstruct import reconstruct_run

root = REPO_ROOT
# For example Path("data/runs/main/main-2026-10-09/qualification.gpt4o.openai").
run_directory = None  # Set an explicit Path relative to the repository root.
SHOW_ATTEMPTS = 20  # attempts listed in full below; a MAIN run has about 1,380
run_path = None if run_directory is None else root / run_directory
attempts = issues = ()  # filled below once a run is selected
if run_path is None:
    print("No run selected. No audit results are available.")

# %% [markdown]
# ## Identity and completeness
# A run is complete only when it closed. Attempts without an outcome are
# indeterminate: the provider may or may not have answered.

# %%
if run_path is not None:
    run = reconstruct_run(run_path)
    attempts = run.attempts
    record = run.record
    print(f"Input: {run_path}")
    print(f"Run: {record.run_id}; track {record.track}; status {record.status}")
    print(f"Requested model: {record.requested_model}")
    print(f"Config hash: {record.config_hash}")
    print(f"Logical calls: {len({a.call_id for a in attempts})}; attempts: {len(attempts)}")
    print(f"Outcomes: {dict(Counter(a.outcome for a in attempts))}")
    print(f"Indeterminate attempts: {sum(a.indeterminate for a in attempts)}")

# %% [markdown]
# ## Integrity
# The first issue names the cause; later issues may follow from it.
# Reconstruction refuses a run with any issue.

# %%
if run_path is not None:
    issues = check_integrity(run_path)
    for issue in issues:
        print(f"{issue.kind.value} at {issue.where}: {issue.detail}")
    print(f"{len(issues)} integrity issues")

# %% [markdown]
# ## Lineage and retries
# Each row is one attempt. Retries share a call; the parent is the call whose
# request plus answer the new request extends. Attempts by stage and outcome
# come first, then every retried call, then the first `SHOW_ATTEMPTS` rows.

# %%
if run_path is not None:
    by_stage = Counter((a.stage, a.failure.value if a.failure else a.outcome) for a in attempts)
    for (stage, result), count in sorted(by_stage.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        print(f"{stage}: {result} x{count}")
    for a in attempts:
        if a.attempt > 1:
            print(f"retried: {a.call_id} #{a.attempt} {a.stage} {a.cell_identity}")
    for a in attempts[:SHOW_ATTEMPTS]:
        result = a.failure.value if a.failure else a.outcome
        print(f"{a.call_id} #{a.attempt} {a.block_id} {a.stage} {a.cell_identity} "
              f"{result} parent={a.parent_call_id}")

# %% [markdown]
# ## Serving evidence and hashes
# Observed fields are `None` when the response did not state them. Request and
# envelope hashes are those recorded at dispatch; integrity checks the files.
# The distinct observed models, endpoints, snapshots and cache states come
# first, then the first `SHOW_ATTEMPTS` attempts in full.

# %%
if run_path is not None:
    for field in ("observed_model", "observed_endpoint", "observed_snapshot", "cache_status"):
        print(f"{field}: {dict(Counter(getattr(a, field) for a in attempts))}")
    for a in attempts[:SHOW_ATTEMPTS]:
        tokens = a.usage.model_dump() if a.usage else None
        print(f"{a.call_id} #{a.attempt}: {a.observed_model} via {a.observed_endpoint}; "
              f"snapshot {a.observed_snapshot}; cache {a.cache_status}; "
              f"finish {a.finish_reason}; usage {tokens}")
        print(f"    request {a.request_hash}; prefix {a.prefix_hash}; "
              f"envelope {a.envelope_ref} {a.envelope_hash}")

# %% [markdown]
# ## Missingness and reconstruction discrepancies
# Each matrix or loop block is rebuilt from saved requests and raw outcomes.
# Slots that were never filled or ended indeterminate are missing. A discrepancy is an
# attempt whose raw text, parsed again, disagrees with its recorded outcome.

# %%
if run_path is not None:
    disagreements = [a for a in attempts if a.parse_agrees is False]
    for a in disagreements:
        print(f"parse discrepancy: {a.call_id} #{a.attempt} {a.outcome} {a.raw_response!r}")
    print(f"{len(disagreements)} parse discrepancies")
    if issues or not any(a.stage for a in attempts):
        print("No block rebuilt: integrity issues or no stage labels.")
    else:
        # A collection run holds a matrix block, and may hold a loop block, per
        # item; each is rebuilt by its kind.
        conditions = matrix_conditions()
        families = len({condition.pressure for condition in conditions})
        for block_id, (_, loop) in run_blocks(reconstruct_run(run_path)).items():
            if loop:
                loops = loop_record_from_run(run_path, block_id)
                turns = [len(policy_loop.turns) for policy_loop in loops.loops]
                print(f"{block_id}: loop turns present {turns}, of {families} each")
                continue
            matrix = matrix_record_from_run(run_path, block_id)
            print(f"{block_id}: drafts present {len(matrix.drafts)} of {families}; "
                  f"finals present {len(matrix.branches)} of {len(conditions)}")

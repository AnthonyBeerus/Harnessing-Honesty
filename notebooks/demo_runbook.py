# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     kernelspec:
#       display_name: Harnessing Honesty
#       language: python
#       name: harnessing-honesty
#     notebook_metadata_filter: kernelspec,language_info
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   language_info:
#     name: python
# ---

# %% [markdown]
# # Harnessing Honesty: demonstration walkthrough
#
# An assistant can abandon a correct answer under unsupported user pressure.
# A checking policy may repair those concessions while damaging answers that
# had already resisted. The study therefore compares policies on identical
# drafts, scores them against a private key, and evaluates repair and
# preservation together.
#
# This notebook brings the main evidence together. Running its cells in order
# executes the existing analysis notebooks in fresh kernels and displays
# selected outputs here; complete outputs and provenance are saved separately.
# No model calls or collection-control actions are enabled. Preparing the
# outputs takes a few minutes.

# %% [markdown]
# ## Setup and evidence selection
# Use Python 3.12 and the **Harnessing Honesty** kernel. From an editable
# checkout, install once in a terminal (these commands are not executed here):
#
# ```bash
# python -m pip install -e ".[dev,notebooks]"
# python -m ipykernel install --prefix .venv --name harnessing-honesty --display-name "Harnessing Honesty"
# ```
#
# A Git clone lacks the Git-ignored provider records. Extract the supplied
# evidence package at its original relative paths for the archived report.
# Availability is checked below; it does not authenticate the supplied hashes.
# The selected-run audit checks MAIN integrity; exploratory transport records
# have the weaker provenance documented in notebook 07.

# %%
import hashlib
import json
import re
import sys
import time
from typing import Any
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path

import jupytext
import nbformat
from IPython.display import Markdown, display
from nbclient import NotebookClient

from harnessing_honesty import REPO_ROOT

root = REPO_ROOT
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
from scripts.demo_evidence import archived_ready
from scripts.demo_notebooks import configure

# Choose "archived", "synthetic", or "collection". Both default paths are offline.
MODE = "archived" if archived_ready(root, include_legacy=True) else "synthetic"
COLLECTION = None  # e.g. root / "data/runs/dev/my-finished-experiment"
STABILITY = None  # that experiment's declared repeat, or None
KERNEL = "harnessing-honesty"

if MODE not in ("archived", "synthetic", "collection"):
    raise ValueError("Select archived, synthetic or collection mode")
if MODE == "collection" and COLLECTION is None:
    raise ValueError("Set COLLECTION to a finished development collection")
if MODE != "collection" and (COLLECTION is not None or STABILITY is not None):
    raise ValueError("Custom selections belong to collection mode")
if MODE == "archived" and not archived_ready(root, include_legacy=True):
    raise FileNotFoundError("Install the complete archived evidence bundle")

selected = Path(COLLECTION).resolve() if COLLECTION is not None else None
repeat = Path(STABILITY).resolve() if STABILITY is not None else None
audited_collection = root / "data/runs/main/main-2026-10-09" if MODE == "archived" else selected
audit_run = None
if audited_collection is not None:
    from harnessing_honesty.evaluation.collection import load_collection, sut_run_id
    spec, _ = load_collection(audited_collection)
    audit_run = audited_collection.parent / sut_run_id(spec, spec.suts[0].card)

output = root / "data/notebooks" / ("walkthrough-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
output.mkdir(parents=True, exist_ok=False)
execution: dict[str, Any] = dict(mode=MODE, collection=str(selected) if selected else None,
                 stability=str(repeat) if repeat else None, model_calls=False,
                 python=sys.version, kernel=KERNEL,
                 packages=dict(sorted((d.metadata['Name'], d.version) for d in distributions())), notebooks={})
print(f"Mode: {MODE}; new outputs: {output}")
if MODE == "synthetic":
    print("Synthetic pipeline demonstration: no recorded-model findings will be shown.")
elif MODE == "collection":
    print("Custom collection: archived report diagnostics are disabled.")

# %% [markdown]
# ### How the steps run
# Each step reuses an existing notebook rather than duplicating its analysis.
# The complete notebook runs, but only selected outputs appear here. A step can
# receive explicit settings, such as the small experiment below; they are
# applied after the safety overrides and recorded in the manifest.
# The manifest records source and effective-cell hashes, packages, completion
# and duration. Re-running a step writes a new numbered copy, preserving its
# previous output. Collection switches are forced off in the execution copy.

# %%
def execute_step(name, settings=None):
    """Run one step notebook; `settings` assigns named top-level variables after the safety overrides."""
    settings = dict(settings or {})
    if settings.get("LAUNCH") == "True" and settings.get("CLIENT") != '"synthetic"':
        raise ValueError("This notebook launches synthetic collections only; paid runs belong to notebook 05")
    source = root / "notebooks" / (name + ".py")
    notebook = configure(jupytext.read(source), MODE, selected, repeat, audit_run)
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        for switch in ("LAUNCH", "REQUEST_STOP", "RESUME"):
            cell.source = re.sub(rf"(?m)^{switch}(?:: bool)? = .*", f"{switch} = False", cell.source)
        cell.source = re.sub(r"(?m)^CLEAR_PAUSE_CARD.* = .*", "CLEAR_PAUSE_CARD = None", cell.source)
        cell.source = re.sub(r"(?m)^APPROVED_CALLS.* = .*", "APPROVED_CALLS = None", cell.source)
        cell.source = re.sub(r'(?m)^CLIENT = .*', 'CLIENT = "synthetic"', cell.source)
        for variable, expression in settings.items():
            cell.source = re.sub(rf"(?m)^{variable}(?::[^=\n]+)? = .*", lambda _: f"{variable} = {expression}", cell.source)
    number = len(execution['notebooks']) + 1
    identity = f"{number:02d}-{name}"
    entry: dict[str, object] = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                 effective_cells_sha256=hashlib.sha256(json.dumps([c.source for c in notebook.cells]).encode()).hexdigest(),
                 status="started", settings=settings)
    execution['notebooks'][identity] = entry
    manifest = output / "execution.json"
    manifest.write_text(json.dumps(execution, indent=2), encoding="utf-8")
    start = time.monotonic()
    try:
        NotebookClient(notebook, timeout=600, kernel_name=KERNEL,
                       resources={"metadata": {"path": str(root)}}, allow_errors=False).execute()
        entry['status'] = "completed"
    except Exception as error:
        entry.update(status="failed", error=str(error))
        raise
    finally:
        entry['seconds'] = round(time.monotonic() - start, 2)
        nbformat.write(notebook, output / (identity + ".ipynb"))
        manifest.write_text(json.dumps(execution, indent=2), encoding="utf-8")
    print(f"{name}: completed ({entry['seconds']} s); full output {identity}.ipynb")
    return notebook


def present(notebook, patterns, rich_limit=None, images_only=False):
    """Display selected executed outputs, bounding lengthy audit text/tables."""
    count = 0
    for cell in notebook.cells:
        if cell.cell_type != "code" or not any(p in cell.source for p in patterns):
            continue
        for item in cell.get('outputs', []):
            if item.output_type == "stream":
                text = item.text
                print(text[:2400] + ("\n[Full output in the saved step notebook.]" if len(text) > 2400 else ""))
            elif item.output_type in ("display_data", "execute_result"):
                if images_only and not any(key.startswith('image/') for key in item.data):
                    continue
                if rich_limit is None or count < rich_limit:
                    display(dict(item.data), raw=True)
                    count += 1


# %% [markdown]
# ## Run a small experiment
# The notebooks that ran the study can also run a new experiment. The next
# cell runs notebook 05 to plan and preview a small selection of the frozen
# items, launches that collection, waits for it to finish, audits one system's
# run with notebook 02 and analyses the collection with notebook 04, showing
# selected outputs from each. The launch happens in this notebook's kernel,
# using the same calls as notebook 05: a collection worker started inside a
# step notebook would stop when that notebook's kernel closes.
#
# The client is synthetic: it returns scripted answers without contacting a
# provider, so the run costs nothing and its rates test the pipeline, not any
# model. Set `RUN_EXPERIMENT = True` to run it. Paid collections are launched
# only from notebook 05, with an explicit call approval.

# %%
RUN_EXPERIMENT = False
EXPERIMENT_ITEMS = 2  # frozen items to include; each adds 69 synthetic calls

if RUN_EXPERIMENT:
    from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
    from harnessing_honesty.compiler.pool import confirmatory_pool
    from harnessing_honesty.domain.enums import Track
    from harnessing_honesty.evaluation import specification
    from harnessing_honesty.evaluation.collection import collection_status, launch, start_or_reuse, sut_run_id
    from harnessing_honesty.evaluation.live import RUNS_ROOT
    from harnessing_honesty.evaluation.workload import status_text

    experiment_id = "demo-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    experiment_items = tuple(item.item_id for item in confirmatory_pool())[:EXPERIMENT_ITEMS]
    experiment_spec = specification.selection(
        experiment_id, Track.DEV, PRIMARY_SERVING_CARDS, experiment_items, freeze_id=None)
    experiment_control = execute_step("05_experiment_control", {
        "COLLECTION_ID": repr(experiment_id),
        "ITEM_IDS": repr(experiment_items),
    })
    present(experiment_control, ["workload.plan_text", "First {kind}"])

    experiment_directory = start_or_reuse(RUNS_ROOT, experiment_spec)
    launch(experiment_directory, approved_calls=experiment_spec.planned_calls, client="synthetic")
    print(f"Launched {experiment_id}: {experiment_spec.planned_calls} synthetic calls")
    deadline = time.monotonic() + 600
    while not collection_status(experiment_directory).complete:
        if time.monotonic() > deadline:
            raise TimeoutError(f"{experiment_id} did not complete; see notebook 05's status section")
        time.sleep(2)
    print(status_text(experiment_directory))

    experiment_run = experiment_directory.parent / sut_run_id(experiment_spec, experiment_spec.suts[0].card)
    experiment_audit = execute_step("02_run_audit", {"run_directory": f"Path({str(experiment_run)!r})"})
    present(experiment_audit, ["run.record", "issues = check_integrity"])

    experiment_results = execute_step("04_results", {
        "COLLECTION": f"Path({str(experiment_directory)!r})",
        "STABILITY_RUN": "None",
        "ARCHIVED_REPORT_DIAGNOSTICS": "False",
    })
    present(experiment_results, ["report.summaries"])
else:
    print("No experiment requested. Set RUN_EXPERIMENT = True to run a synthetic one.")

# %% [markdown]
# ## 1. Instrument: what counts as a concession?
# This section summarises the frozen technical items: their balanced private
# keys and the checks applied to them.
# A capitulation requires a correct neutral start followed by a wrong answer
# under unsupported pressure. A wrong neutral answer corrected later is a
# different event. Sixty items share twelve archetypes; textual uniqueness
# does not make them sixty independent task designs.

# %%
instrument = execute_step("01_instrument_audit")
present(instrument, ["name_masked_total"], rich_limit=1)

# %% [markdown]
# ## 2. Power gate: what may the study conclude?
# The gate shown is the recorded planning result, not one recomputed after the
# outcomes were seen.
# In this study every registered contrast became estimation-only before MAIN.
# A favourable point estimate or interval does not confirm a hypothesis.

# %%
power = execute_step("03_power")
present(power, ["matches the record", "confirmatory", "Analysis code: current"])

# %% [markdown]
# ## 3. Architecture and intervention
# One neutral answer feeds three pressure branches. Each identical pressured
# draft feeds re-ask, self-check and external-report finals. The experiment
# controls the workflow; the model does not choose or execute a tool.
# MAIN's external report is an answer-equivalent ceiling. Its scoring key is
# private, whereas the deliberately supplied verdict is the treatment.
# [Architecture boundaries](../docs/architecture-boundaries.md) compares this
# fixed workflow with common agent-harness patterns.

# %%
control = execute_step("05_experiment_control")
present(control, ["architecture_paths", "workload.plan_text", "First {kind}"], rich_limit=2)

# %% [markdown]
# ## 4. Evidence audit: can the recorded run be reconstructed?
# The selected collection supplies the first system's run automatically. The
# output reports completeness, serving identity and integrity. Synthetic mode
# has no selected provider run and must not make an integrity claim.

# %%
audit = execute_step("02_run_audit")
present(audit, ["run_directory =", "run.record", "issues = check_integrity", 'for field in'])

# %% [markdown]
# ## 5. Outcome: repair must be considered alongside harm
# The registered contrasts come first, followed by repair of conceded drafts
# and damage to held drafts, which are different selected populations. Positive
# paired net benefit means fewer wrong finals; the registered regressive-shift
# contrast has the opposite sign convention. The repeat uses the same items
# and checks variability, not independent replication.
#
# Synthetic mode illustrates the estimator only; recorded-result plots require
# archived mode or a finished custom collection.

# %%
results = execute_step("04_results")
present(results, ['No power record:', '4-2g_contrasts', '4-2c_repair_and_harm', '4-2h_break_even'])

# %% [markdown]
# ### Diagnostic: correction or answer preference?
# In the archived MAIN records, GPT-4o self-check answers yes in 179/180 finals.
# High conditional repair can coexist with held-answer harm and low overall
# discrimination. Always-yes/no lines are calculated references, not new model
# observations. Direction-conditioned transitions describe behaviour, not
# internal reasoning or real user expertise. This extension is disabled for
# custom collections; it must never substitute report data for a new run.

# %%
present(results, ["answer_audit = answer_discrimination.build()"], rich_limit=2)

# %% [markdown]
# ### Recorded conversations beside the aggregate results
# Two different GPT-4o items illustrate repair after concession and harm after
# resistance under fabricated citation. The shortest recorded questions fitting
# those trajectories were selected post hoc; they are illustrations, not
# representative samples. Answers and shared histories are checked against
# recorded requests and responses. The lower panels retain the original MAIN
# populations and interval procedure. This section runs only in archived mode.

# %%
if MODE == "archived":
    from IPython.display import Image
    from scripts import conversation_results_figure
    conversation_data = conversation_results_figure.build()
    conversation_charts = conversation_results_figure.figures(conversation_data)
    display(Image(filename=str(conversation_charts[0])))
else:
    print("Recorded MAIN conversation examples skipped outside archived mode.")

# %% [markdown]
# ### H2: does policy benefit depend on pressure?
# This explicitly exploratory extension evaluates the proposal's pressure
# interaction. It includes both repair and preservation on correct-neutral
# starts, with whole-item intervals and a same-item repeat sensitivity check.
# It runs only on the archived evidence, never on a custom experiment's behalf.

# %%
if MODE == "archived":
    h2_results = execute_step("08_h2_pressure_analysis")
    present(h2_results, ['benefit = main[', 'interactions = main['], rich_limit=2, images_only=True)
else:
    h2_results = None
    print("Archived exploratory H2 analysis skipped outside archived mode.")

# %% [markdown]
# ## 6. External benchmarks: does the intervention travel?
# The charts show adapted SycoBench/PARROT concession, then accuracy across both
# neutral starting states. The external four-option report excludes one option,
# so it is not MAIN's answer-equivalent ceiling. Adaptive SycoBench suggestions
# are false after correct starts and truthful after wrong starts. Its all-start
# suggestion accuracy is therefore not a false-pressure-only measure.
#
# On GPT-4o PARROT the report corrects 7/27 wrong neutral starts but preserves
# only 86/103 correct starts, giving 93/130 overall versus 101/130 under re-ask.
# This is a benefit/cost observation, not proof of a mechanism. These numbers
# belong to the archived report; this section skips in custom/synthetic modes.

# %%
transfer = execute_step("07_transfer_checks")
present(transfer, ["stem_rates =", "external_full = external_behavior_audit.build()"], rich_limit=4, images_only=True)

# %% [markdown]
# ### External pressure moderation and category effects
# SycoBench provides an analogous pressure comparison, with matched instances
# and stem intervals. PARROT provides category effects under a single pressure.
# Neither directly replicates MAIN's fabricated-citation hypothesis. GPT-4o's
# external report helps under SycoBench doubt/authority but harms under wrong
# suggestion; on PARROT, gains after wrong neutral starts coexist with harm
# after correct starts. These additions use archived records only.

# %%
if MODE == "archived":
    present(h2_results, ['external_charts =', 'parrot = external_table['], rich_limit=2, images_only=True)
else:
    print("Archived external moderation analysis skipped outside archived mode.")

# %% [markdown]
# ## Contribution, limitations and the next experiment
# The contribution is a reproducible joint evaluation of repair and preservation.
# It survives even if the candidate explanations receive no independent support.
# Actual user knowledge, an isolated report-referent effect and internal model
# mechanisms were not measured. Prospective studies need pressure-free repeated
# controls, counterbalanced answer direction, explicit report referents and
# separately manipulated expertise cues. Exploratory explanations remain
# hypothesis-generating.

# %% [markdown]
# ## Checks and complete outputs
# Every executed step should complete. Open the saved step notebooks for the full
# calculations, detailed tables and additional charts. The manifest is a record
# of this execution, not a new authenticated experimental freeze.

# %%
assert len(execution['notebooks']) >= 6
assert all(e['status'] == 'completed' for e in execution['notebooks'].values())
print(f"All {len(execution['notebooks'])} executed steps completed; mode={MODE}; no model calls.")
print(f"Execution manifest: {output / 'execution.json'}")

# %% [markdown]
# ## Use this notebook for another experiment
# For a quick synthetic run, use "Run a small experiment" above. For a fuller
# selection or a paid run:
#
# 1. Open [05 experiment control](05_experiment_control.ipynb). Choose a new
#    `COLLECTION_ID`, `Track.DEV`, items/cards and the synthetic client for an
#    offline rehearsal. Launch only after setting its explicit switches and
#    exact planned-call approval; wait for `complete: True`.
# 2. In this notebook set `MODE = "collection"`, `COLLECTION` to that finished
#    directory and `STABILITY` to its own declared repeat, or `None`.
# 3. Restart the kernel and run this notebook from the top. Custom results get
#    fresh derived outputs; archived diagnostics and external results skip.
#
# The detailed notebooks remain the editable controls and analyses. A new
# instrument, pressure wording or persona manipulation needs a separate design
# and validation. Live collection is opt-in and may incur API costs; this
# walkthrough never launches it.

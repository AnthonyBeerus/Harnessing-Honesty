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
# An assistant can give up a correct answer when a user pushes back with a claim that adds no evidence. Asking it to check its answer may win back some of those answers, but it can also break answers the model had defended. The study therefore gives every policy the same pressured reply, scores the results against a private answer key, and reports repairs and damage side by side.
#
# This notebook gathers the main evidence in one place. Running its cells in order runs the analysis notebooks in fresh kernels and shows selected outputs here. Their full outputs are saved separately. Nothing here calls a model or starts a paid collection. Preparing the outputs takes a few minutes.

# %% [markdown]
# ## Setup and evidence selection
# Use Python 3.12 and the **Harnessing Honesty** kernel. Install once from a terminal at the repository root (this cell does not run these commands):
#
# ```bash
# python -m pip install -e ".[dev,notebooks]"
# python -m ipykernel install --prefix .venv --name harnessing-honesty --display-name "Harnessing Honesty"
# ```
#
# A fresh clone does not contain the recorded runs. To reproduce the report, extract the evidence bundle from OSF at its original paths, as the README describes. The check below confirms that the files are present, but it does not verify their hashes.

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
# Each step runs one of the existing notebooks rather than repeating its analysis. The whole notebook runs, and only selected outputs appear here. A step can also receive explicit settings, as the small experiment below does. Those settings are applied after the safety overrides, which always switch collection launches off, and they are recorded in the manifest.
#
# The manifest also records each step's source hash, packages, completion and duration. Running a step again writes a new numbered copy, so earlier outputs are kept.

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
# The same notebooks that ran the study can run a new experiment. With `RUN_EXPERIMENT = True`, the next cell uses notebook 05 to plan and preview a small selection of the frozen items, launches the collection, and waits for it to finish. It then audits one model's run with notebook 02 and analyses the collection with notebook 04.
#
# The client is synthetic: it returns scripted answers without contacting a provider. The run therefore costs nothing, and its rates test the pipeline rather than any model. The launch happens in this notebook's own kernel, because a collection started inside a step notebook would stop when that notebook closes. Paid collections can only be launched from notebook 05, with an explicit call approval.

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
# This section summarises the sixty frozen technical items, their balanced answer keys and the checks applied to them.
#
# A concession needs a correct first answer that turns wrong under pressure. A wrong first answer that later becomes right is a different event. The sixty items come from twelve templates, so they are not sixty independent task designs.

# %%
instrument = execute_step("01_instrument_audit")
present(instrument, ["name_masked_total"], rich_limit=1)

# %% [markdown]
# ## 2. Power gate: what may the study conclude?
# The gate shown here is the planning result recorded before data collection, not one recalculated after the results were seen. It found the sample too small to confirm the planned comparisons, so every registered contrast is reported as an estimate.

# %%
power = execute_step("03_power")
present(power, ["matches the record", "confirmatory", "Analysis code: current"])

# %% [markdown]
# ## 3. Architecture and intervention
# Each item's first answer is challenged in three separate branches. Each pressured reply is then finished in three ways: a re-ask, a self-check or an external report. The harness controls every step, and the model never chooses or runs a tool.
#
# In the main run, the external report states the correct verdict, so it shows the best case for good feedback. The answer key used for scoring stays private. [Architecture boundaries](../docs/architecture-boundaries.md) compares this fixed workflow with common agent-harness designs.

# %%
control = execute_step("05_experiment_control")
present(control, ["architecture_paths", "workload.plan_text", "First {kind}"], rich_limit=2)

# %% [markdown]
# ## 4. Evidence audit: can the recorded run be reconstructed?
# The audit takes the first model's run from the selected collection and reports its completeness, the models that actually served it, and its integrity checks. Synthetic mode has no recorded provider run, so it makes no integrity claim.

# %%
audit = execute_step("02_run_audit")
present(audit, ["run_directory =", "run.record", "issues = check_integrity", 'for field in'])

# %% [markdown]
# ## 5. Outcome: repair must be considered alongside harm
# The registered contrasts come first. Repair of conceded replies and damage to defended replies follow. These are different groups of replies, so their rates are not directly comparable.
#
# Two sign conventions appear. In the paired net benefit, a positive value means fewer wrong final answers. In the registered contrasts, a negative value means the same thing. The repeat run uses the same items, so it checks run-to-run variation rather than replicating the study.
#
# Synthetic mode only illustrates the calculations. Plots of recorded results need archived mode or a finished collection of your own.

# %%
results = execute_step("04_results")
present(results, ['No power record:', '4-2g_contrasts', '4-2c_repair_and_harm', '4-2h_break_even'])

# %% [markdown]
# ### Diagnostic: correction or answer preference?
# In the main run, GPT-4o's self-check answered yes in 179 of 180 final answers. A policy like that can show high repair and high harm at the same time. The always-yes and always-no lines are calculated reference rules, not extra model runs.
#
# This section only runs on the archived report records. It is switched off for custom collections, so report data never stands in for a new run.

# %%
present(results, ["answer_audit = answer_discrimination.build()"], rich_limit=2)

# %% [markdown]
# ### Recorded conversations beside the aggregate results
# Two GPT-4o items show a repair after the model gave in, and a broken answer after it had held firm, both under a fabricated citation. They were chosen after the results, as the shortest examples of each pattern, so they illustrate rather than represent. The answers and shared histories are checked against the recorded requests and responses. This section runs only in archived mode.

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
# The proposal predicted that the external report would help most under a fabricated citation. That prediction was not registered, so this analysis is exploratory. It counts both repairs and preserved answers among correct first answers, and checks the result against the repeat run. It runs only on the archived records.

# %%
if MODE == "archived":
    h2_results = execute_step("08_h2_pressure_analysis")
    present(h2_results, ['benefit = main[', 'interactions = main['], rich_limit=2, images_only=True)
else:
    h2_results = None
    print("Archived exploratory H2 analysis skipped outside archived mode.")

# %% [markdown]
# ## 6. External benchmarks: does the intervention travel?
# The charts show how often models gave in on adapted SycoBench and PARROT items, then their accuracy across all starting answers. On these four-option items the external report rules out one option, so it is not the same best-case verdict as in the main run. SycoBench's suggestions are false after a correct first answer and true after a wrong one, so its overall suggestion accuracy mixes good and bad advice.
#
# On PARROT, GPT-4o's external report corrects 7 of 27 wrong first answers but keeps only 86 of 103 correct ones. That gives 93 of 130 overall, against 101 for a re-ask. This section runs only on the archived records.

# %%
transfer = execute_step("07_transfer_checks")
present(transfer, ["stem_rates =", "external_full = external_behavior_audit.build()"], rich_limit=4, images_only=True)

# %% [markdown]
# ### External pressure moderation and category effects
# SycoBench allows a pressure comparison on matched items. PARROT has a single pressure, so it shows differences between subject categories instead. Neither repeats the main run's fabricated-citation test. GPT-4o's external report helps under SycoBench's doubt and authority pressures but hurts under a wrong suggestion. On PARROT, its gains on wrong first answers come with losses on correct ones.

# %%
if MODE == "archived":
    present(h2_results, ['external_charts =', 'parrot = external_table['], rich_limit=2, images_only=True)
else:
    print("Archived external moderation analysis skipped outside archived mode.")

# %% [markdown]
# ## Contribution, limitations and the next experiment
# The contribution is a reproducible way to measure both what a check repairs and what it breaks. That holds even if the candidate explanations offered here turn out to be wrong.
#
# The study did not measure users' actual knowledge, the effect of the report's wording on its own, or anything inside the models. A follow-up would need repeated runs without pressure as a baseline, balanced yes and no answers, reports that name the claim they judge, and expertise cues varied separately. The explanations offered here are hypotheses to test.

# %% [markdown]
# ## Checks and complete outputs
# Every step should report as completed. The saved step notebooks contain the full calculations, tables and extra charts. The manifest records this run of the notebook; it is not a new signed freeze.

# %%
assert len(execution['notebooks']) >= 6
assert all(e['status'] == 'completed' for e in execution['notebooks'].values())
print(f"All {len(execution['notebooks'])} executed steps completed; mode={MODE}; no model calls.")
print(f"Execution manifest: {output / 'execution.json'}")

# %% [markdown]
# ## Use this notebook for another experiment
# For a quick synthetic run, use **Run a small experiment** above. For a larger selection or a paid run:
#
# 1. Open [05 experiment control](05_experiment_control.ipynb). Choose a new `COLLECTION_ID`, `Track.DEV`, your items and models, and the synthetic client for an offline rehearsal. Launching needs the launch switch and the exact planned call count. Wait for `complete: True`.
# 2. In this notebook, set `MODE = "collection"`, `COLLECTION` to the finished directory, and `STABILITY` to its own repeat run or `None`.
# 3. Restart the kernel and run this notebook from the top. Your results get fresh outputs, and the archived-only sections are skipped.
#
# A new instrument, new pressure wording or a persona manipulation needs its own design and validation. Paid collections are opt-in and cost money; this notebook never launches one.

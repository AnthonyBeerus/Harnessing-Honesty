# Harness architecture

One case travels one route:

```text
configuration → cases → messages → provider → raw attempts → scores → analysis
```

Each arrow is a hand-off between packages, and each stage writes or reads one
authoritative representation, so no datum is held in two places
[[23]](references.md#wilson2014practices). Nothing downstream can change what an earlier
stage produced: scores never reach the request path, and analysis never
reaches collection.

## Two harnesses

Anthropic separates the *agent harness*, "the system that enables a model to
act as an agent", from the *evaluation harness*, "the infrastructure that runs
evals end-to-end", and names a task, a trial, a grader and a transcript
[[41, "The structure of an evaluation"]](references.md#anthropic2026evals).
Harness-Bench likewise places the evaluator outside the model–harness system
[[5, Sec. 3]](references.md#yao2026harnessbench). Here the agent harness is
the treatment: context assembly, the pressure turn and one of three
finalisation policies (re-ask, self-check or external report).
The evaluation harness assigns, records and grades it.

| Term | Inspect [[118]](references.md#inspectdocs) | This harness |
|---|---|---|
| Task / sample | dataset sample with input and target | an accepted item: public prompt, private answer key |
| Solver | produces an answer for each sample | `runtime` runners: the 13-call matrix and the policy loops |
| Trial | one attempt at a task [41] | one block: one item on one SUT |
| Scorer / grader | evaluates the output | `scoring`: exact comparison with the private key |
| Transcript / log | the complete record of a trial [41]; Inspect logs [[31]](references.md#inspectlogs) | `observability`: events, saved requests and provider envelopes |

## The route

| Stage | Package | Authoritative representation | Hands on |
|---|---|---|---|
| Configuration | `models.config`, `compiler.freeze` | serving cards in `config/`, `config/construction.json`, `config/freeze.json` | validated `RunConfig`, signed `FreezeManifest` |
| Cases | `compiler` | `data/corpus/accepted-v1.json`, checked by two independent oracles | `InstrumentItem`: `PromptView` (public) and `AnswerKey` (private) |
| Messages | `runtime` | none persisted here; the runner is deterministic given its answers | `tuple[Message, ...]` per call, built only from `PromptView` and fixed texts |
| Provider | `models` | the pinned route on each card | `ModelResult`: an answer or a typed failure, never an exception |
| Raw attempts | `observability` (driven by `evaluation`) | `events.jsonl`, `requests/`, `envelopes/` per SUT run; `spec.json` and `schedule.json` per collection | reconstructed attempts and episode records |
| Scores | `scoring` | none persisted; recomputed from raw attempts | per-cell and per-loop scores |
| Analysis | `analysis` | `data/power/assessment-v1.json` (the power gate) | rows, estimates and reports per SUT |

## Patterns

**Layers, pipes and filters.** Garlan and Shaw describe systems as pipelines
of filters joined by data streams, and as layers in which each serves the one
above it [[115, Secs. 3.1 and 3.4]](references.md#garlan1993introduction).
The route above is that pipeline; the packages are layered so that a stage
depends only on earlier ones. The rules are enforced by
[`tests/architecture/test_analysis_boundary.py`](../tests/architecture/test_analysis_boundary.py):
`domain` imports no implementation package; `runtime` and `models` import
none of `evaluation`, `compiler`, `scoring` or `analysis`; `scoring` imports
no execution package; `observability` imports neither `runtime` nor
`evaluation`; and no package outside `analysis` imports it.

**Information hiding.** Each package hides one decision that is likely to
change [[22]](references.md#parnas1972modules): the provider SDK behind
`models`, the corpus format behind `compiler`, the file layout behind
`observability`, the estimators behind `analysis`. The decision that must
never leak is the answer key: it lives in `AnswerKey`, which the request path
cannot receive. The first message is rendered from `PromptView` alone; later
turns add the pressure, the model's own answers, the policy text and, for the
external-report policy, the labelled report. That report's verdict is the
policy's declared treatment.

**Ports and adapters.** Cockburn's pattern lets an application "be driven by
users, programs, automated test or batch scripts, and … be developed and
tested in isolation from its eventual run-time devices"
[[116]](references.md#cockburn2005hexagonal). `ModelClient` is the one driven
port: the live adapter (`PydanticAIModelClient`, over Pydantic AI 1.107.1
[[43]](references.md#pydanticai11071)), the synthetic `HashedAnswerClient`
and the test `ScriptedModelClient` all satisfy it, so the same runner serves a
paid collection, an offline experiment and a unit test. The driving side is
the `evaluation` functions; the CLI, the experiment-control notebook and the
tests are three driving adapters over them, and neither the CLI nor the
notebook holds its own procedure.

**Event sourcing.** Fowler: "capture all changes to an application state as a
sequence of events" and rebuild the state by replaying them
[[117]](references.md#fowler2005eventsourcing). Each SUT run's
`events.jsonl` is append-only; its summary, the collection status, a resumed
run's position and every analysis row are projections rebuilt from the events
and saved requests, never stored scores. This is what makes an interrupted
collection resumable and a finished one auditable.

## Packages

| Package | Reason to change |
|---|---|
| `domain` | the typed contracts every stage shares: messages, results, records, events, conditions |
| `compiler` | how cases are built, checked by two oracles, reviewed and frozen |
| `runtime` | the treatment: pressure texts, finalization policies, branching and the runners |
| `models` | how a request reaches a provider and how its response is classified |
| `observability` | how evidence is written, checked for integrity and reconstructed |
| `scoring` | what counts as a valid, correct answer and how a cell or loop is scored |
| `evaluation` | what a collection runs (`specification`), how it runs and resumes (`collection`), run sessions (`live`), cost and status text (`workload`) |
| `analysis` | estimands, the bootstrap, the secondary fit, the power gate and the loop summary |

The CLI (`cli.py`) and the notebooks sit outside the packages as driving
adapters.

## What this experiment retains and removes

The architecture figure can be rebuilt offline with
`python -m scripts.harness_architecture_figure`. It depicts MAIN's fixed
workflow, not the exploratory four-option adapters or fresh-verifier protocol.

Anthropic's public distinction between predefined workflows and model-directed
agents places this design on the workflow side
[[108]](references.md#anthropic2024agents). The treatment varies context and
finalisation after a shared draft. It does not vary autonomous planning, tool
selection, retrieval, memory or external action. Those omissions keep the
intervention identifiable, while limiting claims about production agents.

| Reference architecture | Retained here | Deliberate divergence | Evidential limit |
|---|---|---|---|
| Anthropic augmented LLM / evaluator–optimizer [108] | Model calls, explicit context and feedback | Fixed branch schedule; prevalidated report; one final call | No evidence about autonomous tool choice or iterative convergence |
| Pydantic AI 1.107.1 [43] | `Agent` as provider adapter; typed configuration and result boundaries | Plain-text output, no registered function tools; experiment runner controls policy and retries | Using an SDK is not an SDK-performance comparison |
| Inspect datasets / solvers / scorers [118] | Items, runner, separate exact-key scorer and transcripts | Local event reconstruction and private-key contracts, rather than Inspect execution | Structural comparison only; Inspect was not an experimental arm |
| Anthropic evaluation harness [41] | Task/trial separation, recorded attempts, graders and outcomes | Controlled binary instrument; oracle verdict is declared treatment information | A binary ceiling is not an estimate of realistic tool reliability |

The contribution is the controlled comparison and auditable evidence path,
rather than a new general-purpose agent framework. The four-option transfer
report rejects one named option; it leaves three alternatives and therefore
does not inherit MAIN's binary ceiling. The fresh-verifier substudy separately
changes context, wording and revision control, so it cannot isolate one of
those changes as the mechanism.

## Classes that remain

Classes are kept where a boundary needs a validated schema or state:

- **Pydantic models** for evidence and configuration whose malformation could
  alter the experiment: cards, specifications, schedules, events, records,
  results and reports. Internal values are plain tuples and functions.
- **The `ModelClient` port** and its three adapters.
- **Stateful collaborators**, each owning one piece of mutable state:
  `RunSession` and `RecordingModelClient` (the open run and its call
  counter), `RetryingClient` (the retry budget), `JsonlEventSink` (the event
  sequence), `FilesystemRecordStore` (write-once files), and in `collection`
  `_Replay` (one block's recorded calls) and `_PauseGuard` (one SUT's
  provider-failure streak).
- **Enumerations** for families, policies, stages and response states.

## External dependencies

| Dependency | Used in | Why |
|---|---|---|
| `pydantic` | every package | validation of evidence and configuration |
| `pydantic-ai` (exact pin) | `models` | the provider adapter; request construction is cited from this version's source |
| `pyyaml` | `models.config` | serving cards |
| `python-dotenv` | `models` | the API key from a local `.env`, outside saved cells |
| `z3-solver` (optional) | `compiler.oracles` | one of the two independent oracles |
| `gpboost` (exact pin), `numpy`, `scipy` (optional) | `analysis` | the secondary mixed logit, resampling and power |
| Jupyter stack (optional) | notebooks | percent-format notebooks paired with local `.ipynb` copies |

## Notebook operation

| Operation | Implementation | Input and result |
|---|---|---|
| Validate | `specification.readiness` | every reason a specification may not start; nothing is dispatched |
| Preview | `specification.preview`, `preview_loops`, `workload.plan_text` | the first block of each kind and the expected cost, rendered offline |
| Launch | `collection.start_or_reuse`, `collection.launch` | one detached worker (`python -m harnessing_honesty.evaluation.collection`), writing its own `worker-{time}.log`; a duplicate launch reports the existing state; MAIN takes the live client only |
| Status | `collection.collection_status`, `workload.status_text` | progress, ownership and pauses read from files alone |
| Stop | `collection.request_stop` | the owner stops between blocks; nothing is cut mid-call |
| Resume | `collection.resume`; `clear_pause` for a paused SUT | refused while a worker still owns the collection; continuation from the recorded events, and an uncertain call is retried under its own identity |

Notebook variables hold selections and displayed results; the accepted
specification, schedule and attempt history live in files, so changing a cell
cannot change an accepted run and a lost kernel does not stop a worker. The
CLI's `collection-*` commands call the same functions, and notebook/CLI
equivalence is tested on the same synthetic selection
([`tests/test_notebook_cli_equivalence.py`](../tests/test_notebook_cli_equivalence.py)).
The synchronous live client runs outside Jupyter's event loop
(`Agent.run_sync` [[43]](references.md#pydanticai11071)), which the worker
process provides.

## Limits of the evidence

The import rules constrain static dependencies, not every information flow:
dynamic imports, arguments passed through shared contracts and the contents of
transmitted requests are checked separately: the freeze rebuild
(`accepted_freeze`) compares every prompt, template and pool hash,
[`tests/runtime/test_first_episode.py`](../tests/runtime/test_first_episode.py)
keeps the answer key unreachable from message rendering, and every request
actually sent is saved under its hash. A change to
serialized requests, branch order, fixture scores or CLI behaviour can alter
the instrument and is never treated as purely structural. Architectural
documentation and references are not experimental input: they never appear
in a prompt.

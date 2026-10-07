# Harness architecture

## Decision — 4 September 2026

Pydantic AI provides the implementation reference for model interaction,
typed output, dependencies and message handling. The architecture separates
the workflow whose behaviour is evaluated from the infrastructure that
assigns trials and measures their outcomes.

Anthropic distinguishes these responsibilities in “The structure of an
evaluation” [[41]](references.md#anthropic2026evals). Harness-Bench, Section 3,
likewise places the evaluator outside the model–harness system
[[5]](references.md#yao2026harnessbench). This distinction determines the
access rules below. Pydantic supplies the implementation conventions; the
registered experiment determines which behaviours those conventions may express.

The workflow reproduces context assembly, controlled verification, finalization
and provider interaction. Its transitions are fixed by the experimental
protocol. It does not represent the full range of autonomous agent behaviour.
The three policies are no verification, intrinsic recheck and labelled
external ceiling. Their content and scoring rules are specified by the
registered protocol.

## Pydantic implementation baseline

The implementation baseline is Pydantic AI 1.107.1 with Pydantic 2.13.4,
the versions installed on 4 September 2026.
[pyproject.toml](../pyproject.toml) pins Pydantic AI exactly: within 1.x the
`BaseNode` graph runner and its persistence are deprecated in 1.107.1
(`pydantic_graph/__init__.py`), so a range admits releases whose SDK
behaviour this source does not describe. Pydantic keeps a 2.x range; notebook
executions record its resolved version in `execution.json`
([scripts/run_notebooks.py](../scripts/run_notebooks.py)).

The versioned Pydantic AI source is the reference for concrete APIs
[[43]](references.md#pydanticai11071). In that source, `agent/__init__.py`
defines `Agent`, `deps_type` and `output_type`; `agent/abstract.py` exposes
run methods; `messages.py` defines request and response parts; `run.py`
provides recorded messages; and `usage.py` defines execution limits.
Dependence on public interfaces limits coupling to SDK internals whose
changes could alter execution independently of the experimental protocol.

| Concern | Pydantic convention | Experimental constraint and implementation status |
|---|---|---|
| Model access | `Agent`, `OpenRouterModel`, `OpenRouterProvider` | The live client uses these interfaces. Provider translation is confined to the adapter; the actual served configuration remains a separate validity condition. |
| Answer output | `output_type=str` | The provider returns plain text; the adapter retains it and accepts only `yes` or `no` into `AnswerResponse`. This avoids a response-schema tool in every arm. Pydantic AI's pinned source defines this text-output boundary [[43]](references.md#pydanticai11071); prompt-format sensitivity makes the distinction experimentally material [[14, Sec. 4]](references.md#sclar2024formatting). |
| Context | `message_history`, `ModelRequest`, `ModelResponse` | The client uses these message interfaces. Comparability depends on identical shared prefixes and isolated branch histories. Internal transcripts and translated requests provide different evidence of that correspondence. |
| Dependencies | `deps_type`, per-run `deps`, `RunContext` | Typed dependencies provide runtime services explicitly. The current agent uses `None` dependencies. Private keys, scores and aggregate results fall outside the runtime's permitted inputs. |
| Execution limits | `UsageLimits` and explicit retry configuration | SDK retries are disabled on the serving path. `RetryingClient` applies the registered parse and provider retries; each attempt is a recorded request. |
| Verification | Explicit report validation and result handling | The ceiling is supplied as fixed user-side harness content. A model-selected tool call would change the treatment and is outside this protocol [[15, Secs. 2--3]](references.md#huang2024selfcorrection), [[16, Secs. 3.2 and 8]](references.md#kamoi2024selfcorrection). |
| Records | `all_messages()`, `new_messages()` and run usage | SDK records describe model interactions; raw provider evidence establishes transport and routing properties absent from normalized messages. |
| Offline checks | `FunctionModel`, `TestModel` and overrides | These interfaces permit controlled requests and failures without live inference. Existing client conformance checks use `FunctionModel`. |

Pydantic's dependency documentation explains passing application services
through typed dependencies [[45]](references.md#pydanticdependencies).
Typing is not an access-control mechanism: a dependency carrying an answer
key would still expose it to the receiving code.

Pydantic AI Harness and its examples demonstrate composing execution
capabilities [[44]](references.md#pydanticharness),
[[46]](references.md#pydanticharnessexamples). This design adopts explicit
composition of capabilities relevant to the experiment. A capability's
effects on instructions, context, model settings and additional calls are
part of the experimental procedure. Compatibility depends on the installed
version; current documentation may describe a different interface.

## Components and information flow

| Component | Responsibility | Permitted information |
|---|---|---|
| Domain | Typed contracts | Defines public and private types separately; no provider or estimation implementations. |
| Runtime | Execute the assigned workflow | Public prompt, isolated conversation, selected finalization policy and permitted verification report. |
| Models | Translate requests and classify responses | Public messages and serving configuration; no private answer keys or scoring results. |
| Evaluation | Assign trials, order conditions and manage collection | Scenario identity, registered conditions, execution status and records. It invokes the runtime and scorer separately. |
| Compiler | Construct and validate scenarios | Task definitions, oracle evidence, private keys and the public projection supplied to execution. |
| Scoring | Classify validity and correctness | Recorded responses and private keys; no authority to modify the conversation or request another answer. |
| Observability | Persist execution evidence | Events, transmitted requests, responses and integrity metadata; no authority to choose conditions. |
| Analysis | Reconstruct and estimate offline | Completed records and scoring inputs; no dependency from collection on estimates. |
| Notebooks | Present offline analyses | Analysis notebooks call shared analysis functions and define no separate experimental procedure. |
| CLI | Assemble and invoke operations | Constructs dependencies for the selected command and delegates execution. |

The evaluation layer owns which branches are compared and their trial order.
The runtime owns the sequence within an assigned finalization procedure.
Context code owns the mechanics of copying a prefix without sharing later
mutable history. These are distinct decisions even where current functions
combine them.

A durable session is also distinct from the context sent to a model.
Anthropic's Managed Agents account makes this distinction explicit in
“The session is not Claude's context window”
[[42]](references.md#anthropic2026managed).
Recoverable transformations between recorded history and transmitted context
allow differences in model input to be distinguished from differences in
model response.

The labelled external report is an intentional information channel into the
runtime. Its permitted fields are defined by the protocol. The private
answer key and final outcome scorer remain outside that channel.

## Notebook operation

Any notebook or CLI collection control uses the interface owned by `evaluation`.
Bluesky separates interactive use from its RunEngine's execution and recording
responsibilities [[47, Sec. "The RunEngine"]](references.md#blueskytutorial).
Pydantic Evals supplies a Python interface returning evaluation reports
[[48, Sec. "Code-First Evaluation"]](references.md#pydanticevals).
The choice of a separate worker process is specific to this study: it prevents
notebook kernel state from owning the collection lifecycle.

| Interface operation | Input and result |
|---|---|
| Validate | A typed run specification produces readiness findings and a configuration identity; no calls are dispatched. |
| Preview | The specification produces request examples, condition order and workload estimates without modifying run state. |
| Launch | An explicitly approved specification produces a durable run identity and starts one worker. A duplicate request returns existing state; conflicting configuration is rejected. |
| Status | A run identity returns saved progress, attempt states, worker status and artifact locations. |
| Stop | A run identity requests a recorded stop; in-flight or indeterminate attempts retain their status. |
| Resume | A run identity permits continuation from durable state after readiness and ownership checks; uncertain dispatches are not silently repeated. |

Notebook variables hold selections and displayed results. Durable records own
the accepted specification, schedule, run identity and attempt history.
Changing a cell cannot change an accepted run. Reopening the notebook reconnects
by run identity; a lost notebook kernel does not establish that its worker stopped.
The collection service enforces ownership, duplicate protection and protocol
checks independently of both interfaces. Credentials remain outside saved cells
and outputs.

Runtime code retains branch isolation and finalization; model adapters retain
request handling; scoring retains outcome classification. Notebook/CLI equivalence
requires matching requests, schedule, retries and reconstructed outcomes on the
same deterministic fixture, with identifiers and timestamps accounted for.
The current synchronous client also requires execution outside Jupyter's active
event loop (`Agent.run_sync`, versioned source [[43]](references.md#pydanticai11071)).
Validate and Preview are implemented in `evaluation/specification.py`
(`readiness`, `preview`, `preview_loops`), which also defines the block
schedule; Launch, Status, Stop and Resume are implemented in
`evaluation/collection.py` by `launch`, `collection_status`,
`request_stop`/`clear_stop` and `clear_pause` over the persisted schedule
(`start_collection`, `execute`). `launch` starts one
detached worker process (`python -m harnessing_honesty.evaluation.collection`)
writing to its own `worker-{time}.log`. The experiment-control notebook,
`notebooks/05_experiment_control.py`, calls these functions and
`start_or_reuse`; the CLI's `collection-plan`, `collection-launch`,
`collection-status`, `collection-stop`, `collection-resume` and
`collection-clear-pause` call the same functions, and both print the plan and
status text of `evaluation/workload.py`.
Release execution of notebook checks uses offline fixtures and cannot launch
paid runs.

## Organization and alternatives

Execution, context, pressure text and finalization policies reside under
`runtime`. Scheduling, qualification and development fixtures reside under
`evaluation`. Shared episode records and condition definitions reside in
`domain`, allowing scoring to consume records without importing the runner.
Serving configuration resides beside the model adapters. The scorer exposes
its public interface through `scoring/__init__.py`; this preserves the imports
in the registered analysis source.

```text
src/harnessing_honesty/
├── cli.py                 Command selection and dependency assembly
├── domain/                Contracts, episode records and condition definitions
├── runtime/               Episode execution, branching, context and policies
├── models/                SDK adapter, serving configuration and response handling
├── evaluation/            Scheduling, qualification and development fixtures
├── compiler/              Scenario construction, oracle checks and manifests
├── scoring/               Outcome calculations and private checkers
├── observability/         Recording, storage and event reconstruction
└── analysis/              Offline reconstruction and estimation

tests/
├── architecture/          Import boundaries and package checks
├── domain/
├── runtime/
├── models/
├── evaluation/
├── compiler/
├── scoring/
├── observability/
├── analysis/
└── fixtures/              Captured response data
```

The repository-level `config/` directory contains experiment configuration;
`docs/` contains the protocol and methodological documentation. The original
OSF submission remains in `docs/baseline/`. The package name and CLI entrypoint
are unchanged. The [notebook entrypoints](../notebooks/README.md) reside outside
the runtime package. They currently expose the inventory and analysis
interfaces; substantive audits and statistical estimation remain incomplete.

This organization follows harness responsibilities rather than copying the
SDK's directory tree. Reimplementing Pydantic's agent loop or provider layer
would create a second set of semantics to maintain. Adopting a complete coding
or research harness would introduce unrelated planning, memory and delegation.
The chosen approach uses the SDK's public interfaces while keeping the
experimental procedure explicit.

Parnas's information hiding and Wilson et al.'s scientific-software practices
support keeping these responsibilities separate
[[22]](references.md#parnas1972modules), [[23]](references.md#wilson2014practices).
The harness literature supplies the primary methodological justification.
These are reasons for the present decision, not retrospective claims about
what influenced earlier implementations.

## Methodological consequences and limitations

The separation makes experimental choices traceable through their inputs,
execution and outputs. Its value depends on checks that expose unintended
changes to conditions, information flow, scoring and opportunities to retry.

Behavioural equivalence during restructuring is defined by unchanged
serialized requests, schema content, branch order, fixture scores and CLI
behaviour. A change to any of these can alter the instrument and therefore
cannot be treated as a purely structural change. Compatibility at the public
SDK interface does not by itself establish equivalence on the request path.

Existing evidence includes [client conformance](../tests/models/test_model_client_conformance.py)
and [dependency checks](../tests/architecture/test_analysis_boundary.py).
The latter resolve absolute and relative static imports, including imports
through package aliases. They prohibit dependencies from runtime and model
adapters on evaluation, compilation, scoring and analysis; from scoring on
execution; and from domain contracts on implementation packages. Imports of
analysis remain prohibited throughout the other packages.

These checks constrain source dependencies, not all possible information
flows. Dynamic imports, arguments passed through shared contracts and the
contents of transmitted requests require separate validation. Episode runners
still perform the seeded ordering of branches within a workflow; the outer
scheduler orders trial cells. The directory separation does not itself supply
the missing MAIN collector or establish serving equivalence.

Architectural documentation and scholarly references are separate from the
experimental input. Their inclusion in prompts or schema descriptions would
change the information presented to the model and could affect the measured
policy contrast.

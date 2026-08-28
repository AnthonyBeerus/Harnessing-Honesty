# Architecture boundaries

These are the boundaries the code currently enforces. Design choices that
produced them are in [research-design-decisions.md](research-design-decisions.md).
If a line below is hard to make precise, the corresponding seam is still a
protocol rather than a path.

## Layers

Dependency runs one way.

**Domain** (`harnessing_honesty.domain`) is vocabulary and invalid states.
It does not import runners, clients, scoring, or the CLI. Enums, messages,
results, scenario types, `Condition`, events, `RunRecord`, and the six
protocols live here. A type that would be illegal in a stored run fails at
construction.

**Runtime** sits on domain. Episode runners, stage transitions, pressure and
policy templates, `messages_for`, model clients, and scoring all import
domain types. None of them is imported by domain.

**CLI** (`python -m harnessing_honesty.cli`) is a thin operator surface:
`run-fake`, `show-matrix`, `run-live`. It constructs a client, calls a
runner, and prints public transcripts next to private scores. It is not a
scheduler and does not own records.

Model clients live under `harnessing_honesty.models` and satisfy
`ModelClient` by shape. They do not re-export domain types. Importing
`Message` from that package would give the type a second name.

## Analysis is walled off

`harnessing_honesty.analysis` holds `AnalysisRow`, a post-run projection:
run and scenario identity, a `Condition`, the two primary booleans, and
`draft_correct` as a stratifier. It has no answer fields.

Runtime modules must not import that package. An AST walk of every module
under `harnessing_honesty` except `analysis` fails the suite if any of them
do. Scoring can produce per-episode flags; an analysis row is a later view
of stored public answers plus the private key. That mapping is not wired
yet. The wall is real so the wiring, when it arrives, cannot pull
estimation into the episode path.

## The answer key and the two verifications

A `ScenarioRecord` is a `PromptView` plus an `AnswerKey`. `PromptView` does
not import the key. `messages_for` accepts `PromptView` only and copies
`question` into the first user turn. Episode runners take `PromptView`.
Tests read the source of those modules and fail if they name the private
type.

Scoring is the other direction. `answer_is_correct` reads
`key.canonical_answer`. The `Checker` protocol is explicit that this oracle
*should* see the key. The development checker is still a function,
`check_exact_arithmetic`, not a plugged-in `Checker` instance. The registry
in `domain.checkers` currently names one category, `logical_world`; an
unregistered category is refused when the scenario is built.

The model-visible premise check is a different protocol,
`VerificationTool.run(prompt: PromptView)`. Taking the view rather than the
record is the isolation: a tool that accepted `ScenarioRecord` could read
the canonical answer. What the development matrix actually injects is still
a constant, `DEVELOPMENT_VERIFIER_OUTPUT`, copied into a `tool`-role
message. The protocol is the intended seam; the constant is what runs
today. Tests on that constant refuse conclusion markers, which is the
remaining leak the type system cannot see (a paraphrase, not a copied
field).

## The message path

Everything the model is shown is a tuple of `Message`. Each message has a
`Role` and `content`. The type is frozen and forbids extra fields, so
`condition=`, `expected=`, or `stage=` cannot ride along.

What may write a `Message`:

- `messages_for`, which emits one user turn from `prompt.question`
- the episode runners, which append pressure text, policy text, and, in the
  three tool cells, verifier output
- `Transcript.append`, which returns a new transcript

What must not: scoring, analysis, `AnswerKey`, `Stage` labels, `Condition`
identity, track, or family names. Leak tests search serialized requests for
those strings. `id` on `PromptView` is harness identity for logs; it is not
copied into `content`.

On the wire, the live client projects `tool` onto a user-role turn. The
harness keeps the internal role so leak and symmetry checks can see
verifier output as verifier output. Synthesising a provider tool call to
avoid that projection would add an assistant turn to the tool cells only.

`complete` is total: it returns `AnswerSuccess`, `ParseFailure`, or
`ProviderFailure`, and does not raise for a bad payload or a 429. Two
counts travel with a success. `requested_message_count` is what the
harness handed over; `observed_message_count` is what a capturing client
can show reached the provider. The scripted client does not measure the
wire. The FunctionModel-backed client in the conformance suite does, which
is why that suite can fail a transport assertion the fake cannot.

## What is declared and not yet a path

`Clock`, `EventSink`, and `RecordStore` are protocols without
implementations. `RunRecord` and the event union exist as types; nothing
appends JSONL yet. `CellBinding` refuses a development scenario in a main
condition; no runner consumes that type yet. `Track.MAIN` is a value
`ScenarioRecord` and `RunRecord` can name and refuse. Those are real
invalid states. They are not yet an execution mode.

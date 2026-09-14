# Sources for the methods

This document relates the literature to the instrument as it stands on
11 September 2026. It is a retrospective account of methodological relevance.
It does not establish that a paper influenced an earlier implementation.
The dated [design decisions](research-design-decisions.md) and
[registered submission](baseline/2026-09-03/README.md) document that history.

## Sycophancy and the outcome

Sharma et al. examine agreement with user beliefs at the expense of truth;
SycEval distinguishes progressive and regressive changes in answers
[[1]](references.md#sharma2024sycophancy), [[2]](references.md#fanous2025syceval).
In [scoring.py](../src/harnessing_honesty/scoring/outcomes.py), the primary flag compares
the neutral and final answers against the private key. A correct neutral answer
followed by an incorrect final answer is a regressive shift. This operational
definition covers one response pattern. It does not measure the full range of
behaviours discussed in the sycophancy taxonomy
[[3]](references.md#ye2026taxonomy).

Question framing, repeated disagreement, evaluator rebuttals and persuasion
trajectories are studied in distinct settings
[[4]](references.md#dubois2026ask), [[10]](references.md#hong2025sycon),
[[11]](references.md#kim2025evaluator), [[12]](references.md#tan2025duetpd).
These sources inform the interpretation of pressure in
[pressures.py](../src/harnessing_honesty/runtime/pressures.py) and the limits of transfer
between tasks. They do not establish that this instrument reproduces those
benchmarks or their reported sycophancy rates.

The confirmatory compiler records the opposite answer and an item-specific
opposing claim. The private item validator requires the answer to differ from
the canonical key, and all three pressure families wrap the same proposition.
This implements the registered false-pressure contract. Sharma et al. and
SycEval motivate testing truth-displacing agreement and regressive answer
changes [[1]](references.md#sharma2024sycophancy),
[[2]](references.md#fanous2025syceval); neither source prescribes these exact
counter-position sentences.

The compiler's dependency records distinguish locally generated items from
taxonomy and checker sources. Systems cases use complete operation histories,
happens-before constraints and an executable sequential register specification
from the linearizability definitions in Horn and Kroening
[[52, Sec. 2]](references.md#horn2015linearizability). Their exhaustive search
does not implement the paper's P-compositional algorithm. Transition cases use
small old-state/new-state rule relations, a deliberately narrower substitute
for a TLA+ specification [[53, Sec. 2.2]](references.md#lamport2002specifying).
Authorization cases vary actor/action decisions in local tables; they omit
Cedar's resource, context, hierarchy and policy-combination semantics and are
therefore taxonomy-derived cases rather than Cedar evaluations
[[54, Sec. 2.3]](references.md#cutler2024cedar). Query-result comparison follows
the cross-implementation testing rationale in sqllogictest
[[55]](references.md#sqllogictest); the local join cases additionally preserve
SQLite's documented row-pair and `ON`-filter semantics
[[70, Sec. 2.1]](references.md#sqlite-select). Program traces use the short,
deterministic input-output task structure and filtering constraints in CRUXEval
[[56, Secs. 3--3.2]](references.md#gu2024cruxeval); all statements and inputs
are newly authored here. Complexity cases use BigO(Bench)'s complexity-
prediction taxonomy only [[57, Secs. 1 and 3]](references.md#chambon2025bigobench).
Its labels are inferred from profiling and regression rather than theoretical
complexity, so the repository instead uses two exact static loop-depth checkers
for its deliberately restricted pseudocode. The logic entailment cases use
newly authored facts, Horn-style rules and queries with unsupported conclusions
treated as unknown, following the RuleTaker-style theory and open-world
semantics described by ProofWriter
[[72, Secs. 3.1--3.2]](references.md#tafjord2021proofwriter). The repository uses
two deterministic chainers and does not reproduce source items, train a
reasoning model or request proofs. SAT is mapped to Z3
[[58]](references.md#demoura2008z3).
The leakage items use the clean train/test separation premise, including fitted
preprocessing, in Kapoor and Narayanan
[[59, taxonomy L1 and L1.2]](references.md#kapoor2023leakage). The accuracy
cases use the ordinary exact-match fraction and an independently accumulated
confusion-matrix diagonal, consistent with the published software definitions
[[71, Secs. 3.4.4.2 and 3.4.4.6]](references.md#sklearn-model-evaluation).
These are repository-specific examples and independent local checkers, not
scikit-learn calls. Hoare's rule of iteration supplies the loop-invariant
taxonomy [[60, Sec. 3.4]](references.md#hoare1969axiomatic); the bounded
subtraction loops and non-negativity claims are local constructions. None of
these references supports a claim that public benchmark items were reproduced.

## Finalization and verification

Intrinsic self-correction can fail without useful external feedback;
the distinction between internal and external feedback matters when comparing
correction methods [[15]](references.md#huang2024selfcorrection),
[[16]](references.md#kamoi2024selfcorrection).
[policies.py](../src/harnessing_honesty/runtime/policies.py) defines a final-answer
request, an intrinsic recheck and a labelled external ceiling. Its recheck is
not the iterative feedback procedure in Self-Refine, and its external report
is not the verification-question procedure in Chain-of-Verification
[[17]](references.md#madaan2023selfrefine),
[[13]](references.md#dhuliawala2024verification).

The current working amendment makes the intrinsic condition one prompted
metacognitive self-check using only the supplied premises. The external
condition instead receives a deterministic, labelled report from the harness;
the model does not select or call a tool. The none condition receives only the
minimal final-answer request. This preserves distinct information conditions.
Huang et al. distinguish intrinsic correction without external feedback from
externally assisted correction
[[15, Secs. 2--3]](references.md#huang2024selfcorrection), and Kamoi et al.
require that oracle-fed methods be identified as external
[[16, Secs. 3.2 and 8]](references.md#kamoi2024selfcorrection).

Every call now elicits exactly one plain-text `yes` or `no`; validation into
`AnswerResponse` occurs after receipt and the unmodified response is retained.
Sharma et al. elicited confidence separately and discarded it from the
sycophancy evaluation
[[1, Sec. 3.2 and App. A.4]](references.md#sharma2024sycophancy).
Turpin et al. show that displayed chain-of-thought can rationalize answers
steered by biasing prompt features
[[68, Secs. 3.1--3.3]](references.md#turpin2023unfaithful).
Dubois et al. use a minimal single-symbol response in a choice-based
sycophancy test and show that framing changes measured behaviour
[[4, Secs. 3 and 4.2.3]](references.md#dubois2026ask). Sclar et al. independently
show substantial prompt-format sensitivity
[[14, Sec. 4]](references.md#sclar2024formatting). These results justify
removing confidence, rationale, JSON formatting and response-schema tools from
the model-visible contract; they do not imply that binary prompting eliminates
all measurement effects. Anthropic's current guidance likewise recommends
stating the desired output format and constraints explicitly
[[69, "Be clear and direct"]](references.md#anthropic2026prompting). The shared
whole-response instruction applies that transport guidance without introducing
a provider-specific scientific contract. It is repeated on the pressure
message because that message initiates the shared draft call; leaving the
latest user turn as an assertion alone does not specify that a new binary
response is required.

The pressure draft recorded by
[episode.py](../src/harnessing_honesty/runtime/episode.py) precedes finalization.
An incorrect draft followed by a correct final answer describes recovery;
a correct draft that remains correct describes maintenance. The pooled
neutral-to-final outcome does not distinguish them. This distinction follows
from the instrument's sequence and scoring definitions, rather than an
estimator borrowed from one of these papers.

## Harness and serving configuration

Harness-Bench, the harness-disclosure position paper, Meta-Harness and work on
trajectory-level alignment examine how execution procedures affect results
[[5]](references.md#yao2026harnessbench),
[[6]](references.md#zhang2026disclosing),
[[7]](references.md#lee2026metaharness),
[[8]](references.md#wang2026trajectories).
They support describing the evaluated model together with its harness.
Their agent workflows and optimization procedures differ from this study's
fixed finalization policies. Prompt-format sensitivity supplies a separate
reason to preserve the exact messages and plain-text response contract
[[14]](references.md#sclar2024formatting).

The [live client](../src/harnessing_honesty/models/pydantic_ai_client.py)
and [routing configuration](../src/harnessing_honesty/models/routing.py) should
be assessed against OpenRouter's provider-selection and routing-metadata
interfaces [[32]](references.md#openrouterrouting),
[[34]](references.md#openroutermetadata).
Response caching can replay an answer. Provider prompt caching reuses prompt
processing and has separate usage and routing implications
[[33]](references.md#openroutercaching),
[[40]](references.md#openrouterpromptcaching).
These citations specify the service behaviour to account for; they do not
certify that every required setting is transmitted or every field retained.
Point citations in the [live adapter](../src/harnessing_honesty/models/pydantic_ai_client.py)
identify the OpenRouter routing fields, generation metadata and installed
Pydantic AI boundary [[32]](references.md#openrouterrouting),
[[34]](references.md#openroutermetadata), [[43]](references.md#pydanticai11071).
The [development live smoke](../notebooks/development/live_api_smoke.py) calls
that adapter through the CLI. It is a request-path diagnostic, not an evaluation.

Model equality testing requires evidence about output distributions
[[20]](references.md#gao2025equality). A provider label or successful
[qualification probe](../src/harnessing_honesty/evaluation/qualification.py) is not such
a test. QuaRot demonstrates a particular quantized implementation
[[18]](references.md#ashkboos2024quarot); citing it establishes neither the
quantization method nor numerical precision of an evaluated endpoint.

## Scoring, inference and records

MT-Bench documents limitations of model-based judging
[[19]](references.md#zheng2023mtbench). The primary scorer here uses the private
answer key, so it is not an implementation of that judging procedure.

[formula.py](../src/harnessing_honesty/analysis/formula.py) currently computes
rates and contrasts. It does not fit the proposed mixed model or calculate
cluster-aware uncertainty. Cluster-robust inference provides background on
dependence within groups [[29]](references.md#mackinnon2023cluster).
Gaussian Process Boosting describes the GPBoost framework
[[30]](references.md#sigrist2022gpboost); the separate GPModel API documents
grouped random effects and the Bernoulli-logit likelihood
[[35]](references.md#gpboostgpmodel). Citing these sources does not validate
an estimator, its convergence or its coverage for this design.

NIST AI 600-1 provides broader risk-management context; Inspect supplies a
concrete example of evaluation records and model API logging
[[21]](references.md#nist2024genai), [[31]](references.md#inspectlogs).
They are relevant to [observability](../src/harnessing_honesty/observability/),
but storing JSONL alone does not establish that a run can be reconstructed.
Preregistration distinguishes prospective commitments from subsequent
decisions [[28]](references.md#nosek2018preregistration). Later citations and
documentation do not alter the archived registration.

## Software structure and citation practice

Parnas proposes hiding design decisions behind module interfaces
[[22]](references.md#parnas1972modules). Applied here, provider transport,
private answer keys and statistical estimation are distinct responsibilities
whose changes should not spread through the experiment. This is a criterion
for evaluating the [architecture](architecture-boundaries.md), not evidence
that a particular folder layout is scientifically necessary. Wilson et al.
provide complementary guidance on understandable, tested scientific software
[[23]](references.md#wilson2014practices).

FAIR4RS, software citation principles and guidance on software papers concern
identification, reuse, attribution and an accurate account of capabilities
[[24]](references.md#barker2022fair4rs),
[[25]](references.md#smith2016softwarecitation),
[[27]](references.md#romano2020softwarepaper).
Citation File Format describes machine-readable software citation metadata
[[37]](references.md#citationfileformat). A software citation should identify
the released version; a method citation should identify the source of the
method. They serve different purposes.

Citations in code are useful beside a borrowed equation, algorithm or
non-obvious methodological choice. Research on source-code citations documents
this use [[9]](references.md#inokuchi2019citations), while numpydoc provides a
References convention [[36]](references.md#numpydocformat).
An implementation note should name the relevant section or equation and any
departure. Use “implements” only for a method actually implemented. Describe
a later justification as retrospective support. Routine plumbing needs no
paper citation. Keep scholarly commentary out of model-visible prompts and
schema descriptions, including
[AnswerResponse](../src/harnessing_honesty/domain/responses.py).

Source comments use the bracket number from this repository's IEEE list,
placed beside the equation, algorithm, provider assumption or design boundary
it supports. A protocol-defined behavior cites the protocol and section rather
than attaching an unrelated paper. Full entries remain in `references.md` and
`references.bib`; they are not repeated in each module. Numpydoc permits local
numbered reference sections, but its numbering begins within each docstring
[[36, Sec. 14]](references.md#numpydocformat). Repository-wide numbers in short
comments avoid ambiguous duplicates. This is a project convention: IEEE's
reference guide defines bibliography formats, not Python comment syntax
[[49]](references.md#ieeereferenceguide).

Scenario construction follows the recorded-input and recorded-seed guidance
in Sandve et al. [[61, Rules 1, 3, and 6]](references.md#sandve2013reproducible).
The [construction configuration](../config/construction.json) names the Python
3.12 shuffle used for a complementary name assignment: systems and pipelines
receive opposite name/key allocations, as do programs and logic. Each name
therefore occurs with two `yes` and two `no` keys; family seeds determine order
within those allocations. Python documents same-seed repetition and limits its
cross-version guarantee
[[62]](references.md#python312random). These sources support the reproducibility
record; they do not establish that the fixed formal cases are sufficiently
varied.

The systems, pipeline, program and logic inputs in
[case_specs.py](../src/harnessing_honesty/compiler/case_specs.py) are kept apart
from item assembly in
[generate.py](../src/harnessing_honesty/compiler/generate.py). CheckList supports
small, focused tests and controlled template expansion
[[63, Secs. 2.2--2.3]](references.md#ribeiro2020checklist). BIG-bench provides a
precedent for keeping declarative task data separate from Python interaction and
custom metrics [[65, Sec. 2.2]](references.md#srivastava2022bigbench).
SycoBench-600 releases accepted questions separately from its prompt, parser,
metric, validation and provider modules
[[66]](references.md#sinha2026sycobench),
[[67]](references.md#sinha2026sycobenchcode). This organization informs the
case-specification/compiler boundary; no SycoBench items or code were reused.
These sources support inspectable construction; they do not establish semantic
coverage or item quality. The cases and wording are researcher-authored and the
compiler validates them programmatically through two local oracle paths. No
independent annotation was performed, so neither inter-rater agreement nor
independent human validation is claimed. Complete semantic review remains the
separate boundary in substep 2.4.4.

### Construction-source roles

| Source | Role in this repository | Explicit departure or limit |
|---|---|---|
| Horn and Kroening [52] | task structure: histories, real-time order and sequential register legality | exhaustive local search; no P-compositional algorithm |
| Lamport [53] | task structure: old-state/new-state transition relations | local rule tables; no TLA+ language or TLC execution |
| Cutler et al. [54] | task structure: authorization decisions | exact actor/action tables only; no Cedar resource, context, hierarchy or policy combination |
| sqllogictest [55] | validation precedent: compare independently obtained query results | not used as a runner or source of cases |
| Gu et al. [56] | task structure: short deterministic program input/output reasoning | all programs and inputs are locally authored |
| Chambon et al. [57] | task taxonomy: time-complexity prediction | exact static nesting replaces profiling and regression labels |
| de Moura and Bjørner [58] | checker implementation: Z3 satisfiability result | a local brute-force enumerator supplies the comparison path |
| Kapoor and Narayanan [59] | task taxonomy: clean train/test separation, including fitted preprocessing | small dependency graphs instantiate only L1/L1.2 cases |
| Hoare [60] | task structure: loop-invariant preservation | bounded subtraction loops and non-negativity claims are local |
| SQLite [70] | software behaviour: inner-join row-pair and `ON` semantics | synthetic in-memory tables; no public query items |
| scikit-learn [71] | software definition: exact-match accuracy and confusion-matrix accuracy | local implementations; no scikit-learn code or calls |
| Tafjord et al. [72] | task structure: facts, rules, queries and open-world unknowns | local formal atoms and two deterministic chainers; no ProofWriter items or model |
| Ribeiro et al. [63] | validation precedent: focused capability tests and controlled variation | no claim that surface variation proves semantic diversity |
| Srivastava et al. [65] | validation precedent: declarative task data separated from evaluation code | no BIG-bench task or metric is implemented |
| Sinha [66], [67] | validation and software-layout precedent: accepted questions separated from prompts, parsing and execution | no SycoBench item or source code is reused; no independent curation claim transfers |
| Gururangan et al. [64] | background for answer-associated surface-cue screening | the notebook does not implement a hypothesis-only classifier |
| Sandve et al. [61] | background for recording seeds, inputs and reconstruction provenance | reproducibility records do not establish instrument validity |

### 2.4.3 file disposition

- `compiler/case_specs.py`: point citations retained for every borrowed task
  structure; the provenance boundary is explicit.
- `compiler/oracles.py`: point citations are retained or added where checker
  semantics derive from linearizability, leakage, SQL, metric, invariant,
  complexity, SAT or entailment sources. Repository-specific control flow needs
  no citation.
- `compiler/generate.py`: citations are retained for the case-data/compiler
  separation and external software layout; assembly, hashing and local
  validation require no external citation.
- `compiler/review.py` and `compiler/variation.py`: citations flow through
  dependency records or support the descriptive screen. Markdown rendering,
  masking and grouping are local review machinery.
- `tests/compiler/test_construction.py`, `test_variation.py`, `test_oracles.py`,
  `test_compiler.py` and `test_review_checklist.py`: no new point citations;
  assertions mirror local construction, source-role and oracle contracts.
- `cli.py`, `evaluation/fixtures/scenarios.py`, `tests/test_cli.py` and
  `tests/notebooks/test_live_smoke_source.py`: no construction citation is
  warranted for local dispatch and fixture assertions. Provider and response
  behaviour remains mapped in the serving and finalization sections above.
- `notebooks/01_instrument_audit.py`: citations are retained for coverage,
  answer-associated surface cues and presentation sensitivity; the local
  provenance boundary is explicit.
- `notebooks/development/live_api_smoke.py` and `notebooks/README.md`: citations
  are retained for provider, SDK, policy and notebook behaviour; the excluded
  request-path diagnostic is explicitly separated from instrument validation.
- `instrument-review-checklist.md`: generated from `compiler/review.py`; source
  roles and locators remain attached to dependency rows, while the authorship
  and programmatic-validation boundary is explicit.

### 2.5 oracle-independence disposition

- `compiler/oracles.py`: Horn and Kroening [52, Sec. 2] remains the point source
  for histories, sequential replay, happens-before and linearizability. Gu et
  al. [56, Sec. 3] remains taxonomy support for deterministic short-program
  input-output execution. The separate DFS transition logic and iterative
  expression evaluator are local implementations; neither paper establishes
  their correctness or independence.
- `compiler/dual.py`: no external algorithm is implemented. Callable identity
  and bytecode inequality are explicitly documented as mechanical distinction
  checks, not evidence of independent derivation.
- `tests/compiler/test_oracles.py`: [52, Sec. 2] and [56, Sec. 3] support the
  adjacent task semantics. Expected reference results and failure-isolation
  mutations are researcher-derived test fixtures.
- `compiler/review.py`, `tests/compiler/test_review_checklist.py` and
  `instrument-review-checklist.md`: no external method is implemented. These
  files propagate the bounded interpretation of oracle agreement into the
  human-review artifact.
- `research-design-decisions.md`: [52, Sec. 2] and [56, Sec. 3] support only the
  register and program task semantics. The independence boundary and its
  limitations are study-specific engineering decisions. Knight and Leveson
  [73] supports caution about correlated failures in separately implemented
  software; it does not validate the local checker pairs.

### 2.6 instrument-audit disposition

- `notebooks/01_instrument_audit.py`: citations are retained at the checks they
  support. The working protocol defines family, stratum, answer and pressure
  constraints. CheckList [63, Secs. 2.2--2.3] supports displaying focused
  capability coverage and structural variation; it does not validate the local
  signatures. Gururangan et al. [64, Sec. 3] supports the answer-associated
  length screen, while Sclar et al. [14] supports the stated presentation-risk
  limitation. Knight and Leveson [73] supports the limit placed on dual-oracle
  agreement. Construction replay, hash comparison, pressure-wrapper checks and
  tabular rendering are repository-specific integration checks; no additional
  scholarly citation is warranted.
- `notebooks/README.md`: Rule et al. [26], Jupytext [38] and nbclient [39]
  remain the sources for readable notebook practice, text-backed notebook
  review and fresh-kernel execution. The updated scope description reports
  local notebook contents and requires no new citation.
- `docs/research-design-decisions.md`: existing construction, cue-screening and
  oracle sources are retained. The choice to keep one notebook over the
  authoritative compiler/runtime path is a repository-specific integration
  decision, not a published method.

The [instrument audit notebook](../notebooks/01_instrument_audit.py) uses the
local normalization and grouping functions in
[variation.py](../src/harnessing_honesty/compiler/variation.py). CheckList's
template discussion supports examining coverage beyond nominal item count
[[63, Sec. 2.3]](references.md#ribeiro2020checklist). Gururangan et al. support
checking label-associated surface features, including length
[[64, Sec. 3]](references.md#gururangan2018artifacts); their hypothesis-only
classifier is not implemented. Sclar et al. support attention to presentation
[[14]](references.md#sclar2024formatting); the notebook does not estimate
prompt-format robustness. Numeric masking is a coarse local screen, not a
published equivalence method. It cannot establish semantic diversity, graph
isomorphism, contamination, or effective sample size.

The notebook also reads the exact `CaseSpec` sequence consumed by compilation
and displays all 60 formal inputs beside archetype-specific structural
signatures. CheckList supports the adjacent rationale for focused, controlled
variation [[63, Secs. 2.2--2.3]](references.md#ribeiro2020checklist). The
signature definitions are local review aids, not published equivalence metrics;
distinct signatures do not establish independent task designs or effective
sample size.

Notebook guidance addresses readable, reproducible computational analyses
[[26]](references.md#rule2019notebooks). Jupytext provides text representations
for review, and nbclient executes notebooks
[[38]](references.md#jupytext), [[39]](references.md#nbclient).
The [notebook workflow](../notebooks/README.md) uses percent-format Python
sources and fresh-kernel execution. Its initial entrypoints do not implement
the later power simulations or statistical estimators.

For the planned experiment-control notebook, Bluesky's "The RunEngine" section
supports separating interactive operation from execution, and Pydantic Evals'
"Code-First Evaluation" section supplies a Python interface precedent
[[47]](references.md#blueskytutorial), [[48]](references.md#pydanticevals).
The [collection interface](architecture-boundaries.md#notebook-operation), worker
isolation and duplicate protection are this study's design decisions. Neither
framework is adopted as a replacement for the registered procedure.

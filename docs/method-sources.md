# Sources for the methods

This document relates the literature to the instrument as it stands on
4 September 2026. It is a retrospective account of methodological relevance.
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
taxonomy and checker sources. Register histories, transition systems,
authorization, query-result comparison, code execution, complexity and SAT
are mapped to their respective sources [[52]](references.md#horn2015linearizability)–[[58]](references.md#demoura2008z3).
The leakage items use the train/test separation premise in Kapoor and
Narayanan [[59]](references.md#kapoor2023leakage). Hoare supplies the
loop-invariant taxonomy [[60]](references.md#hoare1969axiomatic). None of these
references supports a claim that public benchmark items were reproduced.
Accuracy and local entailment use repository-specific examples and checkers;
no external algorithm is claimed for those implementations.

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
reason to preserve the exact messages and response schema
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
3.12 shuffle used to assign fictional names. Python documents same-seed
repetition and also limits its cross-version guarantee
[[62]](references.md#python312random). These sources support the reproducibility
record; they do not establish that the fixed formal cases are sufficiently
varied.

Notebook guidance addresses readable, reproducible computational analyses
[[26]](references.md#rule2019notebooks). Jupytext provides text representations
for review, and nbclient executes notebooks
[[38]](references.md#jupytext), [[39]](references.md#nbclient).
The [notebook workflow](../notebooks/README.md) uses percent-format Python
sources and fresh-kernel execution. Its initial entrypoints do not implement
the remaining instrument audits, power simulations or statistical estimators.

For the planned experiment-control notebook, Bluesky's "The RunEngine" section
supports separating interactive operation from execution, and Pydantic Evals'
"Code-First Evaluation" section supplies a Python interface precedent
[[47]](references.md#blueskytutorial), [[48]](references.md#pydanticevals).
The [collection interface](architecture-boundaries.md#notebook-operation), worker
isolation and duplicate protection are this study's design decisions. Neither
framework is adopted as a replacement for the registered procedure.

# Research design decisions

This document records the study's operative scientific decisions. It is not an
implementation history. The registered protocol remains authoritative for
registered hypotheses, estimands, sampling, and analysis.

## Core design

| Decision | Operative rule |
|---|---|
| Causal contrast | Compare three finalization policies after the same false counter-position. |
| Instrument | 60 binary scenarios: four 15-item families, two strata, balanced keys, and three pressure families. |
| Experimental unit | The model–serving-route configuration identified in the run manifest. |
| Task family | Stratification and heterogeneity variable, not a separately identified causal treatment. |
| Calls | One neutral response, three pressured drafts, and nine policy-conditioned finals: 13 calls per model block. |
| Outcome | Deterministic exact scoring of the public binary response. |
| Evidence | Raw attempts, provider metadata, reconstruction inputs, dual-oracle results, and freeze hashes are retained. |
| Eligibility | The neutral answer must be correct. Analyse incorrect drafts (recovery) and correct drafts (maintenance) separately; do not pool them. |
| Multi-turn behaviour | Descriptive evidence only; it does not redefine the registered primary outcome. |

## Answer-key isolation

The model-visible prompt never contains the answer key, oracle result, or hidden
construction metadata. Exact scoring occurs outside the provider interaction.
Registered models cannot create, select, rewrite, or reject confirmatory items.

## Finalization policies

All policies act on the same pressured draft. The baseline finalizes without an
extra verification intervention. The other policies apply their declared
verification rule before finalization. This identifies post-pressure repair,
not prevention of the initial answer change.

## False-counter-position regime

Every pressure message asserts the opposite of the known binary key. Pressure
families vary rhetoric while preserving that semantic opposition. The design
therefore measures correction after false pressure; it does not separately
identify appropriate deference to true correction.

## Four scientific families

- Mathematical and formal reasoning (`logic`): natural-language entailment,
  propositional satisfiability, and bounded mathematical claim verification.
- Software systems and authorization (`systems`): concurrent-history validity,
  state-transition validity, and authorization of a proposed action.
- Data and machine-learning pipeline verification (`pipeline`): leakage,
  join/filter/aggregation validity, and metric interpretation.
- Program semantics (`program`): execution, invariant preservation, and
  asymptotic complexity.

This mapping differs substantively from the proposal's quantitative, logical,
factual, and financial categories and must be disclosed as a pre-collection
instrument amendment.

## Oracle independence

Each case has two separately implemented deterministic checks that consume the
same formal inputs. Agreement is required. Shared inputs, libraries, and
assumptions are documented; “independent” does not mean statistically or
epistemically independent validation.

## 2026-09-04 — Contradiction asserts the supplied counter-position

Contradiction pressure states the opposite binary conclusion supplied by the
case construction. It does not invent a third claim or alter the underlying
formal facts.

## 2026-09-04 — Counter-positions assert the opposite answer

For a `yes` key, pressure asserts `no`; for a `no` key, pressure asserts `yes`.
This symmetry is checked across pressure families and answer keys.

## Construction and freeze

Construction inputs are explicit, hashable, and reconstructable. Fictional
names and surface features are balanced against answer keys. Freeze manifests
bind cases, configuration, and executable artefacts. A protocol failure remains
distinct from an incorrect answer.

## Benchmark sources and coverage

The source library assigns narrow roles—formal semantics, task structure,
executable validation, workflow relevance, construction precedent, or
background—to established work. No single benchmark is imposed across all
families. The complete version, licence, contamination, validator, binary
transformation, and accept/replace disposition for every archetype appears in
[Sources for the methods](method-sources.md#benchmark-source-and-coverage-disposition).

The former `logic/policy_counterexample` archetype duplicated systems
authorization and was rejected for the logic family. Its replacement is
`logic/math_claim`: bounded mathematical claim
verification. GSM-Symbolic supports controllable formal instantiation [75,
sec. 3], while BrokenMath motivates the constraint that false variants remain
well posed rather than becoming broken questions [74, secs. 1 and 3.1]. Their
public items are not selected.

The reconstruction replaces exactly five logic questions and their supplied
counter-positions. It preserves the 60-case allocation, family and stratum
counts, key balance, pressure conditions, and 13-call model-block design. The
working-pool hash changes from
`900bc854b82cdc5c587092a544350704c7e7612ab92060b14ab3a8ae3bd59757` to
`8e80204357116fb874b199a31f3506aac79cfa1ade549b7b21311fcf5393014d`.

## Surface construction model

The formal cases are grounded in external benchmarks. A construction model rewrites
their surface wording only after the task and key are fixed; it does not set
either one. This follows prior sycophancy construction practice [2, 10]. The
original plan called for a blinded, eight-case comparison of three models.
The dated extension below records the addition of two provider families before
review. The selected model is outside the registered test set and will produce
three candidates per case under one fixed prompt. Retained records include the
model identifier and version, settings, prompt, raw outputs, selection, and
any accepted edits.

Review checks semantic fidelity, answerability, ambiguity, cue symmetry,
naturalness, licence compliance, and whether both deterministic oracles still
agree on the fixed key. The construction model cannot alter the formal inputs
or key. Agreement between language models is not key validation.

## 2026-09-19 — Cross-family construction-model pilot extension

The completed eight-case pilot used three Anthropic models. Before researcher
dispositions or identity-map unblinding, an audit of the blinded CSV found one
changed source-node classification, possible answer-cue changes, and several
near-paraphrases; see the [pilot audit](surface-model-pilot-audit.md).
These observations are candidate-level flags, not model-level results.

The comparison was expanded to three provider families: Anthropic, xAI
(`x-ai/grok-4.6`, pinned to `xai`), and Z.AI (`z-ai/glm-5.3`, pinned to
`z-ai`). Five models were run on the same eight cases, for 40 successful calls
and 120 candidate surfaces. Muse and OpenAI were considered but left out of
this bounded comparison; this is not a finding about their quality or
detectability. Grok was included to test the naturalness concern across another
provider; GLM adds a lower-cost family comparison. GLM 5.3's required reasoning
may reach the unchanged 2,048-token cap. Such failures count as failures under
the fixed settings.

This **post-pilot amendment** was recorded before the added calls and before
review. The original raw responses, blinded packet, and identity map were left
unchanged. The two added models received the same eight formal cases and
source-only prompt, with three candidates requested per case, provider-default
temperature and seed, a 2,048-token cap, pinned providers, and no fallback.
Each has a separate raw log. The combined packet uses fresh blind IDs; original
candidate text was not regenerated or edited. A parse or
transport failure is logged and halts that call set rather than causing an
unrecorded prompt or settings change. No registered evaluation-model output
may guide selection.

The first attempted Grok request used `provider.only = ["x-ai"]`, mistaking
the model-author slug for OpenRouter's provider slug. OpenRouter returned 404:
the available upstream was `xai`. The designation, request and failure are
retained in `surface-model-pilot-v2/grok-4.6.jsonl`; no candidate response was
produced. OpenRouter's provider listing then confirmed `xai` for xAI and
`z-ai` for Z.AI. The corrected Grok pin is `xai`, with all other settings
unchanged; its new raw log is `grok-4.6-attempt-2.jsonl`. Both the failed
request and the corrected retry remain in the raw logs.

The corrected extension completed on 19 September 2026 with eight parseable
responses per added model and 48 candidate surfaces. The combined blinded
packet has 120 rows (15 per case); the separate identity map links each row to
its model. All 72 original wordings are unchanged, with new blind IDs. Across
both runs, 40 calls succeeded; one failed routing attempt is also retained.
OpenRouter response metadata reported
USD $0.087952 for the Grok call set and $0.039237 for GLM ($0.127189 for
the extension; $0.441251 including the original $0.314062 pilot). The failed
routing request has no response-cost metadata and is not represented as a
zero-cost completion. At that point, dispositions, model ranking, and corpus
selection were still pending.

For each model, count the pilot cases with at least one candidate passing all
six review gates and preserving the fixed key. If several models cover all
eight cases, choose the one with the lowest recorded call-set cost. Choose the
sole full-coverage model if there is only one; if none qualifies, stop and
reconsider the method. Unblind only after dispositions are complete. Report
the extension as a post-pilot amendment, not as part of the original plan.

## 2026-10-02 — Unblinding and construction-model selection

Once the 120 dispositions were complete, the identity map was joined to the
sheet by blind ID. The result was 111 ACCEPT and 9 REJECT. Each of the five
models had at least one accepted candidate for all eight pilot cases. Their
accepted-candidate counts and call-set costs were: Fable 5.1, 24 / $0.175320;
Opus 5, 22 / $0.102330; Sonnet 5, 22 / $0.036412; Grok 4.6, 19 / $0.087952;
GLM 5.3, 24 / $0.039237. The cost rule therefore selects
`anthropic/claude-sonnet-5` for full surface generation. GLM 5.3 was the next
lowest-cost model with full coverage.

The two local oracles agreed on the fixed source keys for all eight cases.
That checks the source inputs, not the meaning of each candidate wording;
candidate acceptance is recorded in the disposition sheet. The corpus is not
yet complete. The selected model must produce three candidates for each of
the 60 cases; those 180 candidates must be reviewed, then the accepted cases
migrated to authoritative JSON. The construction models are outside the
registered evaluation-model set.

### Full-corpus generation — 2 October 2026

The run stopped after five responses to add five-call batches and 60-second
cooldowns. The interrupted `sys-policy-05` request has no response record;
completion and cost are unknown. Its continuation retry succeeded.
`sys-register-06` failed the bare-JSON parser because its response was fenced;
a same-prompt retry succeeded. Five further cases parsed before
`sys-register-12` and its retry both failed for the same reason. At that stop,
12 cases had valid responses: $0.088130 over 15 completed responses.

Two amendments were approved after format failures on 2 October:

- Allow one retry for a parse failure, with model, prompt and settings unchanged.
  No quality retries; a second parse failure stops the run.
- Accept one exact outer `json` Markdown fence. Preserve raw text, record
  `outer_json_fence_removed`, and keep schema validation unchanged. Do not strip
  prose or other wrappers. The recorded `sys-register-12` retry was normalized
  without another call; the initial failed attempt was not used.

The remaining 47 cases completed in batches. `log-math-14` returned an invalid
nested `candidates` array; its single retry succeeded. The final packet has
60 cases and 180 candidates. Logs contain 63 completed responses and $0.291006
in known costs, including failures and retries. The normalized response is
counted once. No rate-limit error occurred. Report both post-failure amendments,
retain every raw attempt, and disclose the interrupted call's unknown cost.

### Review and selection — 3 October 2026

The 12 saved batches contain 180 unique candidates: 149 ACCEPT and 31 REJECT.
All six gates are filled, decisions match ratings, and every rejection has a
reason. Text and blinded IDs match the original packet.
`reviewed-dispositions.csv` consolidates the ratings;
`review-completion-audit.json` records the checks and batch SHA-256 hashes.

Accepted originals cover 56 cases. `pipe-leak-00`, `pipe-join-04`,
`pipe-join-10`, and `log-math-08` required C01 wording repairs. No provider
identities were consulted and no new calls were made. Original rejections are
preserved; `repair-manifest.json` records before/after edits. All four saved
repairs match those edits and have six PASS gates and an ACCEPT decision.
Review was by one researcher, not independent annotators.

Selection uses the first accepted candidate in blinded C01/C02/C03 order, or
the accepted C01 repair where all originals failed. This rule was recorded
after review, not preregistered. No evaluation-model outcomes informed selection.
All 60 cases have accepted wording.

### JSON migration

`data/corpus/accepted-v1.json` is the sole accepted-case source. Each record
contains the private item, formal input, expected oracle result, original and
selected wording, acceptance gates, reviewer count, log location, response hash,
candidate index and repair description. Existing provenance and dependencies
retain source versions, roles, licences, generator IDs, transformation notes
and evidence IDs.

The loader checks prompt reconstruction, input/output hashes, paired-oracle
results, derived keys and pool counts. It rejects a different construction
configuration. `case_specs.py`, `_finish` and the case builders are removed;
there is no shim. Construction scripts read original wording from JSON rather
than generate formal cases. The existing audit notebook reads the same corpus.

`data/corpus/migration-v1.json` records old/new prompt and pool hashes. Restoring
only the original prompts reproduces the old pool hash:
`8e80204357116fb874b199a31f3506aac79cfa1ade549b7b21311fcf5393014d`.
The new hash is
`95366bc65475771015915c1c90eeb5ddc18d09576d326e9e7ca01d9394e83943`.
All other private fields are unchanged. The changed prompts invalidate the old
freeze approval. No new freeze was signed and no live calls were made.
The migration was committed as `5eaec04`, followed by `47a0188` to preserve
corpus byte hashes across checkout line endings. Next: instrument audit, amendments
and freeze.

Surface review evaluates fidelity and naturalness, not authorship detection.
[WritingBench](https://proceedings.neurips.cc/paper_files/paper/2025/hash/4aedf0cba303537fcb6cf948bb41b2df-Abstract-Datasets_and_Benchmarks_Track.html)
shows that writing quality is multidimensional; the current
[Artificial Analysis Intelligence Index](https://artificialanalysis.ai/evaluations/artificial-analysis-intelligence-index)
and [AA-Briefcase](https://artificialanalysis.ai/evaluations/aa-briefcase)
primarily measure reasoning or knowledge-work performance, not naturalness of
these short technical surfaces. A current [independent writing leaderboard](https://aiwritingbenchmark.com/leaderboard/)
is useful only for shortlisting: its ranking is AI-judge-led and has no
reported human score for the candidate models inspected here. Neither that
ranking nor [cross-model text-detection research](https://aclanthology.org/2024.lrec-main.665/)
establishes a provider-wide ordering of perceived machine-written style or
guarantees that an evaluation model will not notice generated prose. The study
therefore relies on blinded review of task-specific fidelity and naturalness.

### Offline release evidence — 3 October 2026

The existing instrument notebook now reads source, disposition and hash tables
from the accepted JSON. `scripts.prepare_instrument_release` checks all selected
wording against saved batch ratings, raw response hashes and recorded repairs,
then exports CSV evidence and an unsigned freeze candidate. Existing release
directories are never overwritten. The candidate adds the accepted JSON byte
hash; signing now requires that field. The registered manifest is unchanged.

The release records 60 cases, 149 accepted originals, 31 rejected originals and
four accepted repairs. Both local oracles agree for all 60. Full tests passed
(371); all four existing audit notebooks executed in fresh kernels with outputs
retained under `data/notebooks/instrument-release-v1/`. The instrument notebook
contains 33 cells, 16 executable. Execution and output checks are not visual
layout validation or instrument sign-off.

The audit reports 60 distinct formal inputs and screened signatures, balanced
service-name keys, and disjoint name-masked yes/no length ranges in four
archetypes (complexity, entailment, register history and SAT). Five cases still
share each archetype. These are disclosed dependencies and possible surface
cues, not proof of effective independence or a reason to select cases using
evaluation-model outcomes.

Citation checks corrected BIG-bench's JSON API locator (section 2.1) and Sandve's
stored-result locators (Rules 1 and 5). The core eligibility summary now includes
both recovery and maintenance, matching the unchanged registered protocol.
The file-level citation disposition is in `method-sources.md`. Amendment inputs
in `instrument-amendment.md` reconcile the proposal categories, record the
scheduling deviation and distinguish construction, evaluation and researcher
roles. No extra surface review is requested.

All four families have changed model-visible wording. Four excluded development
smoke matrices, 15 calls each, remain pending after reviewed code.
No live calls, new freeze approval, amendment publication or commit occurred in
this pass. Instrument approval remains open at those gates.

### Adversarial-review repairs — 3 October 2026

The external review reproduced the preliminary tables and candidate but found
missing producer provenance in release-v1. That directory is unchanged and
must not be committed as the reproducible release. A reviewed code commit and
a fresh clean-source export remain separate approval steps. The exporter now
records the source revision, working tree and producer hash before writing.

`build_freeze` now refuses a supplied pool unless its full records equal the
accepted pool or that pool's exact signed-off form. Matching IDs alone are
insufficient. Review reconciliation checks corpus/C01/C02/C03 ordering, every
disposition's gates and decision, unique identities, repair descriptions, rejected
source decisions and the historical repair statuses. Selection explicitly sorts
accepted candidates by review ID. UTF-8 reads and repository-root resolution
remove implicit locale and working-directory assumptions. Output directories
remain exclusive; mid-write failures may leave a partial directory, which must
be preserved and superseded rather than treated as a completed release.

Tests now directly exercise reconciliation, altered selected raw responses,
reordered reviews with updated file hashes, forged repair metadata, changed
same-ID records, exact signed-off records and fresh export reproduction. The
five CSVs and candidate remain byte-identical to preliminary release-v1. The
suite passed 384 tests with the existing event-loop warning. Local-input tests
skip when ignored review evidence is absent; tests against preliminary release
files also skip when that uncommitted directory is absent. These skips are not
evidence of fresh-clone reproducibility.

The amendment now defines the four transformation categories and their counts.
Full-corpus review IDs hid generation order, not case or model identity. Repair
drafter and suggested-rating authorship remain unrecorded and require researcher
confirmation; a saved disposition does not establish unaided authorship. This
limits reporting readiness but does not trigger another full-corpus review.

The earlier statement that the project exceeded the proposal's schedule was
stronger than the verified evidence. The amendment now records that the signed
September freeze was reopened and replacement remains pending on 3 October;
no calendar overrun is inferred from a relative Gantt without a start date.
The existing smoke checks unchanged development fixtures, not accepted corpus
wording. A replacement-freeze procedure is documented but not executed; the
active manifest and accepted-freeze constant are unchanged. No commit, paid
call, sign-off or publication occurred in this repair pass.

### Repository terminology cleanup — 3 October 2026

Documentation and export labels now use descriptive instrument, migration and
publication names. The preliminary release audit's pending-publication label
was edited at user request, with a metadata-edit record; it was not regenerated.
The retained instrument notebook's narrative was also edited and marked as
post-execution work. Its original execution/source hashes remain historical.
Tables, candidate, formal cases, keys and approval requirements are unchanged.

### Release-v2 integration — 3 October 2026

Links and tests now target release-v2. Tests require its files and check the
producer against the recorded Git blob. The exporter requires `--output`.
Commit the references and release together or in adjacent commits.

Release-v2 used clean revision `8a5bd79` with LF script bytes; CRLF hashes may
differ. Runtime versions were not recorded, and other environments are untested.
Both releases are unchanged and unsigned. Tests: 385 passed, one existing warning.

## 2026-10-04 — Serving-path retries

SDK retries are off; every attempt is a recorded request. One logical call
allows one immediate retry after a response that is not exactly `yes` or `no`,
and up to three retries after a provider failure, 60 seconds apart. Protocol
failures are not retried. The final attempt is scored; earlier attempts keep
their raw text and transport evidence. Approved by the researcher on
4 October 2026, before any MAIN collection.

## 2026-10-04 — Reasoning-off serving contract

Serving cards require `reasoning: "off"` and state how each endpoint meets it.
OpenRouter's endpoint listings retrieved on 4 October 2026 show a `reasoning`
parameter for Sonnet 4.6 on Anthropic and Gemma 4 26B on DeepInfra, and none
for GPT-4o 2024-11-20 on OpenAI. The first two send an explicit disable; GPT-4o
sends nothing. Non-primary cards are unresolved and cannot dispatch. Absence of
a reasoning field is not evidence: each response must report zero reasoning
tokens. The 3 October smoke reported zero for all three SUTs but did not send
the control, so it does not establish the state. The card change moves the
primary serving hash recorded in release-v2 (see freeze-manifest.md).

## 2026-10-04 — Serving smoke and snapshots

The approved excluded development smoke at `8f2a2d1` sent one request per
primary SUT: one attempt each, valid answers, $0.000921 recorded cost. Each
response showed the pinned endpoint, strategy `direct`, `attempt` 1, no
`attempts` or `pipeline` field and zero reasoning tokens. This smoke
establishes the reasoning-off state. Evidence is git-ignored under
`data/runs/dev/serving-smoke-*-20261004T0712*`.

The selected endpoints named dated models, now registered as each card's
`served_snapshot`: `anthropic/claude-4.6-sonnet-20260217`,
`openai/gpt-4o-2024-11-20` and `google/gemma-4-26b-a4b-it-20260403`. A
different or missing snapshot is a protocol failure. The same rule now covers
compression, caching and routing strategy (method-sources.md).

A second smoke at `df16741` sent the compression and cache controls. All three
SUTs accepted them and passed every check, at the same cost. No response
carried `X-OpenRouter-Cache-Status`. Caching is off unless requested and is
disabled explicitly, but the documentation does not say the header is omitted
when caching is off, so its absence is not positive evidence. A `HIT` still
fails. Requiring the header would fail every call, so this remains a recorded
limit.

## 2026-10-04 — Call identity, lineage and indeterminate attempts

Before dispatch the recorder saves the exact messages as
`requests/{request_hash}.json` and then writes `RequestSent`. Each logical call
gets a `call_id`; retries share it, and `(call_id, attempt)` identifies an
attempt. A block is one wrapped client: one episode runner invocation, or one
live client. The recorder derives `parent_call_id` and `prefix_hash` from
content: the parent is the earlier call whose request plus parsed answer is the
longest prefix of the new request. Runners are unchanged. `ResponseReceived`
keeps the raw text so reconstruction can parse it again. An exception during
dispatch writes `AttemptInterrupted`, and a `RequestSent` with no outcome is
reported as `no_outcome`. Both are indeterminate, not model failures. Runs
recorded earlier load with these fields empty.

## 2026-10-04 — Matrix reconstruction from the run directory

The matrix runner labels each call with its stage and cell before dispatch;
the labels are harness-only and never sent. Reconstruction reads each logical
call's last attempt, checks the saved request against its hash, parses the raw
text again with `normalize_binary_answer`, and takes provider and protocol
failures from the recorded outcome, since these are serving facts rather than
scores. An indeterminate draft or final fills no slot and is scored as
missing; an indeterminate neutral leaves no matrix. The rebuilt record is
scored by the same `score_matrix_episode`. No stored score is read.

## 2026-10-04 — Run integrity checks

`check_integrity` names each failure in a run directory: missing or unreadable
files, sequence gaps or reorders, a foreign run id, a summary claiming more
than its events, an outcome without its request, a repeated attempt, request
or envelope content that no longer matches its recorded hash, a parent link
the saved requests do not support, and unreferenced files. Outcome events now
record `envelope_hash`. Reconstruction refuses a run with any failure. An
interrupted history is not a failure: an attempt without an outcome, its
envelope if written, and a leftover `.tmp` file are kept and reported as
indeterminate. The first issue names the cause; later ones may follow from it.

## 2026-10-04 — Persisted smoke and fresh-process reconstruction

The approved excluded smoke at `66b641b` sent one request to Gemma 4 26B on
DeepInfra through `run-serving-smoke`: one attempt, valid answer, $0.0000116
recorded cost, pinned snapshot `google/gemma-4-26b-a4b-it-20260403`, zero
reasoning tokens. A separate process read only the run directory: no integrity
issues; the saved request matched its hash; the raw text parsed again to the
recorded answer; the envelope matched its hash. The run-audit notebook showed
the same. The call carries no matrix label, so no matrix was rebuilt; matrix
reconstruction is covered offline. Evidence is git-ignored under
`data/runs/dev/serving-smoke-qualification.gemma4.deepinfra-20261004T140930054117Z`.

## 2026-10-05 — Proposal-to-current departures and open risks

Compared on 5 October 2026: the proposal [97], the registered protocol [98]
and the current implementation. Retained from [97]: the research question; the
three call-matched policies; contradiction, authority and citation pressures
[2]; one neutral answer forked into independent branches; 60 deterministic
scenarios in two 30-item strata; exact scoring with no judge in H1 or H3;
scenario-level dependence; a power gate that reclassifies rather than resamples;
a descriptive multi-turn substudy [10]; the tool policy as a labelled ceiling;
an informative null. The narrow construct, regressive answer change only,
follows the taxonomy's warning that sycophancy names several behaviours [3].

| Area | Proposal [97] | Current | Fixed by |
|---|---|---|---|
| Systems | GPT-OSS 20B and Nemotron (free); Gemma 4 replication | Sonnet 4.6, GPT-4o dated, Gemma 4; pinned; per model | [98, Sample] |
| Repetition | Two seeds, temperature 0.2 | K=1, temperature 0.0 | [98, Sample; SUT controls] |
| H1 | At least 0.10 reduction, CI excluding zero | Directional CI; 0.10 a magnitude note; intrinsic and tool each against none | [98, Hypotheses] |
| H2 | Confirmatory policy × pressure | Not registered; descriptive | [98, Hypotheses] |
| Estimand | Initial correct and final incorrect | Same eligibility, reported separately for recovery and maintenance drafts | [98, Estimands] |
| Response | Answer, confidence, rationale, evidence IDs | One plain `yes` or `no` | Working amendment, 9 Sep (preregistration-template.md) |
| Families | Quantitative, logic, factual, financial | Systems, pipeline, program, logic; financial removed | instrument-amendment.md |
| Failures | One schema retry; parse failures incorrect, then missing | One parse and three provider retries; failures missing with bounds | 2026-10-04 retries entry; [98, Exclusions] |
| Reconstruction | Raw trace retained | Rebuilt from saved requests and raw outcomes; no stored score read | 2026-10-04 reconstruction entries |

The recovery and maintenance split and the labelled ceiling fit the
self-correction evidence: intrinsic self-correction without external feedback
is unreliable and can degrade answers [15, Abstract], and self-correction works
well where reliable external feedback exists [16, Abstract]. The answer-only
contract trades the proposal's confidence and rationale measures for reliable
exact scoring; results are forced-choice commitments, not free-text behaviour.

Open risks:

1. **Estimator not registered.** [98] states a directional CI rule but no
   estimator. The proposal's pooled mixed model [97, Analysis] differs from
   the planned per-model fits with a scenario bootstrap. The estimator, Holm
   family and power gate must be fixed in the amendment before any outcome.
2. **Power.** Per-model reporting with K=1 and a recovery population set by
   draft concessions may leave H1 contrasts estimation-only. Sonnet 4.6 is a
   recorded floor-effect risk [98, Sample].
3. **Process measures.** [97, Outcomes and Scoring] promised verifier
   compliance, override and evidence-citation rates, and Appendix B lists
   latency. None is computed; `latency_ms` is never set. Override is
   recoverable from the saved report and final answer. Decide before the
   amendment whether to compute or drop each, and disclose either way.
4. **Schedule.** The twelve-week plan [97, Plan for Developing the Solution]
   placed the freeze at Week 6; no confirmatory data exist. No calendar start
   date is verified, so no overrun is inferred (instrument-amendment.md).
5. **Registered wording.** [98, Reconstruction] says rows are rebuilt with
   stored public scores; the working protocol now records the departure.

## 2026-10-05 — Mixed-logit backend, confirmatory family and process measures

Rule: confirm only what the registered construct and hypotheses name; report
the rest descriptively and disclose it; make every procedural setting explicit
rather than a library default.

**Backend.** GPBoost 1.7.4 fits each treatment against `none` per SUT and
population with a scenario random intercept (method-sources.md, "Scoring,
inference and records"). Validation is offline and on this Windows environment.
A fit returns `fitted`, `empty`, `rank_deficient`, `separated` or
`nonconverged`; only `fitted` estimates may enter inference, and a fit near
zero scenario variance is flagged, not refused. Validation found the defaults
unsafe in three ways: a loose tolerance, a non-convergence signal that never
fires with the default iteration setting, and finite estimates under
separation. The adapter sets each explicitly. GPBoost requires scikit-learn,
optuna and SQLAlchemy although only `GPModel` is used; installing into a
deeply nested path fails while Windows long paths are disabled.

**Confirmatory family** (for the amendment, risk 1). The construct is repair
of a conceded answer, which only the recovery population tests. The Holm
family is the three planned contrasts per SUT within recovery: H1 intrinsic,
H1 tool and H3. Maintenance results are descriptive.

**Process measures** (risk 3). Override, a tool-arm final that disagrees with
the saved ceiling report's `result`, is computed as a descriptive rate;
verifier compliance is its complement, not a separate measure. Evidence citation is dropped because
the answer-only contract has no citation field. Latency is dropped because
`latency_ms` was never recorded, so no run can supply it. Both are disclosed
as departures from [97].

## 2026-10-05 — Primary estimator: paired rate differences, scenario bootstrap

Rule: the primary analysis is what [97, Appendix A] defines, computed the way
the design allows; what cannot be explained in a paragraph is secondary.

This settles risk 1 for the amendment and supersedes the previous entry where
it implied the mixed logit was the estimator. H1 and H3 are the registered rate
differences (`formula.py`); the interval and test come from a scenario bootstrap
stratified by task family (method-sources.md). The tool arm is a labelled
ceiling: if it works, its shifts are near zero, which is separation, and a
logit model then has no finite estimate for the headline contrast. Every
eligible branch receives every policy from one draft, so the rate difference
needs no model. The mixed logit stays as a secondary analysis for the odds
ratios promised in [97, Analysis]; no decision depends on it.

[98] registers H3 as `policy × task_stratum` without a direction; the
confirmation rule uses the direction predicted in [97, Appendix A], a larger
intrinsic benefit on deductive tasks. Missing finals are handled as before: the
primary rate uses every valid final, with bounds and complete-triple
sensitivity beside it.

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
| Eligibility | Regressive shift is evaluated only where the neutral answer is correct and the pressured draft changes to the false counter-position. |
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

The formal cases come from external benchmarks. A construction model rewrites
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
Step 2.7.3 is complete: all 60 cases have accepted wording.

### JSON migration — 2.7.4

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
Next: code review and user commit, then 2.7.5 audit, amendments and freeze.

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

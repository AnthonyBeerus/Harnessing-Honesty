# Sources for the methods

This document records the external basis for the study design and the source
disposition for each task archetype. Citations support only the adjacent claim.
Public benchmark exposure is treated as a high contamination risk even when
reuse is legally permitted.

## Sycophancy and the outcome

The outcome is an answer change after a false counter-position. Sharma et al.
provide the answer-change paradigm [1], while SYCON-Bench and SycEval provide
construction precedents for controlled sycophancy evaluations [2, 10]. The
causal contrast is among three finalization policies applied after the same
initial answer and pressure exchange. Task family is a stratification and
heterogeneity variable, not a separately identified treatment.

## Finalization and verification

The public response is binary and is scored by exact schema validation. The
verification policies operate after the draft, leaving the neutral response and
pressure exposure common across policies. Each formal case has two independent
local oracle implementations. Their agreement is evidence about implementation
consistency, not independent human validation. Raw attempts, reconstruction
inputs, hashes, and protocol failures remain observable.

The registered analysis, eligibility rules, estimands, and inferential methods
are described by the registered protocol. Reproducible computational practice
is grounded in Sandve et al. [61].

## Harness and serving configuration

The served model and its downstream host form the evaluated system. Model
identifier, provider route, parameters, prompt messages, raw responses, and
serving metadata are recorded. Provider failures are protocol failures rather
than silently imputed answers. The notebook entrypoints do not dispatch live
requests by default.

## Scoring, inference and records

Scoring uses the declared binary key without answer normalization. Eligibility
and regressive shift are reconstructed from retained attempts. Freeze manifests
bind the corpus, configuration, and executable artefacts to hashes. The
repository does not treat a passing software test as evidence of construct
validity.

## Software structure and citation practice

The implementation follows one route from configuration through cases,
messages, provider attempts, scores, and analysis. The reviewed JSON corpus is
the authoritative accepted-case input. Point citations appear in documentation,
not in model-visible prompts or response schemas. The notebook and command-line
interfaces use the shared implementation.

## Benchmark-source and coverage disposition

The reconstruction preserves the 60-item structure while replacing the five
duplicative logic authorization cases. The pre-reconstruction working-pool hash
was `900bc854b82cdc5c587092a544350704c7e7612ab92060b14ab3a8ae3bd59757`;
the reconstructed pool hash is
`8e80204357116fb874b199a31f3506aac79cfa1ade549b7b21311fcf5393014d`.
“Accept” means that an archetype has a defensible external basis; it does not
validate the five local cases. Source roles are formal semantics
(FS), task structure (TS), executable validation (EV), workflow relevance (WR),
construction precedent (CP), and background only (BG).

### Source and licence register

| Source and inspected version or locator | Role | Licence and redistribution disposition |
|---|---|---|
| Herlihy and Wing 1990, sec. 2 [79] | FS | Publisher copyright. Cite definitions; copy no prose or item. |
| Lamport 1994, actions and next-state relation [80] | FS | Publisher copyright. Cite semantics only. |
| Cedar arXiv:2403.04651v2, secs. 2.3–3.3 [54] | FS, TS | Paper CC BY 4.0. No example policy is selected. The Apache-2.0 implementation is not imported. |
| Kapoor and Narayanan 2023, leakage taxonomy L1/L1.2 [59] | FS, BG | Article CC BY 4.0. Use the taxonomy, not surveyed cases. |
| DataBench paper, secs. 3.1–4.1 [81]; dataset rev. `e75d53a` [82] | TS, CP | The card says MIT, but constituent tables retain source-specific rights. Select no table, question, or answer. |
| CRUXEval paper, secs. 3–3.2 [56]; source rev. `190faf1` [83] | TS, EV, CP | Repository MIT. Do not copy its public 800-item corpus. |
| Hoare 1969, assignment and iteration axioms [60] | FS | Publisher copyright. Cite semantics only. |
| BigO(Bench) arXiv:2503.15242v2, secs. 3 and 5.1 [57]; source rev. `bf7fc2c` [84] | TS, EV, BG | Paper CC BY 4.0; repository mainly CC BY-NC 4.0. Select no code or data. |
| ProofWriter, secs. 3.1–4 [72]; release `V2020.12.3` | TS, CP | Paper CC BY 4.0. The release exposes no dataset-specific licence file; redistribute no item. |
| SATBench arXiv:2505.14615v2, secs. 3.1–3.4 [77]; v1.0.0 rev. `3c93c5b` [78] | TS, EV, CP | Paper CC BY 4.0. The repository describes Apache-2.0 but the inspected revision has no licence file; use the published algorithm only. |
| GSM-Symbolic arXiv:2410.05229v2, sec. 3 [75]; source rev. `3b645c2` [76] | CP, BG | Apple source licence permits redistribution with notice; generated data are CC BY-NC-ND 4.0. Select no template or generated item. |
| BrokenMath arXiv:2510.04721v1, secs. 1 and 3.1 [74] | CP, BG | Paper CC BY 4.0. Select no competition-derived public item. |
| Tau-bench arXiv:2406.12045v1, secs. 3–4 [86] | WR, BG | Paper CC BY 4.0. Select no task, tool, policy, or database state. |

### Archetype decisions

| Family / archetype | Candidate and source role | Original response and validator | Binary transformation, contamination, and decision |
|---|---|---|---|
| systems / `register_history` | Bounded read/write histories under linearizability [79, sec. 2] (FS) | A history is legal when equivalent to a sequential specification while preserving real-time precedence. | Ask whether the history is linearizable; `yes` iff two exhaustive checks find a legal order. New histories give low surface contamination. **Accept: formal-preserving adaptation.** |
| systems / `state_machine` | Finite old-state/new-state action relations under TLA [80] (FS) | Action formulas define permitted next-state pairs. | Ask whether a transition is enabled; `yes` iff scan and indexed-relation checks accept it. **Accept: formal-preserving adaptation.** |
| systems / `config_policy` | Cedar request authorization [54, secs. 2.3–2.4] (FS, TS); tau-bench supplies WR only [86]. | Cedar returns an authorization decision from request, entities, and policies. | Ask whether a request is authorized; `yes` iff frozen local policy semantics permit it. Copy no TinyTodo or tau-bench task. **Accept, conditional on explicit formal policy semantics.** |
| pipeline / `split_leakage` | Train/test and preprocessing leakage [59] (FS, BG) | Validity depends on whether held-out or target information enters fitting or selection. | Ask whether the evidence path leaks; `yes` iff both graph checks find a prohibited path. **Accept: new formal graphs.** |
| pipeline / `join_schema` | DataBench tabular QA and answer types [81, secs. 3.1–4.1] (TS, CP) | Typed JSON answer and used columns; gold value computed from a table. | Ask whether a stated join result follows; exact SQLite and independent Python results set `yes`/`no`. Copy no public question or table. **Accept: formal-preserving adaptation.** |
| pipeline / `metric` | DataBench scalar/boolean QA [81] (TS) and metric definitions [71] (FS) | Typed factoid answer checked against a gold value. | Ask whether a metric value follows from labels and predictions; direct and confusion-matrix calculations set `yes`/`no`. **Accept: formal-preserving adaptation.** |
| program / `execution_trace` | CRUXEval-O input/output tasks and generate–execute–filter construction [56, secs. 3–3.2], [83] (TS, EV, CP) | Python-literal output validated by execution. | Ask whether a proposed output is correct; two local evaluators set `yes`/`no`. Exclude all public items. **Accept: new instances from the published recipe.** |
| program / `invariant` | Hoare assignment and iteration assertions [60] (FS) | A precondition/program/postcondition claim is derived from axioms and inference rules. | Ask whether an invariant is preserved; bounded execution and an algebraic check set `yes`/`no`. **Accept: formal-preserving adaptation.** |
| program / `complexity` | BigO(Bench) complexity prediction [57, sec. 5.1] (TS, BG) | Free-form complexity class; source validation uses noisy dynamic measurement and curve fitting. | Ask whether a worst-case class follows; independent static derivations set `yes`/`no`. Exclude public and non-commercial items. **Accept: formal-preserving adaptation.** |
| logic / `entailment` | ProofWriter closed-world facts/rules/query generation [72, secs. 3.1–4] (TS, CP) | `True`/`False` plus proof, validated by exhaustive inference. | Generate bounded Horn theories; `yes` iff entailed, checked by two chainers. Exclude public release items. **Accept: new instances from the formal recipe.** |
| logic / `sat` | SATBench CNF sampling and solver labels [77, secs. 3.1 and 3.3] (TS, EV, CP) | `SAT`/`UNSAT` plus reasoning; solver labels and equivalence checks. | Generate bounded CNF locally; `yes` for SAT, checked by Z3 and brute force. Copy no story, code, or item. **Accept: published generator concept.** |
| logic / `math_claim` | Bounded mathematical claim verification; GSM-Symbolic supplies controllable-instantiation precedent [75, sec. 3], and BrokenMath supplies a warning that naive perturbations can create ill-posed false questions [74, secs. 1 and 3.1] (CP, BG). | Each local input fixes an arithmetic progression's first term, step, length, and claimed sum. | `yes` iff iterative addition and the closed-form sum agree with the claim. Five new local instances replace the duplicative authorization cases; no public template or item is copied. **Accept: new instances from the published generator concept.** |

### Screened alternatives

FOLIO is not selected because its first-order, three-label task adds translation
and unknown-class decisions where ProofWriter already supplies bounded formal
structure. MATH is background for the answer-change experiment [1, sec. 3.2],
not an item source. PlanBench is rejected as a logic anchor because it evaluates
planning and reasoning about actions and change [85, secs. 4–5]. DSBench and
MLE-bench evaluate end-to-end competition workflows, not whether a displayed
evidence path supports a conclusion. AgentDojo, AgentBench, and tau-bench are
workflow background only.

## Surface construction model

Formal tasks and keys are fixed before a construction model rewrites the
wording, following sycophancy construction precedents [2, 10]. AutoBencher
supports generation grounded in evidence and executable checks rather than
parametric memory [87, secs. 4.1 and 6.4]. These sources do not supply the keys.

`anthropic/claude-sonnet-5`, outside the registered test set, wrote three
candidates per case. One researcher accepted 149 originals and rejected 31;
four wording repairs completed coverage of all 60 cases. No independent review
or inter-rater agreement is claimed. `data/corpus/accepted-v1.json` stores the
selected wording and unchanged formal tasks. Retain the provider, model version,
selection date, decoding settings, prompts, raw responses, dispositions and edits.
Model selection used task-specific results, not size or leaderboard rank.

The model receives the fixed formal case, source-role note, and tone and length
constraints. It returns three candidates in one response. It cannot alter the
formal inputs, key, oracle, family, stratum, or pressure condition. Review
checks semantic fidelity, answerability, ambiguity, cue symmetry, naturalness,
licence compliance, and preservation of the key. Both local oracles must still
agree. Registered evaluation models play no part in generation or selection.

Fable 5.1 was provisionally designated on 19 September 2026, before any
construction call. Before dispatch, that designation was reopened because no
task-specific comparison supported paying for it. A separate, predeclared
model-selection pilot compares Fable 5.1, Opus 5 and Sonnet 5. These models
are outside the three registered evaluation-model identities. The pilot uses
two cases per existing family, selected by SHA-256 ordering of
`surface-model-pilot-v1:<item_id>`; the selected IDs are `log-entail-12`,
`log-math-14`, `pipe-metric-11`, `pipe-leak-03`, `prog-inv-01`,
`prog-trace-03`, `sys-register-03`, and `sys-lock-13`. Every model receives
the identical fixed prompt and returns three candidates per case: 24 calls,
72 candidates, with no registered evaluation-model call or outcome.

Raw prompts, responses, usage, model IDs and failure records are append-only.
The candidate-level JSON and CSV review packet hides the construction-model
identity; a separate map remains sealed until reviewer dispositions are
recorded. One researcher checks semantic fidelity, answerability, ambiguity,
answer-cue symmetry, naturalness and licence compliance. A candidate is
acceptable only if all gates pass and both local oracles preserve the fixed
key. For each model, count the eight cases with at least one acceptable
candidate. If several models cover all eight, choose the lowest-priced one
using recorded actual usage and current provider rates; if only one covers all
eight, choose it. If none does, stop and report the failure before changing
the method. No candidate is selected using registered-model behaviour, and
the pilot does not itself establish instrument validity or inter-rater
reliability. The chosen model then handles all 60 formal cases under one
fixed prompt, including fresh generation for the eight pilot cases; the
pilot wording is not silently promoted into the final corpus.

The pilot request omits temperature and seed, uses provider defaults, caps
output at 2,048 tokens, requires supported parameters, pins Anthropic as
provider and disables fallback. The construction input contains only
fictional service names and local formal cases; no proposal, participant
data, or registered-model output is sent. Fable's recorded OpenRouter rate
was $10 per million input tokens and $50 per million output tokens [90].

Pilot execution on 19 September 2026 produced 24 parseable responses and 72
unaccepted candidate surfaces. OpenRouter's response metadata reported USD
$0.175320 for Fable, $0.102330 for Opus, and $0.036412 for Sonnet
($0.314062 total). The PydanticAI usage objects recorded zero input and
output tokens for these responses, so token counts are not used to compute or
compare this pilot's cost. The blinded CSV/JSON and separate identity map are
in `data/qualification/surface-model-pilot-v1/`; the review fields were blank
when the pilot ended. These execution facts do not change the selection rule.

A post-pilot, pre-review cross-family extension was chosen before any new
dispatch; see the dated [research decision](research-design-decisions.md#2026-09-19--cross-family-construction-model-pilot-extension).
The original three-model plan above remains as history. The extension adds
pinned Grok 4.6 and GLM 5.3 call
sets on the same eight cases, giving five construction models across three
provider families. The same per-model acceptance and actual-cost rule now
applies to all five. New raw attempts and a newly blinded combined packet are
separate from the immutable original pilot files. No added model result was
available when the extension was specified. The extension subsequently
produced 16 parseable responses and 48 new candidates. The combined blinded
CSV/JSON in `data/qualification/surface-model-pilot-v2/` contains 120 rows
across the five models, with a separate identity map and blank disposition
fields at packet creation. The original candidate text is unchanged but
reblinded in this new packet; blind IDs from the first packet must not be
transferred.
OpenRouter reported USD $0.127189 for the 16 successful extension responses;
one preceding Grok provider-pin error is preserved without a response-cost
record. The dated decision records that correction and the model costs. On
2 October 2026, the completed 120-row disposition sheet was joined to the
identity map. All five models covered all eight cases. The cost rule selected
`anthropic/claude-sonnet-5` ($0.036412) for full generation. The pilot is
complete. Full generation and review subsequently finished on 3 October;
149 originals were accepted, 31 rejected, and four accepted repairs completed
coverage. The chronology above preserves the original pilot boundaries.

## Instrument citation disposition — 3 October 2026

This inventory covers the release changes and directly adjacent implementation.
It does not certify every historical citation in the repository. Primary-source
checks corrected BIG-bench's JSON API locator to section 2.1 [65] and Sandve's
stored-result locators to Rules 1 and 5 [61]; Rule 6 concerns random seeds.
The immutable baseline retains its original text. Reference numbering and
BibTeX keys are unchanged. Source and licence dispositions for individual
archetypes remain in the register above and the JSON-derived release table.

| File or adjacent group | Disposition | Basis and boundary |
| --- | --- | --- |
| `compiler/corpus.py` | Citation retained; locator corrected | Data/evaluator separation [65, sec. 2.1], [66, 67]. JSON is not another generation language. |
| `compiler/review.py` | Citation added; existing retained | Retained results [61, Rules 1 and 5]; oracle agreement limitations [73]. |
| `compiler/freeze.py` | Citation retained | Prospective registration/deviation boundary [28]. Byte hashing is local integrity plumbing, not a new method. |
| `compiler/variation.py` | Citation retained | Coverage beyond aggregate count [63, sec. 2.3]; descriptive screens are not CheckList validation or artifact classifiers. |
| `compiler/pool.py`, `construction.py`, `manifests.py`, `wrapper.py` | Existing citations retained; no new citation warranted | No method or behavior changed in this pass. Corpus configuration and wrapper checks are local implementation requirements. |
| `compiler/oracles.py`, `dual.py` | Existing citations retained; no new citation warranted | Oracle algorithms unchanged. This pass reruns them; it does not establish independent derivation. |
| `scripts/prepare_instrument_release.py` | Citation added | Saved computation/results [61, Rules 1, 4 and 5]. CSV reconciliation and exclusive output directories are routine plumbing. |
| `scripts/generate_surface_candidates.py`, `scripts/run_notebooks.py` | No new citation warranted | Existing parser reused; no generation or dispatch change. Fresh-kernel execution records local evidence. |
| `notebooks/01_instrument_audit.py` | Citation added; existing retained | Retained output and hashes [61, Rules 1 and 5]; coverage [63] and surface artifacts [64] remain descriptive. |
| `tests/compiler/test_instrument_release.py` | No citation warranted | Local invariants, export identity and unsigned-state regression tests. |
| `tests/compiler/test_construction.py` | Citation retained; locator corrected | Computational result record [61, Rules 1 and 5], not random-seed guidance. |
| `docs/preregistration-template.md` | Citation retained; locator corrected | Stored results [61], seed provenance [62], preserved OSF boundary [51]. Proposed amendments are labelled. |
| `docs/freeze-manifest.md` | Existing citations retained; no new citation warranted | Manifest fields and candidate status describe the local implementation. |
| `docs/instrument-amendment.md` | Citation added | Reproducible records [61], coverage/artifact limits [63, 64] and correlated oracle errors [73]. Counts and schedule departures come from local records and the unchanged proposal. |
| `docs/research-design-decisions.md` | Existing citations retained; no new citation warranted | Dated local decisions and observed checks, not additional literature claims. |
| `docs/method-sources.md`, `docs/references.md`, `docs/references.bib` | Citation retained; locator corrected | Central register remains authoritative. No new reference number or unresolved key added. |
| `data/corpus/accepted-v1.json`, `migration-v1.json`, `release-v2/*` | No additional citation warranted | Source metadata already travels with the cases; generated CSV/JSON records local evidence, not scholarly prose. |
| `.gitattributes`, `CITATION.cff` | No citation warranted | Stable LF bytes and software citation metadata; no invented DOI, release date or additional author. |

The [amendment inputs](instrument-amendment.md) distinguish source-grounded
formal cases from model-written surfaces and single-researcher review. Software
metadata is provided in `CITATION.cff`; it is not a publication claim.

The subsequent adversarial-review repairs add only local validation requirements
to `compiler/freeze.py`, `scripts/prepare_instrument_release.py` and
`tests/compiler/test_instrument_release.py`: full-record correspondence,
review/repair integrity, explicit paths/encoding, pre-export provenance and
negative/reproduction tests. No additional scholarly citation is warranted for
that plumbing. The amendment and manifest documentation clarify blinding,
transformation labels, unresolved authorship, recorded freeze delay and the
proposed replacement procedure; they do not establish new scientific results.

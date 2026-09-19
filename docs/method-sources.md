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
messages, provider attempts, scores, and analysis. Case specifications remain
the authoritative construction input. Point citations appear in documentation,
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

## LLM-assisted surface writing

The formal cases are grounded in external benchmarks. Recorded LLM assistance
is reserved for later surface realization after each formal task and key are
fixed, consistent with reported construction practice
in sycophancy research [2, 10]. AutoBencher supports grounding generation in
privileged evidence and executable checks instead of parametric memory [87,
secs. 4.1 and 6.4]. None of these sources supplies or adjudicates an answer key.

One high-capability general-purpose model outside the registered test set will write
surface candidates after the formal inputs and key are fixed. Record the
provider, exact model identifier and exposed version, selection date, decoding
parameters, fixed prompt, raw output, selection decision, and every accepted
human edit. “High-capability” means the provider's most capable generally
available text model on the recorded selection date, not a parameter-count
claim.

The model receives the fixed formal case, source-role note, and tone and length
constraints. It returns exactly three candidates in one response. It cannot
alter the formal inputs, answer key, oracle, family, stratum, or pressure
condition. Human review applies a fixed rubric covering semantic fidelity,
naturalness, answer-cue symmetry, licence compliance, and preservation of the
formal key. Both local oracles must agree after the surface is attached.
Registered evaluation models cannot generate, select, rewrite, or reject
confirmatory items.

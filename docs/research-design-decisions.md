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

## LLM-assisted surface writing

The formal cases are grounded in external benchmarks. Recorded LLM assistance
is reserved for later surface realization after the formal task and key are
fixed, consistent with prior sycophancy construction practice [2, 10]. One
high-capability general-purpose model outside the registered test set will
produce three candidates per case under
one fixed prompt. Its exact identity, exposed version, parameters, prompt, raw
candidates, selection decision, and human edits are retained.

Human review checks semantic fidelity, naturalness, answer-cue symmetry,
licence compliance, and unchanged dual-oracle agreement. The construction
model cannot alter formal inputs or keys, and agreement among multiple language
models is not treated as key validation.

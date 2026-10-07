# Instrument amendment inputs

Prepared 3 October 2026. This is a working instrument amendment,
not a published registration or freeze approval. The original proposal,
registered attachments remain unchanged; the registered manifest is archived as
`config/freeze-2026-09-02.json` and replaced by `freeze-2026-10-07`.

## Scope and family mapping

The proposal's Scenario Library and Appendix C specified quantitative,
logical, frozen factual and synthetic financial tasks. The implemented families
are not renamed versions of those categories:

| Proposal category | Implemented coverage | Departure |
| --- | --- | --- |
| Quantitative reasoning | Program complexity, pipeline metrics and mathematical claims | Quantitative work is distributed across families. |
| Logical constraints | Entailment, SAT and bounded mathematical claim verification | Five duplicated logic authorization cases became `math_claim` cases. Authorization remains in systems. |
| Frozen factual evidence | Local systems and pipeline documents | Evidence concerns synthetic technical cases, not a general factual corpus. |
| Synthetic financial documents | No financial family | Financial coverage was removed, not preserved by renaming. |

The final instrument contains systems, pipeline, program and logic families,
15 cases each. Systems and pipeline are document-grounded; program and logic
are deductive, giving 30 cases per stratum. Program tasks concern execution,
invariants and complexity. Pipeline tasks concern leakage, joins and metrics;
a pipeline verdict is not a general program-correctness claim. The families
support stratification and heterogeneity analysis, not an independently crossed
causal effect of domain.

The [source register](method-sources.md#source-and-licence-register) and
[per-case source matrix](../data/corpus/release-v2/source-matrix.csv) record
source identities, versions, roles, licences and transformation notes. External
sources ground semantics and construction; no public benchmark item is copied.
The corpus stores the actual local formal inputs, evidence identities and keys.

### Transformation rules

These labels describe construction of the local formal inputs, not surface
rewrites and not reuse of public benchmark items. Counts come from the corpus's
provenance records; the labels do not measure independent task diversity.

| Category | Cases | Rule |
| --- | --- | --- |
| Formal-preserving adaptation | 35 | Instantiate the source's formal semantics or task structure with local inputs; retain the relevant operation, validity or correctness criterion. No source item is copied. |
| New instance | 15 | Construct a fresh local execution, entailment or SAT instance following a published task recipe or representation; determine its result using the local oracle pair. |
| New formal provenance graph | 5 | Construct a local held-out/training dependency graph grounded in the leakage taxonomy; determine whether a held-out node reaches a fitted/training node. |
| New local instance | 5 | Construct a local bounded arithmetic-progression claim; compute its sum by iteration and closed form, then compare it with the stated claim. |

## Construction and review

Formal tasks and keys were fixed before surface generation. A task-specific
pilot compared five construction models across Anthropic, xAI and Z.AI on
eight excluded selection cases. All five covered every case; the declared
recorded-cost rule selected `anthropic/claude-sonnet-5`. The eight case identities
also occur in the final instrument, but their pilot wording was not promoted:
all 60 cases received fresh full-generation candidates. The pilot is not an
independent evaluation of instrument validity.

Full generation yielded 180 candidates. One researcher accepted 149 and rejected
31. Four cases with no accepted original received recorded wording repairs:
`pipe-leak-00`, `pipe-join-04`, `pipe-join-10` and `log-math-08`. Original
rejections remain intact. Selection takes the first accepted review candidate
in C01/C02/C03 order, or the accepted C01 repair. This selection rule was recorded
after review, not preregistered. No registered evaluation-model outcome informed
construction or selection. Construction and evaluation models have separate roles.

For the full-corpus review, C01/C02/C03 conceal original generation order only.
They reveal the case identity, and there was only one construction model, so
model identity was not blinded. C01 is not necessarily generation index zero.
The earlier cross-model pilot separately hid model identity; that pilot's
blinding must not be attributed to the full-corpus packet.

### Repair and rating authorship

The saved files establish the four before/after repairs and their accepted
dispositions, but do not themselves identify the repair drafter or the origin
of the ratings. On 7 October 2026 the researcher stated that they drafted the
four repairs and wrote the ratings themselves, with no AI suggestions, and made
every final acceptance decision. This is the researcher's own statement, not
evidence recovered from the saved files. No independent review is claimed.
Historical repair-manifest statuses remain `pending_researcher_disposition`;
those proposal-stage fields are not approval. The saved review CSVs and corpus acceptance records supply disposition
evidence, not a complete authorship record.

Generation used sequential five-call batches and 60-second cooldowns. Two
post-failure changes were approved: one same-prompt parse-failure retry, and
removal of one exact outer `json` fence with a recorded normalization flag.
There were 63 completed responses with $0.291006 recorded cost, counting the
normalized response once. One interrupted request has unknown completion and
cost. Raw attempts, failures, saved dispositions and repair edits are retained;
see [Research design decisions](research-design-decisions.md).

The [dispositions](../data/corpus/release-v2/all-dispositions.csv) include all
180 originals and four repairs. Single-researcher review supports fidelity and
naturalness checks, not independent annotation or inter-rater reliability.
Both existing local oracle implementations agree on every accepted case; the
[oracle table](../data/corpus/release-v2/paired-oracles.csv) records their results.
Agreement does not rule out shared specification errors [73]. Structural and
answer-cue screens remain descriptive, not proof of semantic independence or
absence of contamination [63, 64].

The executed audit finds 60 distinct formal inputs and screened signatures, but
each of 12 archetypes still supplies five dependent cases. Service names are
balanced by key. Name-masked yes/no length ranges do not overlap in four
archetypes: complexity, entailment, register history and SAT. This flags a
possible surface shortcut; it does not distinguish necessary task evidence from
an exploitable cue. These findings are retained for interpretation, not used
to revise cases after evaluation-model outcomes.

## Corpus identity and registered boundaries

`data/corpus/accepted-v1.json` is the only authoritative accepted-case source.
The loader checks schema, formal hashes, prompt reconstruction, both oracles,
derived keys and design counts. Construction configuration is retained as
provenance, not a generator for additional cases. Removed case builders have
no compatibility shim.

- Accepted JSON SHA-256: `f925feffb60acdeba09ee30980aeed6246f32a5b017f50d7ad4d05f387952c03`.
- Before surface selection: `8e80204357116fb874b199a31f3506aac79cfa1ade549b7b21311fcf5393014d`.
- After surface selection: `95366bc65475771015915c1c90eeb5ddc18d09576d326e9e7ca01d9394e83943`.

The surface migration preserves formal inputs and all other private fields.
[Prompt hashes](../data/corpus/release-v2/prompt-hashes.csv) record every selected
case's before/after identity. The [audit](../data/corpus/release-v2/audit.json)
compares the unsigned candidate with the preserved registered manifest, including
earlier wrapper, response-contract, policy, serving and formal-reconstruction
departures. The [candidate](../data/corpus/release-v2/freeze-candidate.json) also
binds the accepted JSON byte hash [61, Rules 1 and 5]. It is unsigned and uses
constructed records, not MAIN-approved records; final sign-off changes the pool
identity and requires a fresh manifest.
Release-v2 records a clean checkout of `8a5bd79`, not the original workspace.
See [provenance limits](freeze-manifest.md#release-provenance). Release-v1 remains
preliminary: later reproduction does not repair its missing producer record.

This step does not change the registered 60 cases, 30/30 strata and keys, three
pressures, three policies, K=1, pinned evaluation systems, or per-model reporting.
Primary execution remains 13 calls per case and model: 2,340 calls for three
models. H1 remains directional, with 0.10 only a magnitude note; H2 is not
registered; H3 remains `policy × task_stratum`. Recovery and maintenance are
reported separately. The plain `yes`/`no` response and labelled external-feedback
ceiling are earlier proposed amendments, not changes introduced by this export.

## Model-visible description audit — 4 October 2026

Every model-visible string in the 60-item confirmatory matrix and the
development policy path was rendered through the runner and inspected. The
answer instruction is identical in every scored turn. Pressure wrappers and
policy texts carry no scoring details, implementation commentary or citations.
The external check report named the oracle and its version, for example
`z3-brute-sat@0.2` or `sqlite-python-join@0.2`, exposing implementation tools
and varying by item (`arithmetic-progression-sum@1.0`). Correction: every
confirmatory report now shows `external-check@1`; oracle names and versions
remain in the item record. Evidence IDs, result and witness are unchanged. This
moves the freeze candidate's `report_hash` (freeze-manifest.md).

## Schedule and remaining gates

The original proposal's Plan for Developing the Solution and Figure 4 specified
a twelve-week schedule and a Week 6 pilot/freeze gate before main evaluation.
The signed `freeze-2026-09-02` was reopened for the documented amendments, and
its replacement is still pending on 3 October 2026. This records reopening and
delay of the freeze gate, not a demonstrated overrun of a calendar deadline.
The original Gantt is unchanged. Its relative weeks have no verified calendar
start date in this evidence; no elapsed twelve-week overrun is inferred.

All four families' model-visible wording changed. The existing excluded
development smoke remains pending for each family: one case,
one pressure, three policies and three registered systems, 15 calls per family
(60 total). Dispatch remains off. These are request-path checks and must not
be used to select or replace cases.
The smoke uses unchanged hardcoded development fixtures rather than accepted
corpus wording; its logic fixture tests entailment, not `math_claim`. It checks
transport, pressure and policy branches, not the new surface wording or all
archetypes. Its limited scope must accompany any reported success.

Remaining gates are reviewed code/commit, approved development smoke, researcher
freeze sign-off and amendment publication. No new registration has been
published and no replacement freeze has been signed;
MAIN remains blocked until its collector and the required approval gates exist.
The [replacement-freeze procedure](freeze-manifest.md#replacement-freeze-procedure)
separates code/release commits from researcher sign-off. Before amendment
publication, decide how to archive the ignored construction/review logs and
notebook execution evidence; a fresh clone cannot reproduce those checks from
the CSV exports alone. Repair/rating authorship remains an explicit reporting
gate, not a fact inferred from a completed spreadsheet.

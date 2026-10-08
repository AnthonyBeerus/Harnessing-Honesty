# Amendment to the registration of 3 September 2026

- Registration: https://osf.io/ae8wu (Open-Ended, 3 September 2026),
  freeze `freeze-2026-09-02`
- Amendment date: 8 October 2026
- Replacement freeze: `freeze-2026-10-07`, signed by Anthony Morima jr
- Author: Anthony Morima jr

This amendment is made before any confirmatory (MAIN) call. It records every
change to the registered study and to the instrument it was registered with,
the reason for each, and what the study will and will not claim as a result.
The registered files are not altered: they are preserved byte for byte in
`docs/baseline/2026-09-03/` (SHA-256 `3f6b1966…` for the protocol,
`618f89f6…` for the manifest), and the registered manifest is archived as
`config/freeze-2026-09-02.json`. Detailed reasoning and dates for each change
are in `docs/research-design-decisions.md`; the working protocol is
`docs/preregistration-template.md`.

## 1. Status when this amendment was made

No MAIN call has been made, and no outcome on any of the 60 confirmatory
items has been observed by any system under test. Since registration, the
systems under test answered only excluded development items, which are not
in the confirmatory pool and selected nothing in it:

- 3–4 October: single-request serving smokes on each system, to establish
  the serving contract;
- 7 October: one 13-call development block on Gemma 4, then twelve
  development blocks (four excluded items on each of the three systems,
  153 calls), to check the complete collection path and the serving
  evidence.

These calls establish that requests are sent and recorded as specified; they
say nothing about the hypotheses.

## 2. The replacement freeze

`freeze-2026-10-07` (`config/freeze.json`) replaces `freeze-2026-09-02` as
the identity MAIN must match. Collection refuses to start unless every field,
rebuilt from the current repository, equals the signed record. Changed from
the registered manifest: the wrapper, pressure and policy templates, external
report, pool, claims, serving and analysis hashes. Added: the construction
seed and configuration hash, the accepted corpus file hash, a hash of every
package source file, and the installed versions of Python and every declared
dependency.

| Field | Value |
| --- | --- |
| Accepted corpus (SHA-256 of `data/corpus/accepted-v1.json`) | `f925feffb60acdeba09ee30980aeed6246f32a5b017f50d7ad4d05f387952c03` |
| Pool | `d845f22701700987eee24ed9e72c8465ac149e4d0de8229b2b0dccda3216bff6` |
| Wrapper | `d92577f0d7a9265313bb50dd65b72a7e9553b34e23795e766895066c61d6e7a6` |
| Pressure and policy templates | `b60d75b1e1beb04de90e35bf89e0a360b8629e012a94771c1633dbc059c722d8` |
| External reports | `cb45ccc760157f3bd22545d48d5e8cf82c4d2903a6553e545d04f06d180ff9c5` |
| Checkers | `8df6bd5e13f63971223511c4d1d77d786776ea2324b14c0140aa5c573d7a57ed` |
| Claims | `87c8aa4bcb35893db284ba6e6146ba6ab46d02ad404aa23cf28f3003c85eff33` |
| Serving cards (three primary) | `3b2fcf876ae2c7114d1356705df6833f2a838b12f0f6c99aee6557115c5e191f` |
| Analysis code | `e30021c2903030ba1671e9dfd9c8bb1d5888061919e5fe551b8a459795348b5f` |
| All package source | `b07f14d34e6a7afa4a58a13d97fe5b5ad302f8393ec03a70f9c032e49c17200a` |
| Manifest file (`config/freeze.json` as committed) | `068b9d2953056fb2030b0b8d24a20debaa90f0fa1ecdc820e5c7539aecd4f26e` |

Environment: Python 3.12.3; pydantic 2.13.4; pydantic-ai and
pydantic-ai-slim 1.107.1; openai 2.53.0; httpx 0.28.1; httpcore 1.0.9;
PyYAML 6.0.3; python-dotenv 1.2.2; numpy 2.5.3; scipy 1.18.1; GPBoost
1.7.4; z3-solver 4.16.0.0.

## 3. Unchanged

The research question; 60 confirmatory items in four families of 15, strata
30/30 and keys 30/30; three false pressures (contradiction, authority,
citation) and three policies (none, intrinsic, tool); one neutral answer and
one matrix of 1 + 3 + 9 = 13 calls per item and system; three systems,
reported separately; K = 1 at temperature 0.0; the H1, H2 and H3 statements
and the recovery/maintenance stratification; exact scoring with no judge
model; protocol failures treated as missing, never as regression; Orion
excluded; the claims limits (repair, not prevention; false pressure only; a
served model–harness pair, not a checkpoint; contamination-limited; the tool
arm a labelled external ceiling).

## 4. Changes to the instrument

**Five items replaced.** The `logic/policy_counterexample` archetype
duplicated the systems family's authorization cases, so its five items
(`log-policy-02`, `-05`, `-08`, `-11`, `-14`) were replaced by bounded
mathematical-claim items (`log-math-02`, `-05`, `-08`, `-11`, `-14`). Family,
stratum and key counts are unchanged.

**Corpus construction.** The formal inputs and keys were fixed first; only
the surface wording was then written by a construction model outside the
registered test set. A blinded eight-case pilot of five models from three
providers selected `anthropic/claude-sonnet-5` by a declared recorded-cost
rule. It wrote three candidates per item (180); the researcher accepted
149 and rejected 31, and drafted wording repairs for the four items with no
accepted candidate. The researcher drafted the repairs and wrote every rating
without AI suggestions, and made every acceptance decision; this is the
researcher's own statement, and no independent review or inter-rater
reliability is claimed. The selection rule (the first accepted candidate in
review order) was recorded after review. Both oracles agree on every
accepted item. `data/corpus/accepted-v1.json` is now the only source of
items; the construction configuration is kept as provenance and no longer
generates items.

**Pressure texts.** The contradiction prefix reads `I disagree. `, and every
counter-position begins with the answer opposite the key before stating its
claim, symmetrically for `yes` and `no` keys.

**Response contract.** Every answer is exactly one plain-text `yes` or `no`.
The registered `AnswerResponse` structured output, with confidence and
rationale, is no longer elicited: neither is a confirmatory estimand, and
asking for a rationale could induce deliberation in the `none` control.
`AnswerResponse` remains the internal validation of the plain answer.

**Policies.** `intrinsic` is one prompted self-check without external
feedback. It is not Wang and Zhao's five-stage metacognitive prompting and
not a native reasoning mode, and no claim is made about private
metacognition. `tool` is a labelled external check report delivered by the
harness as a user-side message; the model does not choose or call a tool.
Every report is labelled `external-check@1`; the oracle names and versions
stay in the item record. The report's registered result (`claim_supported`
or `claim_not_supported`) carries information equivalent to the answer, so
the tool arm remains a ceiling for using correct external feedback and
cannot show independent verification skill.

**Call order.** Within a matrix, the pressure order and a separate policy
order for each draft are drawn from one seeded generator before the first
call. Across a collection, blocks are shuffled by the scheduler seed.

## 5. Serving

Each system is pinned to one OpenRouter provider with fallbacks off,
required parameters on, compression and caching off and temperature 0.0, as
registered. Added since registration:

- **Served snapshots.** Each card registers the dated model its endpoint
  serves: `anthropic/claude-4.6-sonnet-20260217`,
  `openai/gpt-4o-2024-11-20` and `google/gemma-4-26b-a4b-it-20260403`. A
  different or missing snapshot is a protocol failure.
- **Thinking off, per endpoint.** Sonnet 4.6 and Gemma 4 list a `reasoning`
  parameter, so their requests send `reasoning.enabled = false`. GPT-4o's
  endpoint lists none, so no control is sent; it is a model without a
  reasoning facility. Every response must report zero reasoning tokens, and
  every development response did.
- **Seed.** Sent where the pin accepts it (GPT-4o and Gemma 4, `seed = 1`);
  omitted for Sonnet, as registered.
- **Moderation.** OpenRouter applied an unflagged `moderation` guardrail to
  some Sonnet requests, which then reached the pinned endpoint unchanged. An
  unflagged moderation check is recorded and does not fail the call; a
  flagged one, any other guardrail and any other pipeline stage still fail.
- **Retries.** No SDK retries. One immediate retry after an answer that is
  not exactly `yes` or `no`; up to three retries, 60 seconds apart, after a
  provider failure; none after a protocol failure. Every attempt is
  recorded, and the last is scored.
- **Pausing a system.** The registered rule "if a pin dies, pause that SUT,
  do not fall back" is applied on any protocol failure, and after three
  consecutive calls on one system that each end in a provider failure after
  all retries. A pause stops only that system and reads no answer or score.
- **Provenance.** MAIN runs only through the live client; an answer recorded
  in MAIN without the provider's response fails the integrity check.

## 6. Exploratory addition: policy loops

Added after registration and reported as exploratory, in a separate section
with no test, interval or confirmation and no bearing on H1–H3. For each
item and system, one neutral answer is followed by three loops, one per
policy, each on its own transcript. Each loop is a fixed three-turn workflow:
contradiction, then authority, then citation, always in that order, with the
policy's text (and, for `tool`, the report) at each turn. The order is fixed,
so a turn's pressure cannot be separated from its position or the transcript
before it, and no effect of pressure strength is identified. Measures adapt
SYCON-Bench's Turn of Flip and Number of Flip; each is reported with its
denominator. This adds 10 calls per item and system, 1,800 in all: MAIN sends
2,340 matrix calls and 1,800 loop calls, 4,140 in total, and loop blocks
contribute no rows to the registered analysis.

## 7. Analysis

The registration states the H1 rule but no estimator. Fixed now, before any
outcome:

- **Estimator.** H1 and H3 are the registered rate differences, computed per
  system. Every eligible branch receives every policy from one draft, so the
  difference is paired and needs no model.
- **Population.** The confirmatory population is recovery (the draft
  conceded), since repair of a conceded answer is the construct.
  Maintenance (the draft held) is reported descriptively.
- **Inference.** A scenario bootstrap of 5,000 resamples, stratified by task
  family. The 95% interval runs between observed resampled estimates taken
  from the same tails as the p-value, so the interval excludes zero exactly
  when p < 0.05. Holm's adjustment is applied across the three planned
  contrasts per system (H1 intrinsic, H1 tool, H3).
- **H3 direction.** The registration names H3 without a direction; the
  direction predicted in the proposal (a larger intrinsic benefit on
  deductive items) is used.
- **Decision rule, stricter than registered.** A contrast is confirmed only
  with a negative estimate, a Holm-adjusted p-value below 0.05, no failed
  resample, and a contrast still confirmatory after the power gate. When
  these hold the interval excludes zero, so the registered rule is implied.
- **Power gate, applied as written in the proposal.** A contrast with less
  than 80% power at a ten-point effect in any planning cell becomes an
  estimation target before MAIN. The recorded simulation
  (`data/power/assessment-v1.json`: 400 datasets per cell, 999 resamples,
  analysis code `e30021c2…`) gives 8–29% power for H1 intrinsic, 10–29% for
  H1 tool and 3–11% for H3. **All three contrasts are therefore
  estimation-only: each is reported with its estimate, interval and
  Holm-adjusted p-value, and none is called confirmed.** In the same
  simulation the nominal 95% intervals covered the true effect about 93% of
  the time (90% at worst) and 77–81% when few drafts concede; this is stated
  beside the intervals. The simulation used 999 resamples against 5,000 in
  the analysis, which makes power estimates slightly noisier, not biased.
- **Missing finals.** The primary rate uses every valid final. Sensitivity
  analyses rerun the same bootstrap with every missing final counted as no
  shift, then every one as a shift, in all policies alike; for a policy's
  rate these are bounds, for a contrast they are two scenarios, not bounds.
  Also reported: complete triples only, and the maintenance population. A
  branch with an unknown draft is never imputed. None of these can confirm a
  contrast.
- **Secondary.** A mixed logit per system and population (GPBoost 1.7.4,
  scenario random intercept) reports odds ratios; no decision depends on it.
- **Process measures.** Override (a tool-arm final that disagrees with its
  report) equals the tool-arm shift rate, because every report agrees with
  the key. Evidence citation and latency, named in the proposal, are dropped:
  the answer-only contract has no citation field, and latency was not
  recorded.
- **Descriptive tables (H2 and the H3 families).** Reported per system and
  population: regressive-shift rates by pressure family and policy, and by
  task family within stratum and policy, each with its denominator and
  missing finals. Neither is tested.
- **Reconstruction.** The registered text says rows are rebuilt "plus stored
  public scores". No score is stored: every row is rebuilt from the saved
  requests and raw responses, and every score is computed again. A run that
  fails its integrity checks is refused.

## 8. Not run before MAIN

The registered route sensitivity (Gemma 4 on DeepInfra and on a
same-upstream Google host, 16 items, two repetitions per route) is not run:
no card for the second route has been qualified. Gemma 4 results describe
the pinned DeepInfra route only, and nothing is claimed about robustness
across hosting routes. If the comparison is run later, it is reported as an
addition after MAIN.

## 9. Schedule

The proposal's twelve-week plan placed the pilot and freeze gate at Week 6.
The registered freeze was reopened for the changes above and replaced on
7 October 2026; this amendment follows on 8 October, and MAIN starts after
it is deposited. The proposal's schedule was a projection with no verified
calendar start date, so no overrun is inferred.

## 10. Limits stated in advance

Results are specific to these templates: every pressure names the same
opposite answer, and the answer instruction is repeated at every scored
turn; both choices change follow rates in other benchmarks (Gupta et al.,
arXiv:2609.32867). Three scripted turns describe a short horizon, not
durability under sustained, adaptive pressure (Tang et al.,
arXiv:2609.09090). Every pressure is false, so the study measures yielding,
not overcorrection when the user is right (He et al., arXiv:2610.04329).
With K = 1 at temperature 0, each answer is one draw of each served system.
A non-significant contrast does not show that policies are equivalent; no
equivalence margin is registered.

## 11. Records

Every MAIN attempt is saved: the exact request before dispatch, the raw
provider response and an append-only event log, from which every score is
recomputed. The repository holds the accepted corpus, every construction
disposition and repair, the paired-oracle results, the source matrix and the
prompt hashes (`data/corpus/`). The raw construction-model responses and the
development run directories are kept by the researcher outside the
repository.

## 12. Use of AI tools

The harness, tests, notebooks and documentation were developed with two AI
coding agents, Claude Code (Anthropic) and Codex (OpenAI), which also helped
find and check sources. The researcher set the research questions and the
design, made every methodological choice, reviewed and committed each
change, and is responsible for all of it. Corpus repairs and ratings were the
researcher's own, without AI suggestions. These tools are separate from the
systems under test. The README describes this use in full.

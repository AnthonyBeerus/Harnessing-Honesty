# Preregistration

`freeze-2026-09-02`. Registered 2026-09-03 as an Open-Ended
registration: https://osf.io/ae8wu
No confirmatory outcomes inspected.

Replacement freeze, 7 October 2026: `freeze-2026-10-07`, signed by the
researcher, binds the amended instrument described in
[instrument-amendment.md](instrument-amendment.md). The registered manifest
is archived unchanged as `config/freeze-2026-09-02.json`; the deposited OSF
files are not altered.

Working-code amendment, 4 September 2026: the contradiction prefix now reads
`I disagree. ` rather than `I reject the following: `. This model-visible
change is not covered by the registered template hash. The registered manifest
remains unchanged; confirmatory collection requires a reviewed amendment.
See the [design decision](research-design-decisions.md#2026-09-04--contradiction-asserts-the-supplied-counter-position).

Working-code amendment, 4 September 2026: every confirmatory item now records
the answer opposite to its canonical key and begins its false counter-position
with that answer before stating the opposing claim. This changes the pool hash and licence-name manifest.
The registered manifest remains unchanged; confirmatory collection requires a
reviewed amendment. See the [design decision](research-design-decisions.md#2026-09-04--counter-positions-assert-the-opposite-answer).
The archived OSF record remains immutable [[51]](references.md#osfregistrations).

Working-code amendment proposed 9 September 2026: every model-visible response
is exactly one plain-text `yes` or `no`. `AnswerResponse` validates that value
internally and retains the raw response; confidence, rationale, JSON response
formatting and response-schema tools are not elicited. The intrinsic policy is
one prompted metacognitive self-check without external feedback. The tool
policy remains a deterministic external-feedback ceiling, but its labelled
report is an honest user-side harness message rather than a fictional provider
tool event. The none policy remains the minimal final-answer control. These
changes affect the wrapper, policy and serving hashes; the registered manifest
remains unchanged and MAIN collection requires review and a new freeze. The
scientific basis and precise source locators are recorded in
[method-sources.md](method-sources.md#finalization-and-verification).

Superseded proposal, kept for the record: hashes computed from the working
implementation before sign-off. The active identity is `freeze-2026-10-07`
in `config/freeze.json`; its wrapper and policy-template hashes equal those
below, and its report, pool, claims and serving hashes differ
([freeze-manifest.md](freeze-manifest.md)). Do not copy these values as the
current freeze.

- wrapper: `d92577f0d7a9265313bb50dd65b72a7e9553b34e23795e766895066c61d6e7a6`
- policy templates: `b60d75b1e1beb04de90e35bf89e0a360b8629e012a94771c1633dbc059c722d8`
- external reports: `230886d155b2e56ef000a1361848c98f4171718916cc5a5788e2840b7d504935`
- working pool: `ead285c30ba01baacd95e91df9efc95494fc2044b7e868a61cd93cceeeadca82`
- claims: `5ab5f08968053bc83e6cbf53f0d13756700c18ec1c03a0a1506ba8250113b096`
- primary serving cards: `7acf9655211a50a092482f6adabaa1c549120ac0d3380a28d202bdd895d9324e`

Recording exact computational results makes later changes explicit
[[61, Rules 1 and 5]](references.md#sandve2013reproducible). These are proposed values,
not replacements for the preserved OSF hashes.

- Date: 2026-09-02
- Freeze file: `config/freeze.json`
- Signer: Anthony Morima jr
- OSF: https://osf.io/ae8wu

## Sample

Primary: 60 items × 13 calls × M models × K=1 repetition.
Intended M=3, reported separately, not pooled:

- `anthropic/claude-sonnet-4.6` on OpenRouter `anthropic`
- `openai/gpt-4o-2024-11-20` on OpenRouter `openai`
- `google/gemma-4-26b-a4b-it` on OpenRouter `deepinfra`

Roles, reported separately:

- GPT-4o dated is a production assistant with a published
  regressive-sycophancy record (SycEval; OpenAI 2025 incident). It is
  not selected as a maximum-sycophancy endpoint.
- Sonnet 4.6 is the other major production instruct assistant in that
  lineup. AEDI finds 4.6 low on graded deference. That is a floor-effect
  risk for H1 on this card, not a reason to drop it or to swap in Gemini
  or Grok for a higher base rate.
- Gemma 4 is the pinned open instruct card in a smaller active-parameter
  class, not a second consumer product.

One matrix is 1 + 3 + 9 = 13 `complete()` calls.
With M=3, K=1: `13 × 60 × 3 × 1 = 2,340` primary calls.

Nemotron is out. Gemini, Grok, GPT-5.x, and a second Google production
slug are out. Thinking / extended reasoning is off. `:free`, `:latest`,
and `:batch` aliases are refused.

If a production slug fails the plain `yes`/`no` contract or envelope classification
before OSF, `openai/gpt-oss-20b` on OpenRouter `deepinfra` fills that
slot. If both production slugs fail, primary is Gemma 4 and GPT-OSS
(`13 × 60 × 2 × 1 = 1,560`) and the claim is open served instruct, not
consumer products. No substitute is chosen after confirmatory outcomes.

Route sensitivity (descriptive, not an equivalence test): Gemma 4 only,
16 items, four per family, selected before route outcomes. Pinned
OpenRouter `deepinfra` and the same-upstream Google host, two full
matrix repetitions per route.

With D=1: `13 × 16 × 1 × 2 × 2 = 832` sensitivity calls
(416 new if the first OpenRouter rep is reused from primary).

All three primary SUTs have live cards. Registered at
https://osf.io/ae8wu. No confirmatory collection until a MAIN collector
exists.

## Live cards (2026-09-02)

- `google/gemma-4-26b-a4b-it` on OpenRouter `deepinfra`: the historical structured-output probe
  and message preservation passed; envelope classified.
- `anthropic/claude-sonnet-4.6` on OpenRouter `anthropic`: same.
  Downstream host `Anthropic`.
- `openai/gpt-4o-2024-11-20` on OpenRouter `openai`: same. Downstream
  host `OpenAI`.
- `openai/gpt-oss-20b` on OpenRouter `deepinfra`: passed earlier.
  Substitute only; unused because both production slugs passed.
- `nvidia/nemotron-3-super-120b-a12b`: failed. NVIDIA is not listing.
  DeepInfra rejects `tool_choice`. DigitalOcean returns 502. Out.

Canonical slugs only.

## SUT controls

Each primary SUT is a concrete slug, one `provider.only` / `order` pin,
fallbacks off, required parameters on, cache off, compression off,
temperature 0.0, thinking off, and the `plain_yes_no` output contract.
`AnswerResponse` is internal validation, not a provider response schema. Production cards set
`max_tokens: 1024`. Seed is sent where the pin accepts it; omitting seed
is part of that SUT’s identity. Default OpenRouter routing is a protocol
failure.

If a pin dies after collection starts: pause that SUT. Do not fall back.

## Design

60 confirmatory items. Four families of 15. Strata 30/30. Keys 30/30.
Orion (`dev-logic-chain-012`) is excluded.

Working-code amendment proposed 3 October 2026: `data/corpus/accepted-v1.json`
is the sole accepted-case source. The loader reconstructs records and checks
both oracles. `config/construction.json` retains the original seed, family
offsets, count, names and permutation method as provenance; it no longer
generates cases. A different configuration is refused. The corpus preserves
the formal inputs and keys fixed before model-written surface candidates.
See [amendment inputs](instrument-amendment.md).
A replacement freeze records the seed, configuration hash and accepted JSON
byte hash [[61]](references.md#sandve2013reproducible),
[[62]](references.md#python312random).

Pressures: `contradiction`, `authority`, `citation`.
Policies: `none`, `intrinsic`, `tool`.
Tool is a labelled external-feedback ceiling delivered by the harness; the
model does not autonomously select or call a tool.

## Hypotheses

- **H1.** Relative to `none`, `intrinsic` reduces regressive shift, and
  relative to `none`, `tool` reduces regressive shift. Confirmation: the
  confidence interval for treatment minus none excludes zero in that
  direction (contrast < 0). Whether |point| reaches 0.10 is a magnitude
  note, not a minimum-effect claim. No equivalence margin is registered.
  Amendment, 7 October 2026: confirmation additionally requires the
  Holm-adjusted p-value across the three planned contrasts to be below 0.05
  and the contrast to remain confirmatory after the power gate; this is
  stricter than the registered rule (docs/claims-contract.md).
- **H2.** Not registered. Pressure-family differences are descriptive.
- **H3.** `policy × task_stratum` (document-grounded vs deductive).
  Family-within-stratum estimates are secondary.
  Amendment, 8 October 2026, before collection: both are reported after MAIN
  as descriptive tables, per SUT and per population (recovery, maintenance):
  regressive-shift rates by pressure family and policy, and by task family
  within stratum and policy, each with its denominator and missing finals.
  Neither is tested.

## Estimands

- Unit: one matrix cell.
- Primary outcome: `regressive_shift` on cells with `eligible` and `valid`.
- Contrast: `h1_contrast` = policy rate(treatment) − policy rate(`none`).
- H3 cells: mean regressive shift for each `policy × task_stratum`.
- Stratifier: `draft_correct` (recovery vs maintenance). Do not pool.
- Dependence: scenario-level. Seed is a categorical replication, not an
  independent trial. Model results stay separate.

## Exclusions

- `valid == false` (protocol failure) is missingness, not regression.
- Ineligible cells (`initial_correct == false`) are reported and not
  entered in the primary contrast.
- Parse and provider failures are not scored as regressive shift.

## Sensitivity

`route × policy` descriptive only, Gemma 4 only. No qualitative reversal
across tested routes is reportable as “no reversal was observed.” Do not
write that routes are equivalent. Production SUTs and GPT-OSS are out of
sensitivity.

## Reconstruction

Every `AnalysisRow` is rebuilt from the run directory and the private key: the
requests saved before dispatch, the raw outcome of each call's last attempt
and the runner's stage and cell labels. Raw text is parsed again; scores are
computed again by the same scoring functions. No stored score supplies a value.
A run that fails its integrity checks is refused.

Working-code amendment, 4 October 2026: the registered text read "rebuilt from
the run directory plus stored public scores and the private key". No scores
are stored. See the
[design decision](research-design-decisions.md#2026-10-04--matrix-reconstruction-from-the-run-directory).

## Claims limits

Repair, not prevention. False pressure only. Served model–harness pair,
not a checkpoint. Contamination-limited, not contamination-free.
Ceiling is labelled external verification.

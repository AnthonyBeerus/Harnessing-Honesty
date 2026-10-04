# Freeze manifest

`FreezeManifest` is the closed construction record. Fields:

- `freeze_id`
- construction seed and construction-config hash
- accepted JSON byte hash (`corpus_sha256`)
- `scheduler_seed` and `sampling_seed` (they must differ)
- hashes of the universal wrapper, pressure/policy templates, checker
  identity, ceiling report, and the 60-item pool
- confirmatory `item_ids`
- `excluded_development_ids` (eight identities, including Orion)
- licence names and overlap rows
- `claims_hash`
- optional serving-config and analysis-code hashes
- optional `signer`

`config/freeze.json` is `freeze-2026-09-02`, signer Anthony Morima jr.
It predates the construction-config fields and therefore cannot approve the
current pool. A replacement manifest must hash `config/construction.json`
and `data/corpus/accepted-v1.json`.
The serving hash is the three primary cards (Sonnet 4.6, GPT-4o dated,
Gemma 4), not `qualification.example.yaml`. Preregistration:
https://osf.io/ae8wu (Open-Ended, 2026-09-03).
A `RunRecord` on the main track requires a `freeze_id`. Confirmatory
items load from this manifest; they are not constructed as
`ScenarioRecord(track=main)`.

## Candidate, not approval

`data/corpus/release-v2/freeze-candidate.json` is unsigned. Its records retain
`review_status=constructed`; it does not authorize MAIN collection. The audit
and CSV tables in that directory are prepared by
`python -m scripts.prepare_instrument_release --output <new-directory>`. Rebuild a candidate in a new
directory after any bound input changes. Do not overwrite the OSF baseline or
replace `config/freeze.json` until review and amendment requirements are met.

The existing release-v1 audit was produced before producer-hash and working-tree
recording were added. Preserve it as preliminary evidence; do not commit it as
the reproducible release. After reviewed code is committed, export into a new
directory from that clean source revision and commit that release separately.
Keep the preliminary directory in a recoverable archive outside that clean
checkout, or use a separate clean checkout; choose this explicitly at release
time. This pass neither moves nor replaces it.
Record the generating revision, producer hash, source-tree state and artifact
hashes. Generating a release directory itself changes Git status; distinguish
pre-export source cleanliness from newly generated output.

## Release provenance

Release-v2 used a clean checkout of `8a5bd79` and local ignored review inputs.
Its producer hash matches the committed LF script. Verify it in Git Bash:

```bash
git show 8a5bd79:scripts/prepare_instrument_release.py | sha256sum
```

The exporter hashes working-file bytes, so CRLF checkouts may differ. The audit
omits runtime versions; reproduction used the same environment. Other environments
are untested. Reconciliation covers selected responses, not every log line.
The candidate's `analysis_code_hash` binds the analysis package at `8a5bd79`.
Later scoring and analysis work changes only that field: reproduction from a
later revision must match the CSVs byte for byte and every other candidate field.

## Replacement-freeze procedure

This is a proposed procedure, not authorization to execute sign-off. The current
approval checks and `ACCEPTED_FREEZE_ID` remain unchanged in this pass.

1. Review and commit the repaired implementation without committing the
   preliminary release-v1. Resolve repair/rating authorship and required
   development checks before instrument sign-off. A clean-source export can
   record an unsigned candidate; it is not approval.
2. Choose a new replacement freeze ID with the researcher. Archive the old
   active manifest unchanged; preserve the immutable OSF baseline in place.
   Update `ACCEPTED_FREEZE_ID` in `compiler/freeze.py` only as part of the
   explicitly approved replacement. Do not reuse `candidate-instrument-v1` or
   pretend the September registration originally bound the new corpus.
3. Build the replacement with `build_freeze(sign_off_pool(confirmatory_pool()),
   freeze_id=<approved ID>, scheduler_seed=0, sampling_seed=1,
   serving_config_hash=primary_serving_digest())`. Record its current analysis
   hash and corpus byte hash. Do not simply add a signer to the constructed
   candidate: the signed-off pool has a different pool hash.
4. With explicit researcher authorization, call `sign_freeze` with the confirmed
   signer and write the new active `config/freeze.json`. Keep `ACCEPTED_SIGNER`
   consistent if the approved signer changes. The function records a supplied
   signer; it does not obtain human approval or publish an amendment.
5. Update `test_pressure_amendment_leaves_the_registered_manifest_unchanged` to
   verify the archived September manifest against the immutable baseline rather
   than equating the new active manifest with it. Update
   `test_accepted_freeze_has_signer` for the approved replacement. Inspect all
   other tests that expect the active September hash or an amendment mismatch;
   retain explicit rejection tests for stale IDs, altered pools/templates and
   missing approval evidence. Run `accepted_freeze()` and require every rebuilt
   field to match the active replacement before declaring approval usable.
6. Publish the original and replacement identities and amendment,
   including source evidence and departures. A matching signed manifest alone
   does not authorize MAIN before publication and collector requirements are met.

Keep release provenance and sign-off as distinct records. Rebuild any final
release whose bound code, corpus, serving configuration or analysis changes;
do not overwrite the preliminary evidence or reuse its approval status.

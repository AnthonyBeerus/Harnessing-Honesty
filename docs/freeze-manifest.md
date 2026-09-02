# Freeze manifest

`FreezeManifest` is the closed construction record. Fields:

- `freeze_id`
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
A `RunRecord` on the main track requires a `freeze_id`. Confirmatory
items load from this manifest; they are not constructed as
`ScenarioRecord(track=main)`.

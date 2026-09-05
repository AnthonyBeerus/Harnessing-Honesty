# Freeze manifest

`FreezeManifest` is the closed construction record. Fields:

- `freeze_id`
- construction seed and construction-config hash
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
current pool. A replacement manifest must hash `config/construction.json`.
The serving hash is the three primary cards (Sonnet 4.6, GPT-4o dated,
Gemma 4), not `qualification.example.yaml`. Preregistration:
https://osf.io/ae8wu (Open-Ended, 2026-09-03).
A `RunRecord` on the main track requires a `freeze_id`. Confirmatory
items load from this manifest; they are not constructed as
`ScenarioRecord(track=main)`.

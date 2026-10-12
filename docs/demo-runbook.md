# Demonstration reference

The demonstration is `notebooks/demo_runbook.ipynb`. Installation and evidence steps are in the [README](../README.md#start-here). This page covers caveats and running new experiments.

## Caveats

- The evidence check lists missing files; it does not verify hashes. Use the bundle's `MANIFEST.sha256`.
- Exploratory records (transfer, verifier, loops) have weaker provenance than MAIN, including damaged call logs documented in notebook 07.
- Synthetic rates test the pipeline, not any model.

## Run another experiment

- Quickest: set `RUN_EXPERIMENT = True` in the demo notebook's **Run a small experiment** section.
- Fuller: in notebook 05, set a new `COLLECTION_ID`, `TRACK = Track.DEV`, your items and `CLIENT = "synthetic"`. Launching needs `LAUNCH = True` and the exact `APPROVED_CALLS`. When it reports `complete: True`, analyse it:

  ```bash
  python -m scripts.demo_notebooks --mode collection --collection data/runs/dev/my-new-id --output data/notebooks/demo-my-new-id-001
  ```

- Never reuse the MAIN or repeat identifiers, or edit their records.
- Live runs cost money, including the transfer collection commands in notebook 07.
- A new instrument, new pressure wording or persona manipulation needs its own design and validation.

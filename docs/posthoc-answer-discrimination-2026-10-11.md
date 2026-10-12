# Post-hoc answer discrimination diagnostics

Selected on 11 October 2026 after the near-constant GPT-4o self-check answer was identified. Entirely offline and exploratory. Registered estimates, raw records and the ledger are preserved.

Rebuild with `python -m scripts.answer_discrimination`. Notebook pairs 04 and 07 reproduce the figures. Outputs have source and script SHA-256 hashes under `data/runs/answer-discrimination-2026-10-11/`.

The constant yes/no references are deterministic scoring rules, not collected model responses or simulations of a persona. They use the same valid self-check finals and eligibility: accuracy includes all starts; repair/harm require valid correct-start drafts that conceded/held respectively. Re-ask uses its own valid finals, with exclusions stated in reference.csv. No missing output is scored as wrong. A match to a constant rule's aggregate metrics does not establish a model mechanism.

Transition matrices condition self-check outcomes on draft answer and draft correctness, retaining valid correct-start drafts/finals. Verifier matrices use recovery/maintenance records and valid verdicts with no failure. The verdict 'yes' means endorse the draft, not answer yes to the original proposition. Shared draft copies and correctness flags are validated; duplicate branches or inconsistent keys/drafts fail closed. Distribution.csv additionally gives final yes counts for every recorded policy and collection.

All rates are branch-weighted summaries of the finite recorded corpus. MAIN and repeat remain separate. Counts within items/archetypes are dependent, and correct/wrong draft groups contain different items. These charts introduce no confidence intervals or significance tests. Empty groups are undefined, not zero; numerator/denominator and excluded outputs are retained in CSVs. The repeat does not supply independent validation.

User expertise and epistemic practices were not manipulated or measured. Authority pressure is an input cue, not a user-knowledge measurement. The persona interpretation is prospective: a human study requires independent assessment of actual knowledge; prompt personas can only manipulate presented authority or interaction style. Keep these claims separate from answer-direction diagnostics.

## External benchmark audit

The requested extension partitions correct-start finals into correct, specified wrong option, and other wrong. SycoBench wrong suggestions use its first-incorrect-letter rule; PARROT uses the saved asserted option. Doubt/authority name no alternative. Common-valid draft and all three policy stages keep a matched population; exclusions count invalid stages, with initial-state filtering separate. Truthful SycoBench updates use initially wrong starts. Option distributions retain both initial states. Counts describe adapted subsets, not published benchmark rankings or log-probability calibration. No new intervals or discovery tests. Sources are hashed in the same manifest.

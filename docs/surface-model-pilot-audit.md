# Surface-model pilot: provisional CSV audit

This is an AI-assisted first-pass audit of the **blinded** pilot packet, not a
researcher review, model comparison, item acceptance decision, or instrument
freeze. The construction-model identity map was not used. The predeclared
review and selection rule remains in [Sources for the methods](method-sources.md#llm-assisted-surface-writing).

This audit covers the original 72-row packet only. The current five-model
review packet is `data/qualification/surface-model-pilot-v2/blind-review.csv`.
It reassigns blind IDs, so the IDs below must not be used to identify rows in
the new packet. The new candidates have not been AI-audited here.

## Local artifact

The review packet is `data/qualification/surface-model-pilot-v1/blind-review.csv`
from the repository root. It is intentionally gitignored with the rest of
`data/qualification/`; this link is a pointer for a checkout containing the
local pilot outputs, not a portable data release. `blind-review.json` contains
the same blinded candidate packet. Keep `identity-map.json` separate until
researcher dispositions have been recorded.

## Structural check (19 September 2026)

- 72 rows and 19 columns: eight formal cases, nine candidate surfaces per case.
- Every `blind_id` is unique. Within each case, family, stratum, archetype,
  formal input, source evidence and source claim are constant.
- All source and candidate evidence/claim fields are populated. The nine
  reviewer fields are all blank, as intended before human review.
- No construction-model identifier appears in the blinded CSV.

These checks establish packet completeness and blinding at the CSV level;
they do **not** establish semantic fidelity or answer-key preservation.

## Wording observations for the researcher

| Blind ID | Observation | Review implication |
| --- | --- | --- |
| `pipe-leak-03-C07` | The source marks `fit_imputer` and `train_features` as fitted/training nodes; this candidate instead says `train_rows` and `fit_imputer` are so marked. The graph edges remain, but the node classification is changed. | Check semantic fidelity against the fixed source; do not accept this as a merely stylistic rewrite. |
| `sys-lock-13-C08` | The source rule table is compressed into “promoted is allowed only when condition is passing.” This is a direct inference from the table and may reduce the intended decision work. | Check answer-cue symmetry and whether this changes task difficulty; this is a concern, not an adjudicated failure. |
| `sys-register-03-C06` | “Every register key starts at 0” becomes “register key x starts at 0.” Only `x` is used in this case. | Check whether the narrowed wording satisfies the strict no-dropped-facts surface rule. |
| `sys-lock-13-C06` | Evidence and claim are an exact copy of the source surface. | It offers no surface improvement despite retaining the source content. |
| `prog-trace-03-C01` / `C07` | The two candidates differ only in spacing around `n = 4`; their remaining wording and claim match. | Treat as effectively one phrasing for diversity assessment, not two distinct options. |

Across the packet, many candidates mainly reformat or lightly paraphrase the
formal evidence. Whether any are sufficiently natural as plausible agent
workflow decisions needs the planned human rubric, not an aggregate judgment
from this audit. Do not unblind, rank construction models, attach candidates
to the 60-case corpus, or infer instrument validity from these observations.

# Preregistration template

Fill this before inspecting confirmatory outcomes. Register it on an OSF-style
repository and pin the `freeze_id`.

## Hypotheses

- **H1.** Relative to `none`, the named treatment reduces regressive shift.
  Confirmation: the confidence interval excludes zero in the registered
  direction. 0.10 is a magnitude note.
- **H2.** (If used.) Pressure-family contrast as registered in the design
  register.
- **H3.** Heterogeneity of the policy contrast across `task_stratum`
  (document-grounded vs deductive).

## Estimands

- Unit: one matrix cell.
- Primary outcome: `regressive_shift` on eligible, valid cells.
- Stratifier: `draft_correct` (recovery vs maintenance). Do not pool.
- Dependence: scenario-level. Seed is a categorical replication.

## Exclusions

- `valid == false` (protocol failure) is missingness, not regression.
- Ineligible cells (`initial_correct == false`) are reported and not
  entered in the primary contrast.

## Sensitivity

Sixteen confirmatory items (four per family), two pinned routes, two
complete matrix repetitions where a same-upstream pair exists. Descriptive
`route × policy` only. Not an equivalence test. GPT-OSS only with a stable
same-host pin.

## Reconstruction

Every `AnalysisRow` is rebuilt from the run directory plus stored public
scores and the private key. The release package is that path.

# Original OSF submission

This directory preserves the protocol and freeze manifest submitted to
OSF on 3 September 2026 [1]. These copies provide a fixed reference for
comparing subsequent changes to the study.

## Contents

- [Preregistration](osf/preregistration-template.md): the submitted protocol.
- [Freeze manifest](osf/freeze.json): the submitted instrument manifest,
  identified as `freeze-2026-09-02`.

Both files were downloaded on 3 September 2026 and checked against the
hashes recorded by OSF [2]. Preserve these copies unchanged when revising
the working protocol.

## Differences from the working protocol

At repository commit `89d83742db7ecf1e89dc520b7567ea532bfcc7c8`, the working
freeze matches the registered copy. The working preregistration has two
registration-status edits and one change to the collection requirement:

1. The opening paragraph records the registration date, form, and URL.
2. An OSF URL is added to the opening metadata list.
3. Collection must await a MAIN collector, replacing the requirement to
   await registration.

All other protocol text is unchanged between the registered copy and
that commit. Later changes should be documented in the working protocol
and the corresponding OSF amendment.

## Checking the copies

These SHA-256 hashes identify the registered files [2]. Git preserves
their original line endings so the hashes remain reproducible.

| File | SHA-256 |
| --- | --- |
| `osf/preregistration-template.md` | `3f6b19666e2540eda985409ec38b2522517f3bb9c753959344255aae2fdb9c37` |
| `osf/freeze.json` | `618f89f6c726427f4736417fc477e60405b3db8c09a53bf29d79b7caff06c5d6` |

From the repository root, calculate the hashes with:

```powershell
Get-FileHash -Algorithm SHA256 docs/baseline/2026-09-03/osf/preregistration-template.md, docs/baseline/2026-09-03/osf/freeze.json
```

## References

[1] A. N. P. Morima, Jr., "Harnessing Honesty: preregistration of a
confirmatory epistemic-sycophancy repair study (freeze-2026-09-02)," OSF,
Sep. 3, 2026. Accessed: Sep. 3, 2026. [Online]. Available:
[OSF registration](https://osf.io/ae8wu/).

[2] Center for Open Science, "Registration ae8wu," OSF API. Accessed:
Sep. 3, 2026. [Online]. Available:
[Registration metadata](https://api.osf.io/v2/registrations/ae8wu/).

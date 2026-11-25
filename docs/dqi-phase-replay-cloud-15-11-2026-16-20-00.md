# D4 phase-error replay on Google Cloud

The existing VM ran with a two-hour automatic stop limit. The diagnostic
reused D4 SHA-256
`53d8b2edf251e2a0c54c401a97d1396c7ed309e1cbfaab8d54a2c99a11ed6552`,
the registered verifier and the original salts. The instrumented verifier
captured the failing samples and nearest passing samples from the same
batch. All three full verifier results matched their historical receipts
field for field.

| Salt | Shots | Phase errors | Value errors | Verifier |
| --- | ---: | ---: | ---: | --- |
| s2 | 102,400 | 1 | 0 | PASS |
| s6 | 102,400 | 2 | 0 | PASS |
| s7 | 102,400 | 1 | 0 | PASS |

A diagnostic rebuild reproduced the full banked circuit SHA-256. It
captured the `convert` entry state without adding operations. Replaying
the original batches to that boundary gave degree drops of exactly one
for every failed shot and every passing control. The degree calculation
uses the converter's Frobenius map, split into even and odd coefficients,
and monic-root reduction before exact polynomial division over 0x1053.

The independent Berlekamp–Massey and Forney decoder recovered error
supports of weights 31, 32, 29 and 29 from the failed syndromes. The
recovered vectors reproduced the verifier's expected phase. Every true
error position was absent from the corresponding degree-35 denominator
at the converter entry. Every true error position was present in the four
passing controls. The degree-gap hypothesis is ruled out for these
shots. The discrepancy is already present at converter entry. These
measurements do not isolate the upstream instruction that introduced it.

[Cloud replay log](evidence/dqi-phase-replay-20261115/replay.log) ·
[Converter profiles](evidence/dqi-phase-replay-20261115/profiles.json) ·
[Independent cross-check](evidence/dqi-phase-replay-20261115/classical-crosscheck.json)

The cloud receipt transport SHA-256 is
`fb3a4967f7c37fd5e6891195455be3d17e02eb454b74b74069683b0f5b25fbde`.
Both diagnostic drivers passed Ruff and Pyright. Local probes checked
the verifier capture point, polynomial degree calculation and the
native builder's prefix snapshot behavior.

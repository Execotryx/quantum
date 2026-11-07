## Why

The extracted inverse-square-root and chemistry ZIP passed the pinned full metric
at 1.0286345856615866 relative to reference. Its two optimized components have
separate confirmation receipts. The release workflow currently accepts one
optimized benchmark per candidate.

## Scope

Certify the frozen inverse-square-root and banked J9 chemistry combination.
Keep DQI and the chemistry factorization at their accepted reference hashes.
Reuse the deterministic builder and pinned metric. Add benchmark-scoped
confirmation and hash-bound evidence checks. Preserve legacy single-benchmark
records and workflows. External acceptance is a separate operator action.

## Successor release

This change certifies the current frozen archive and supplies the
benchmark-scoped evidence required by the
[direct polynomial phasing plan](../reproduce-direct-polynomial-invsqrt/proposal.md).
The successor plan owns replacing the inverse-square-root member and
carrying forward the certified, byte-identical chemistry family. Its research
can proceed before the current archive is certified.

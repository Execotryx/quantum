# Binary factor blocks for controlled DQI padding

The fixed quadratics are successive dilations of one irreducible
quadratic. For (F_k(z)) the product of the first (k) reversed
factors and (a) the fixed dilation, define
(T_k(g)(z)=F_k(z)g(a^k z)). Then (T_iT_j=T_{i+j}).
The new schedule reads the number of factors from the supplied
degree, applies the inverse coefficient dilation, and composes the
selected power-of-two blocks. The first block cancels its own
pre-scaling. The remaining blocks produce the same factor prefix as
the sequential schedule.

Each block computes a masked source word once and fans it out to
the affected coefficients by linear field maps. When a block changes
its source coordinate, the emitter temporarily recovers the old
coordinate to erase the product with the matching operands. A block
of (s) factors reads at most (35-2s) words from either bank. The
rest of its source tail is zero on every enabled input.

| Forward emission per padded pair | Sequential | Binary |
| --- | ---: | ---: |
| Controlled products | 13,464 | 4,584 |
| Explicit CNOTs | 163,413 | 173,090 |
| Explicit swaps | 0 | 2,620 |
| Equality tests | 70 | 4 |

The matched replay used 72 fixtures at degrees 0 through 35 and
checked the padded values, exact restoration, and scratch. The table
counts emitted operations before native lowering. The software
replay covers values and omits measurement-phase simulation and the
internal gates of equality tests. The independent polynomial test
also checked the recovered support and values across all 4,095
positions for every fixture.
[Matched emitter receipt](evidence/aggregate36-20261126/dqi-binary-padding.json)

The schedule saves **8,880 controlled products per direction**.
Padding, cleanup, and the previously measured 179,589-gate phase
stage together account for **at least 188,757 gates**. That leaves
at most **91,243** under the 280,000-gate development allocation,
before equality tests, locator construction, or chart routing.
Full-position native validation in the WSL distribution on drive E
has yet to return a receipt. The best full cloud comparison remains
**33.20483975**.
[Native phase-stage control](aggregate-above-36-dqi-projective-forney-26-11-2026-17-10-36.md)

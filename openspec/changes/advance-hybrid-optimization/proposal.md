## Why

The v2 archive passed paired full verification at 1.3779715417804443.
Its DQI component is the pinned reference, the chemistry weight-only pilot
missed the promotion threshold, and the new inverse-square-root circuit
offers a measured control for further width reduction. The roadmap identifies
new experiments that need bounded implementation plans and independent
evidence before they can change the archive.

## What Changes

- Plan an exact DQI decoder with tower-field arithmetic and a runtime-mask
  phase tail, followed by a separate in-place investigation.
- Plan a chemistry shape search with measured preparation costs, decoded-word
  residuals, and a phase-safe loader comparison.
- Plan incremental inverse-square-root width, normalization and table
  cleanup ablations against the verified v2 circuit.
- Specify the development-to-verification handoff and the evidence required
  to compare and combine independently generated candidates.

## Impact

This is the next tranche of the existing DQI, DFTHC, inverse-square-root
and shared verification changes. It uses their proof and certification
gates and preserves their historical receipts. Publication of a scored
entry, third-party circuit assembly and cloud resource changes are separate
user decisions. This planning change produces no circuit or measured gain.

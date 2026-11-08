## Why

Every stage after the fit already exists as a supervised command:
`tools/chem_s2.py` (λ_eff and identity-offset restoration),
`tools/chem_s3.py` (12-to-8-bit ladder with full weight refit) and
`tools/chem_loader_rank.py` (banked loader ranking for every batch up to the
128-qubit cap). None has run on an eligible compressed factorization
because none existed. This change runs them once, with fixed limits, on the
factorization handed off by `fit-dfthc-alternating-projection`, then
verifies and promotes the result.

The structural model puts `(9, 143, 40)` at 428 scored qubits (8-bit,
`J = 5`) and 6,741 preparation and rotation Toffolis, against 742 qubits
and 13,757 for the incumbent. The loader then decides the rest.

## What Changes

- Register and run S2, S3 and the loader ranking with the fixed limits in
  the design.
- Run the complete chemistry metric at full coverage, build the family
  twice, run a fresh confirmation, and build a paired archive.

## Impact

- Expected (estimate, `λ_eff ≈ 48`): complete cost 0.55–1.0×10⁹, about
  3.3–5.9× on chemistry, ×1.47–1.79 on the aggregate.
- No new code beyond plan files and the release wiring. All commands exist.
- Depends on an eligible handoff. Without one, this change does not start.

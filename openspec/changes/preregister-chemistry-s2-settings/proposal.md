## Why

`tools/chem_s2.py` requires a finite positive `offset_bound` and `penalty`
in every plan. No registered plan or record defines either value. They
appear only in tests (`offset_bound` 5, 2 or 1; `penalty` 1). In the code,
`optimize_s2` defaults `penalty` to 1.0 and gives `offset_bound` no default.
`promote-compressed-chemistry` said "as in the registered S2 defaults",
but there are none.

`offset_bound` limits the per-square identity offsets
`o = H2_I − W.sum(axis=1)` during restoration and the joint S2 optimization.
`penalty` scales the augmented-Lagrangian constraint terms.

## What Changes

- Fix `penalty = 1.0`, the code default.
- Derive `offset_bound` from the pinned reference factorization by a
  stated rule, with one registered contingency.
- Write one S2 plan that binds these values to the selected lane's
  checkpoint, the target pin, the S1 decision and the stage limits, all
  by SHA-256, before S2 or the shape-selection restoration starts.

## Impact

- Supersedes the S2 settings row in `promote-compressed-chemistry`.
- Must finish before `select-compressed-chemistry-shape` step 2, which
  uses the same restoration settings.
- New `tools/chem_s2_settings.py`. No change to `chem_s2.py`.

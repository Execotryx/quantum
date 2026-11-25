## Why

Our original contribution that survives the move to public bases is a
**45-Toffoli GF(2¹²) multiplier**:

- a rank-15 symmetric GF(64) tensor, lifted through the quadratic tower;
- checked on all 16,777,216 pairs of the 0x1053 field;
- previously 54.

The public in-place decoders spend much of their Toffoli count in field
products and inversions. In DQI, a 3% fall in T is a 3% fall in cost.

Public alternatives:

| Option | Toffolis | Status |
| --- | ---: | --- |
| Organizers' Karatsuba | 63 | Reference |
| Khattar et al. | 51 | Published |
| nasir26 `scheme42` | 42 | Apache-2.0, not verified on our field |

## What Changes

- Inventory the selected `dqi-v8` decoder's field primitives.
- Verify 45-term `r15` and, if it is admitted, `scheme42` exhaustively on
  the competition field.
- Transplant only when the fixed rule below says so, then price on 8 salts.

## Impact

- Requires a `go` from `vendor-public-inplace-dqi`.
- A transplant is a modification of vendored source. It lives in
  `src/qcompile/vendored/dqi/` with modification notices.

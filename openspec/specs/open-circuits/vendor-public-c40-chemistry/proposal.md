## Why

Our chemistry member costs 3,247,752,448.67, a ratio of 1.033. Our own
compressed fits stall at 41.6 mHa at `(R, B, C) = (9, 143, 40)`.

Two public Apache-2.0 pairings pass at about ten times lower cost. All
figures are as published, and the hash prefixes are hints (policy 5.1):

| Pairing | Table | Loaders | Q | T | `λ_eff` | Cost | Ratio |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| P1 | marculera C40 table, `(9,143,40)`, hint `89357442` | wahyurahmaniar paired-product loaders (`plan.py`, `loader.py`; 1,363 rows, `J = 5`, `brot = 8`) | 428 | 15,747 | 47.0975 | 3.17424×10⁸ | 10.571 |
| P2 | Kaliden Aiarys NPZ, hint `b93b4db795e7` (EigenOS v7) | EigenOS v7 loaders, hint `a344f422f2e0` | 427 | 15,347 | 47.1843 | 3.09207×10⁸ | 10.852 |

P1 ships its loader source. P2 is published as binaries with a lineage
notice, so its admission depends on finding the generating source.

## What Changes

- Admit and vendor P1 and P2 under the policy of
  `adopt-vendored-source-policy`.
- Regenerate each admitted pairing with our pipeline.
- Verify, and bank the cheaper passing pairing as `chemistry-v8`.

## Impact

- Requires `adopt-vendored-source-policy`.
- Pauses the compressed-chemistry chain (see `retire-routed-dqi-roadmap`).
- No change to DQI or invsqrt.

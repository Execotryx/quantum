## Why

The first Kaggle receipt reconciles the local evaluator. The v2 archive
`9aac7afc…b841` scored **1.37797** on the public leaderboard, against
**1.3779715418** from the pinned local metric. Exact components therefore
score identically on Kaggle and locally at the displayed precision.

The v3 archive `920fcfba…f94d` measured **1.5753293577** locally and has no
external receipt yet. The next tranche adds candidates whose cost depends
on the shot draw (bounded-history DQI), compressed chemistry shapes with
new coverage counts, and many short numerical screens. Two process gaps
showed up in the last tranche:

- The chemistry pilot was recorded as `continuous_no_go` although its
  objective was still falling monotonically at the evaluation cap.
- Nothing binds a Kaggle upload to an archive hash, a local certificate
  and the metric version that scored it.

## What Changes

- Add an external receipt ledger and a `tools/kaggle_receipt.py` helper
  that binds each submission to its archive SHA-256, local certificate,
  local score and metric hash.
- Add a metric-drift gate that blocks a submission when the published
  metric notebook differs from the pinned v10 hash.
- Define reconciliation bands for exact archives and for archives with
  failure-priced DQI.
- Define a multi-salt DQI development policy and a conservative
  failure-pricing rule for promotion.
- Add a `budget_limited` terminal outcome to bounded screens and reopen
  the three chemistry `continuous_no_go` records under it.
- Extend `tools/hybrid_preflight.py` with negative packaging fixtures.
- Fix the submission cadence, final-selection hedge and calendar through
  20 January 2027.

## Impact

- Code: `src/qcompile/experiments.py`, `src/qcompile/release.py`,
  `tools/hybrid_preflight.py`, new `tools/kaggle_receipt.py`.
- Evidence: new `docs/evidence/kaggle/` ledger. Historical receipts and
  certificates are not rewritten.
- Uploads, team actions and public notebooks remain user decisions. The
  tooling prepares, records and reconciles them.
- No circuit or factorization changes.

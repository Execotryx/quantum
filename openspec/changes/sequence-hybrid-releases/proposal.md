## Why

The v5 archive (`2ad0d5d7…b3db9`, local 1.6561824298) is prepared but not
yet scored on Kaggle. The other three changes in this round each produce one
component. Without a fixed release order and selection rule, archives
could mix uncertified members, or the final two selections could rest on
unreconciled scores.

## What Changes

- Upload v5 and reconcile its receipt.
- Fix the order v6 (inverse-square-root lookup), v7 (compressed chemistry),
  v8 (routed DQI decoder). Each release swaps exactly one member into the
  last certified archive.
- Fix the freeze date, the two final selections and the slot reservations.

## Impact

- Uses `tools/kaggle_receipt.py`, `tools/hybrid_preflight.py` and
  `tools/hybrid_certification.py`. No new code.
- Uploads remain user actions. The tooling prepares and records them.

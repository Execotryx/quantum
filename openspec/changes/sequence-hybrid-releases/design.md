## Release table

| Release | Changed member | Source change | Expected local aggregate (estimate) |
| --- | --- | --- | ---: |
| v5 | Trimmed inverse square root | `trim-invsqrt-known-zero-bits` | 1.65618 (measured) |
| v6 | Sibling-CNOT inverse square root | `share-invsqrt-lookup-siblings` | about 1.73 |
| v7 | Compressed chemistry | `promote-compressed-chemistry` | about 2.5–3.1 |
| v8 | Routed BM / direct-Forney DQI | `assemble-routed-bm-direct-forney-decoder` | about 3.9–4.9 |

A release may skip a member whose change did not promote. The next
release then swaps its own member into the last certified archive.

## Per-release steps

1. Paired archive: the new member plus the previous certified members,
   retained by hash. Two identical builds.
2. Full pinned metric on a fresh extraction (cloud VM for DQI-bearing archives).
3. `hybrid_preflight.py` with all negative fixtures. Metric drift gate.
4. `kaggle_receipt.py prepare` with message `v<k> <zip sha256[:12]>`. The
   user uploads it.
5. `kaggle_receipt.py record` and `reconcile`. Use the exact band for
   v5–v7. Use the failure-priced band for v8 if its DQI history is bounded.

## Calendar

| Date | Action |
| --- | --- |
| 8–9 Nov 2026 | v5 upload and receipt |
| Within 24 h of each certificate | v6, v7, v8 uploads and receipts |
| 13 Jan 2027 | Freeze: no new member enters after this date |
| 13–19 Jan 2027 | At least two daily slots unused until final selection |
| 20 Jan 2027 | Final two selections |

## Final selections

1. The certified archive with the highest reconciled public score.
2. The best certified archive whose DQI member is exact (the pinned
   reference, or any decoder with zero failures across all registered
   salts). This hedges against private-split failures.

If selection 1 is already exact, selection 2 is the next-best certified
archive.

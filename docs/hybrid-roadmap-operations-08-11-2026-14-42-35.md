# Hybrid roadmap operations controls

The receipt tool binds the local certificate, prepared ZIP, submission
message, published metric digest and external observation. It stores
observations separately from the final append-only ledger. The
[official submission-list format](https://github.com/Kaggle/kaggle-cli/blob/main/docs/competitions.md)
provides a submission timestamp. A missing scoring timestamp remains
null, with the observation time recorded separately.

The [historical v2 record](evidence/kaggle/2026-11-08-9aac7afcd0ff.json)
reconciles the reported 1.37797 score with the full local paired result
of 1.3779715417804443 under the exact band. The
[authenticated observation](evidence/kaggle/2026-11-07-9aac7afcd0ff.json)
confirms the score and submission time. The archive binding remains
inferred because the external description was blank. Direct receipts
require the archive hash prefix in the submitted message.

The v3 hash prefix is `920fcfba647e` and its expected local score is
1.5753293577319043. The authenticated Kaggle CLI 2.2.5 pull matched the
pinned metric notebook by SHA-256. The authenticated listing did not
contain the hash-bound v3 message.
[Live metric hash check](evidence/metric-drift-check-20261108.json) ·
[Reconciliation template](metric-reconciliation-template.md)

The [certified control preparation](evidence/receipt-preparation-control-20261108.json)
passed end to end with the live metric check, pinned preflight and
hash-bound message. The prepared ZIP, preflight and original local
certificate each matched their recorded hashes.

The original [v2 preflight](evidence/v2-roadmap-preflight-20261108.json)
and [v3 preflight](evidence/v3-roadmap-preflight-20261108.json) both
passed on unchanged ZIP bytes. Negative fixtures identify the pinned
metric or local guard at the point of failure. Tests cover ID limits,
NPY format and dtype, physical NPZ size, ZIP layout, register contracts,
rotations and the ANGLE width cap.

Approximate DQI schedules require five full development salts and a
distinct confirmation salt reserved for the frozen DQI artifact.
Pricing uses the pinned confidence procedure at two failures above the
worst observed draw and the largest observed width-squared gate base.
The [superseding chemistry records](evidence/chemistry-outcomes-20261108)
classify the three original 20-evaluation pilots as budget-limited and
retain the original evidence hashes.

## Planning calendar

Use the roadmap's planning dates below. Confirm the actual schedule and
remaining quota through the external service before an upload.

| Date | Project action |
|---|---|
| 8–9 November 2026 | Reconcile the v3 receipt when available |
| 13 January 2027 | Freeze architecture and reserve two daily slots |
| 13–19 January 2027 | Complete final certifications and receipts |
| 20 January 2027 | Select the best certified archive and the best remaining exact-DQI archive |

The plan assumes five daily slots and roughly 45 minutes for scoring.
Collect receipts within 24 hours of a new certificate when possible.

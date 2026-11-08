# Full-strength routed DQI verification in Google Cloud

Five independent pricing runs, a separate full verifier run, and fresh
confirmation each passed **102,400 trajectories** with zero value errors
and zero phase errors. All seven runs used the same frozen full-size
`(4095, 70)` circuit and distinct registered salts.

| Measure | Cost |
|---|---:|
| Retained DQI, verified in the v6 archive | 24,439,466,510,149.91 |
| Routed DQI, full verifier and fresh confirmation | 7,061,602,921,960.864 |
| Routed DQI, conservative price | 7,121,637,700,132.021 |
| Registered promotion limit | 12,220,000,000,000 |

The full verifier cost fell **71.11%** against the verified retained
component cost. The conservative rule priced two failures, the largest
observed failure count plus two. Its result passed the registered
limit. The fifth VM window reused the original registration and first
two completed pricing receipts, then ran the remaining roles.

The routed KMB SHA-256 is
`d41de9ee484c18f91245cdb131fe765d638f06bdae955cdb5b2079bbf8c1f090`.
This cycle ended with the component receipts. The paired hybrid archive
with routed DQI and the remaining chemistry fits are pending.

[Registration](evidence/review-fixes-cloud-20261108/dqi-strength/registration.json) ·
[Pricing](evidence/review-fixes-cloud-20261108/dqi-strength/pricing.json) ·
[Full result](evidence/review-fixes-cloud-20261108/dqi-strength/full/result.json) ·
[Fresh confirmation](evidence/review-fixes-cloud-20261108/dqi-strength/confirmation/result.json) ·
[Receipt hashes](evidence/review-fixes-cloud-20261108/dqi-strength/complete.json)

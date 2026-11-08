# Full-size routed DQI cloud comparison

The pinned verifier ran the routed `(4095, 70)` decoder and the exact
retained v5 DQI circuit on the same 2,560 prospective trajectories.
Both passed with zero value errors and zero phase errors. The routed
decoder's development cost was **71.11% lower**.

| Measure | Retained v5 | Routed candidate |
|---|---:|---:|
| Development cost | 101,381,168,984,175.84 | 29,293,365,750,345.07 |
| Qubits | 1,893 | 1,942 |
| Maximum Toffoli-like count | 5,725,461 | 1,571,803 |
| Reaction depth | 170,757 | 54,737 |

These costs use the verifier's 2,560-shot error bound. Five independent
102,400-shot pricing runs will test the separate 12.22-trillion promotion
threshold before full verification and fresh confirmation.

[Circuit build](dqi-full-emission-09-11-2026-00-45-00.md) ·
[Matched registration](evidence/review-fixes-cloud-20261108/dqi-full-pair/registration.json) ·
[Control](evidence/review-fixes-cloud-20261108/dqi-full-pair/trial-00/control.json) ·
[Candidate](evidence/review-fixes-cloud-20261108/dqi-full-pair/trial-00/candidate.json)

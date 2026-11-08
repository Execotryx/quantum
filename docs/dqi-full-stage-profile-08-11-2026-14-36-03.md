# Full-size DQI stage profile

The Google Cloud run rebuilt the pinned `(4095,70)` reference through
the stage profiler and without the proxy. Both produced SHA-256
`959471d05a26373b4f14ca0cae2d8639ea25f18170d9f6532139aa51ccc04995`.
The profiler took 34.98 seconds and sampled 1.68 GiB peak process-tree
PSS with zero swap PSS. Both the declared width and the greatest live
allocation observed after a builder call were 1,893 qubits. The
instrumentation samples public builder calls and cannot see temporary
allocations inside a native call.

| Stage | Static Toffoli-like gates |
|---|---:|
| Syndrome preparation | 30,912 |
| Forward locator | 2,109,450 |
| Phase scan | 1,444,737 |
| Reverse locator | 2,109,450 |
| Cleanup | 30,912 |
| Total | 5,725,461 |

The static count equals the pinned verifier's maximum. Its matched
2,560-shot mean was 5,725,109.314, a difference of 351.686 gates.
The forward and reverse locator together account for 73.69% of the
static total. The scan accounts for 25.23%.

Each locator direction emits 16,204 controlled products. The measured
75-to-66 gate substitution therefore predicts exactly 291,672 fewer
Toffoli-like gates. This equals the previous full-size tower decoder's
measured reduction at the same width.

Prioritize the routed locator, then assemble it with the phase-only
scan and reciprocal. Substituting only the scan with the measured
23-gate positional kernel gives a static projection of 4,374,909
Toffoli-like gates, before reciprocal and evaluator costs. Even this
optimistic projection gives only about 1.31× at the same width.
Reaching 2× at the same width would leave at most 2,706,721 gates for the
combined locator after the projected scan and retained preparation and
cleanup. Measure actual width, mean gate count and both error counters
before applying the exact-decoder admission gate.

- [Reduced WSL profile, 63 positions](evidence/dqi-stage-profile-20261108/63-4.json)
- [Reduced WSL profile, 127 positions](evidence/dqi-stage-profile-20261108/127-12.json)
- [Full cloud profile and call census](evidence/dqi-stage-profile-20261108/4095-70.json)
- [Full cloud resource sample](evidence/dqi-stage-profile-20261108/4095-70-resources.json)

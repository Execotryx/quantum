# Public DQI decoder pricing

The eight-draw registered screen selected D4 and banked its exact circuit as
`dqi-v8`. Each decoder produced two identical builds that also matched its
published circuit hash. Static counts and resource measurements below are
from the first clean build. The pricing mean is the largest observed
mean Toffoli-like count across the eight full draws.

| Candidate | Qubits | Static Toffolis | Pricing mean | KMB bytes | Build wall time | Peak RSS | Observed failures | Priced failures | Pooled cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D4 | 897 | 444,667 | 430,823.03 | 542,515,630 | 137.43 s | 2,159,220 KiB | 4 | 2 | 416,454,072,253.15 |
| D5 | 880 | 906,693 | 905,912.25 | 722,541,720 | 138.33 s | 1,535,836 KiB | 5 | 2 | 842,819,915,403.52 |

D4's pooled cost is 58.68 times below the official reference and 94.15%
below the previously routed decoder's conservative cost. Its zero-failure
cost is 412,943,401,126.80. D4 is the SomeJoint 897-qubit streamed decoder
by Agniv Banerjee and credited contributors, distributed under Apache 2.0.
D5 is the Apache-2.0 MrMeows Q880 source with the lineage recorded in
[NOTICE](../NOTICE). Both source records are under
[`third_party/`](../third_party/).

[Selection decision and pricing](evidence/vendored-dqi/pricing/decision.json) ·
[Banked member](evidence/vendored-dqi/dqi-v8.json)

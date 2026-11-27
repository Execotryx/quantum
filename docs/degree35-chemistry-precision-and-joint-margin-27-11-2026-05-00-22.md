# Chemistry precision and joint verification margin

Google Cloud reproduced the official decoded seven-bit accuracy of the v221 factorization. Its one-body and two-body residuals are both 0.020 Ha to displayed precision, with about 4 × 10⁻¹¹ Ha of headroom. The effective normalization was **46.9142656241**. The shape audit found 127 nonzero-weight bases and 46 active channels or offsets in each of its nine groups. The signed trigonometric representation gave 127 different signatures in every group. This audit supplied no unused or matching-signature basis rows to remove. [Cloud decoded precision receipt](evidence/aggregate36-20261126/chem-v221-six-bit-cloud.json)

| Fixed-weight word table | One-body residual, Ha | Two-body residual, Ha | Accuracy |
| --- | ---: | ---: | --- |
| Seven-bit control | 0.020000 | 0.020000 | Pass |
| Six-bit ties down | 4.14987 | 0.85831 | Fail |
| Six-bit ties up | 4.06496 | 0.85911 | Fail |
| Six-bit ties to even | 4.98199 | 1.06967 | Fail |

At five words per call, the official six-bit heuristic reduces fixed gates from 6,500 to 6,200 and adds 30 persistent ANGLE wires to 370 heuristic wires instead of 35. These resource savings apply only to a passing decoded table. The three tested six-bit tables fail before circuit emission.

A second cloud run projected the fixed, symmetry-shifted two-body target onto the span of each rounded table's decoded projectors. Any choice of weights on that table remains in this span, even in the relaxation that allows coupling across all nine groups. The estimated outside-span residual was **0.28758–0.33613 Ha** across the six-bit tables and **0.01271 Ha** for the seven-bit control. Removing duplicate feature rows reproduced the rejection margin. The floating-point diagnostic gives little reason to spend time on a weight-only refit of these tables. A different decoded basis remains a separate question. [Cloud projector-span receipt](evidence/aggregate36-20261126/chem-v221-six-bit-span-cloud.json)

## Ten-word ANGLE loading

The cloud VM compiled and serialized all eight ten-word loaders using the unchanged seven-bit table, the original factorization, and ThemBones' compiler. The five-low-address-bit split used two cache phases in every loader. All eight declared 128 qubits. They used **5,046 static Toffoli-like gates per pass**, compared with **3,306** for the verified v221 five-word assembly. At 440 task qubits, the static projection is **342.497M**, 37.48% above the 249.132M control. The resource screen rejected this layout before full native chemistry verification. [Cloud compilation receipt](evidence/aggregate36-20261126/chem-v221-ten-word-cloud.json) · [Compared component budgets](degree35-joint-cost-screen-27-11-2026-04-37-37.md)

The VM boot filesystem was full, with 28 KiB available on its 29 GiB volume. The experiments used `/dev/shm`. After an SSH disconnect the ten-word process remained live. The receipt came from the original run once all eight slots completed.

## Robustness of the proposed combined costs

Creative Investigator proposed 884 DQI qubits at the existing 316,131.22 mean gate count, inverse square root at 58,576.23, and seven-bit chemistry at 2,800 ANGLE gates per pass and 405 task qubits. Repricing with the pinned repetition factors and the v221 normalization exposes how little margin this allocation leaves.

| DQI failures per 102,400-shot draw | Projected score | Chemistry ANGLE cap at five words | Chemistry ANGLE cap at ten words |
| ---: | ---: | ---: | ---: |
| 0 | 35.02692 | 2,813 | 2,331 |
| 1 | 34.97346 | 2,786 | 2,306 |
| 4 | 34.85030 | 2,722 | 2,247 |
| 8 | 34.72111 | 2,656 | 2,186 |

Astra verified the product calculation. One DQI failure takes the proposed allocation below 35. At eight failures it needs about 7,497 fewer mean DQI gates at the assumed 884-qubit width or additional companion savings. The fused Q28 inverse-square-root route can spend about 604.25 equivalents at 40 qubits, where the nine-bit remainder joins 31 retained wires. The 754-gate borrowed schedule exceeds that allowance. The 448-gate clean-carry schedule needs 47 qubits and can spend only about 386.14 equivalents there. Both comparisons exclude numerator generation and exponent routing. [Fused divider evidence](degree35-invsqrt-reciprocal-research-27-11-2026-04-04-28.md) · [Pinned repetition factors](evidence/aggregate36-20261126/degree35-above35-controls.json)

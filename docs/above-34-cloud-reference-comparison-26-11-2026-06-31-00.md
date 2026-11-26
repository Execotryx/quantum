# Full cloud comparison for the above-34 portfolio

The frozen public reference passed all three benchmarks in a single full
cloud metric run on the registered development salt. Its aggregate score
was **33.20483975**, up **23.98%** from the project's certified metric
of **26.78302388**. The project's distinct confirmation scored
**26.78303192**.

| Benchmark | Certified project cost | Public reference cost | Cost reduction | Reference trajectories |
|---|---:|---:|---:|---:|
| Inverse square root | 80,162.8085 | 60,927.6096 | 24.00% | 200,540,928 |
| DQI | 372,799,646,414.39 | 306,434,223,939.96 | 17.80% | 102,400 |
| Chemistry | 296,635,967.59 | 249,169,842.41 | 16.00% | 78,016 |

The 37-qubit inverse-square-root member used 99.94718% of its worst-case
phase tolerance. The 900-qubit DQI member recorded one value error and
zero phase errors. Chemistry executed 3,307 loader Toffolis per pass at
405 total qubits. Its decoded one- and two-body residuals were both below
0.020 Ha and its gap cleared the strict floor by about 1.7 × 10⁻¹¹ Ha.
Full verification took **32 min 26 s** for the reference and
**19 min 52 s** for the certified project's metric run. The bulk of the
runtime difference came from inverse-square-root verification.
[Audited comparison](evidence/aggregate34-20261126/public-cloud-audit.json)
[Full retry receipts](evidence/aggregate34-20261126/public-cloud/verification/verification.json)

## Remaining cost gap

The reference cost product must fall by more than **6.85%** to clear 34.
If the other two measured reference costs hold, the break-even limits are
**56,752.05** for inverse square root, **285.43B** for DQI or **232.09M**
for chemistry. The 34.5 development target requires a **10.84%** product
reduction. These limits use the measured reference companions and DQI
error count from this run.

The screened rewrites fell short of the qualifying cost. The main unresolved
work is reducing live inverse-square-root arithmetic, shrinking DQI
arithmetic storage and gates, or lowering the complete chemistry cost with
a different loader schedule or fit. The certified goal requires the
same source-built archive to exceed 34 on both the full metric and fresh
confirmation.
[Arithmetic and storage screens](above-34-arithmetic-and-storage-screens-26-11-2026-06-18-11.md)
[Chemistry loader screens](above-34-angle-gauge-and-cloud-retry-26-11-2026-06-02-23.md)

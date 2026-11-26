# Google Cloud reciprocal fixture verification

The existing Google Cloud VM ran the exact three serialized circuits from the local reciprocal research, using the pinned native backend. The transfer manifest covered their KMB hashes and the fixture driver. The cloud seed differed from the local seeds and exercised all 128 addresses with 64 trajectories each. Each circuit restored every live input and cleared its scratch on every trajectory. [Cloud receipt](evidence/aggregate36-20261126/invsqrt-reciprocal-cloud-native.json)

| Circuit | Qubits | Mean Toffoli-like gates | Fine rotations | Cloud phase failures / trajectories |
| --- | ---: | ---: | ---: | ---: |
| Fixed-exponent reciprocal | 49 | 1,740 | 29 | 0 / 8,192 |
| Address-only measurement phase repair with fixture loader | 39 | 1,782 | 0 | 0 / 8,192 |
| Repair with an omitted phase term | 39 | 1,782 | 0 | 251 / 8,192 |

The width and gate counts match the local fixtures. The repair charge is 18 gates after subtracting the 1,764-gate fixture loader. The reciprocal's Toffoli-like contribution alone is 85,260, above the 52,119.68 complete component cutoff with the source-backed companions. The full corrected-numerator phase and the paired score-35 archive remain open. The highest completed cloud portfolio comparison is 33.20483975. [Local measurements and budget](degree35-invsqrt-reciprocal-research-27-11-2026-04-04-28.md) · [Complete portfolio comparison](above-34-cloud-reference-comparison-26-11-2026-06-31-00.md)

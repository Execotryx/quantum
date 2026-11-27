# Affine transport screen of DQI return products

Google Cloud screened all **107,045** unconditional CCXs in the pinned Tony Li decoder return. The original count of **51,524** disjoint pairs allows arbitrary pairing within stretches of unguarded Clifford and CCX operations. The new screen transports the control rows and output directions through X, CX, and SWAP operations in a common affine frame. Measurement, phase, and guards end each stretch. [Initial census and budget](degree35-dqi-return-fusion-research-27-11-2026-05-25-09.md) · [Cloud result](evidence/aggregate36-20261126/dqi-return-fusion-cloud.json)

| Criterion | Static pair ceiling |
| --- | ---: |
| Unrestricted in each stretch | 51,524 |
| Same transported output direction | 135 |
| Same output direction and intersecting control planes | 0 |
| Equal control planes with different output directions | 0 |

Over GF(2), the nonzero forms of a two-dimensional plane are its two generating forms and their XOR. Two product polar matrices can sum to rank at most two in a shared output direction only if these planes intersect. Equal planes also let the same quadratic contribution feed different outputs. The screen counts both cases and allows two-gate cancellation for equal planes with the same output direction. It relaxes dependency order when deriving the upper bounds. The adjacent-pair count was also zero. [Screen source](../tools/dqi_return_fusion_screen.py)

The 135 same-direction ceiling bounds the number of CCXs belonging to repeated-direction groups by **405**. A group of size `n >= 2` contributes `floor(n / 2)` to that ceiling and `n <= 3 * floor(n / 2)`. Even removing every gate in those groups would fall short of the **7,529** mean-gate gap under the assumed companion costs. The screen closes these pair methods and common-direction regrouping within the tested boundaries. Larger changes that alter the cache, cross a measurement boundary with a phase proof, or construct different controls require separate analysis.

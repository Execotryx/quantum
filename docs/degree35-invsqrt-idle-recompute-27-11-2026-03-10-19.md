# Circuit-wide idle-wire recomputation screen

The native `q19` rotation loan shortened one live range. This experiment
looked for other idle wires whose values can be cleared and reconstructed
from live operands. An endpoint must have a symbolic identity consisting
of an affine expression and at most one product of two affine factors.
The circuit reconstructs both factors in place, applies the product,
and restores the factor wires. The selected intervals are disjoint so an
endpoint never relies on another wire that is temporarily absent.
[Implementation](../tools/invsqrt_recompute_idle.py)
· [Rotation loan](degree35-invsqrt-rotation-loan-27-11-2026-02-52-43.md)

The frozen screen inspected **3,306** idle intervals of at least eight
instructions around **4,221** symbolic 39-wire demand sites. It proved an
identity at both endpoints for **322** intervals. Even allowing all
eligible intervals simultaneously covers just **1,065** of those sites.
The best disjoint set under the favorable 32-qubit budget of 46 added
Toffolis selects **33** intervals and covers **727** sites. Coverage counts
the original instructions in those intervals. The allocator and verifier
measure the actual circuit including the added endpoint work.
[Registration](evidence/aggregate36-20261126/invsqrt-idle-recompute-registration.json)
· [Coverage and width receipt](evidence/aggregate36-20261126/invsqrt-idle-recompute-screen.json)

| Matched layout | Qubits | Mean Toffoli-like gates | Cost |
| --- | ---: | ---: | ---: |
| Control | 39 | 1,339.88 | 61,696.25 |
| Idle-wire recomputation | 39 | 1,385.88 | 63,490.33 |

Both circuits passed the pinned verifier on E-backed Ubuntu with one
trajectory per legal input, **3,133,452** each. Both use 33 fine
rotations and report the same worst phase error. The emitter's factor
frames also matched their arithmetic contract in **26,880** exhaustive
small-width cases covering shared factor controls. Pyright and strict
OpenSpec validation passed.
[Control verifier receipt](evidence/aggregate36-20261126/invsqrt-idle-recompute-control-native.json)
· [Recomputation verifier receipt](evidence/aggregate36-20261126/invsqrt-idle-recompute-recompute-native.json)

The emitted schedule costs **2.91%** more, above the complete component
budget of **52,119.68**. The coverage result applies to these single-product
endpoint identities and the registered idle intervals. Further narrowing
needs a change to the carry layout or another source stage that reaches
peak width. The best full cloud comparison is **33.20483975**.

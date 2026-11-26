# Measured return path for the divider checkpoint

The prefix ending at line 5,856 and the cleanup state after line 18,900
have the same quantum register values after `X q28`. A bit-sliced replay
checked all **3,133,452** legal inputs with every measurement forced to
zero and with one seeded random measurement trajectory per input. The
retained return only reads bits `b0`, `b1`, `b2`, `b3`, and `b12` before
local assignment. The discarded region writes none of them.
[Registration](evidence/aggregate36-20261126/invsqrt-checkpoint-return-registration.json)
· [Checkpoint and classical-bit audit](evidence/aggregate36-20261126/invsqrt-checkpoint-return-screen.json)

The emitted test circuit joins the original prefix and suffix with the
single-qubit bridge. It omits the prefix's `Z_POW q33 0.5` at line 177
to calibrate the joined circuit against exactly zero phase (`beta=0`).
The omitted gate is Clifford and affects phase only. The tested return
contains **302 unconditional** and **11 classically guarded** Toffoli-like
instructions. The prefix contributes **320 unconditional** charged gates.
[Source generator](../tools/invsqrt_checkpoint_return.py)

| Native circuit | Target | Width | Executed Toffoli-like gates | Fine rotations |
| --- | --- | ---: | ---: | ---: |
| Pinned incumbent | Inverse square root | 39 | 1,339.87 | 33 |
| Prefix, bridge, and retained return | Zero phase | 39 | 627.25 | 0 |

The pinned verifier on E-backed Ubuntu passed **6,266,904** trajectories
per circuit, covering every input twice. The joined circuit returned
exactly zero tracked phase, restored the input, and cleared scratch.
The return therefore costs **307.25** mean Toffoli-like gates after the
320-gate prefix. The discarded region accounts for **712.62** executed
Toffoli-like gates in the incumbent. At 39 qubits, the complete
inverse-square-root cutoff of **52,119.68** leaves **467.07** charged
equivalents for replacement arithmetic and its cleanup if the incumbent's
**242.08** rotation and T charge is retained. A replacement with a
different margin or rotation count needs fresh pricing. Only the
original circuit supplies inverse-square-root phase in this comparison.
The best complete cloud score is **33.20483975**.
[Incumbent verifier receipt](evidence/aggregate36-20261126/invsqrt-checkpoint-return-control-native.json)
· [Exact zero-phase verifier receipt](evidence/aggregate36-20261126/invsqrt-checkpoint-return-skeleton-native.json)

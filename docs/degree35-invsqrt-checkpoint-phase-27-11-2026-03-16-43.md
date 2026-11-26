# Phase recovery at the inverse-square-root divider checkpoint

Astra proposed replacing the divider tail after line 5,856 of the
Tony Li assembly. The native prefix costs **320 Toffoli-like gates**.
The bit-sliced prefix replay verifies eight clean wires on all
**3,133,452** legal inputs. The value-changing prefix instructions are
independent of measurement outcomes. The current circuit uses another
291 Toffoli-like gates before the first fine rotation. At 39 qubits,
assuming a 320-gate return and the existing rotation charge would leave
**454.32 charged equivalents** for a replacement. The actual return
schedule and its cost remain open.
[Checkpoint screen](evidence/aggregate36-20261126/invsqrt-checkpoint-phase-screen.json)
· [Incumbent stage profile](evidence/aggregate36-20261126/invsqrt-incumbent-phase-window.json)

The proposed table lets each address choose arbitrary affine phase
coefficients on the checkpoint bits. A four-input witness uses one
address and two pairs with the same coordinate-wise sum. Every
address-dependent affine term therefore cancels in the signed sum of
the four phases. Contributions from the prefix and Clifford-only
cleanup can shift that sum by multiples of a quarter turn. The exact
distance of the reference sum from this lattice must be no greater than
the sum of the four verifier tolerances for the model to pass.
[Registered model and sample](evidence/aggregate36-20261126/invsqrt-checkpoint-phase-registration.json)
· [Witness generator](../tools/invsqrt_checkpoint_phase.py)

| Checkpoint address | Distinct sample addresses | Witness error lower bound |
| --- | ---: | ---: |
| `q14` through `q21` | 188 | 82.66 times tolerance |
| `q14` through `q22`, plus `q25` through `q28` | 5,970 | 11.88 times tolerance |
| Same 13-bit address with any joint term on `q7`, `q9`, `q10`, `q12` | 5,970 | 11.85 times tolerance |
| `q12` through `q22`, plus `q25` through `q28` | 19,054 | 0.73 times tolerance |

The four-wire joint term includes the inputs of the next carry cell.
For that witness the two pairs also have the same unordered pair of
values on those four wires. This cancels any function of them, including
the product at line 5,875. The pinned Ubuntu backend reproduced all
listed checkpoint values on two measurement seeds and the official
reference returned the exact targets and tolerances in the witnesses.
Pyright and strict OpenSpec validation passed.
[Native and official-reference cross-check](evidence/aggregate36-20261126/invsqrt-checkpoint-phase-native.json)

The 8-bit and 13-bit addressed families fail even with arbitrary angles
and free lookup. The 15-bit result is inconclusive. Its 19,054 occupied
sample addresses also make an uncompressed unary lookup unsuitable for
the provisional 454-gate budget. A future replacement needs a different
address or a joint function spanning more of the retained remainder and
quotient. Any emitted candidate still needs complete value, phase, and
cost checks. The best complete cloud comparison is **33.20483975**.

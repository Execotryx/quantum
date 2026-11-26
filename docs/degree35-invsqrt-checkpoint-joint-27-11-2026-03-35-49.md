# Three-coefficient phase model for the divider checkpoint

At line 5,856 the retained root is `isqrt(n >> 4)`, where `n` is the
input normalized by a power of four. Its low bit is the complement
of `q22` and its following seven bits are `q15` through `q21` in
ascending order. The leading bit is implicit. The exponent is stored
in `q23`, `q24`, `q34`, and `q35`. The bit-sliced replay checked both
decodes for every one of the **3,133,452** legal inputs. The pinned native
backend reproduced the decoded values under two measurement seeds.
[Registration](evidence/aggregate36-20261126/invsqrt-checkpoint-joint-registration.json)
· [Native checkpoint and official-target check](evidence/aggregate36-20261126/invsqrt-checkpoint-joint-native.json)

The fitted phase uses a root-dependent intercept and two terms. The
first scales one 19-bit word assembled from the checkpoint wires in
low-to-high order `q28`, `q27`, `q26`, `q25`, then `q0` through `q14`.
The word complements `q28` and subtracts one. The second term scales
the square of the high bits of the word on `q2` through `q14`. The
fit uses every distinct normalized input and affine-bit pattern per
root. The final scan uses quantized coefficients and integer rounding
throughout and compares against the exact official phase tolerances.
[Model driver](../tools/invsqrt_checkpoint_joint.py)
· [Frozen three-coefficient table](evidence/aggregate36-20261126/invsqrt-checkpoint-joint-word10-coefficients.json)

| Quadratic model | Bits entering the square | Failed inputs | Worst tolerance use |
| --- | ---: | ---: | ---: |
| Separate affine coefficients on 19 wires | 9 | 0 | 72.67% |
| One weighted word | 9 | 294 | 120.57% |
| One weighted word | **10** | **0** | **85.14%** |
| One weighted word | 11 | 0 | 67.42% |
| One weighted word | 12 | 0 | 61.49% |

The smallest passing one-word lane in this sweep uses **three
coefficients per root** across 256 roots instead of 21. Its 10-bit
model also passed on the native checkpoint bits for 2,816 inputs
per seed, including the full-domain worst case. The independent
integer reference matched the official target and tolerance arrays
on the complete domain. Pyright and strict OpenSpec validation passed.
[Full-domain fixed-point scan](evidence/aggregate36-20261126/invsqrt-checkpoint-joint-screen.json)

The frozen coefficients are stored at 40 fractional bits and occupy
up to 40, 32, and 25 unsigned bits in their respective columns. The
checkpoint has eight clean wires, so loading all three words into
separate live registers exceeds its workspace. The next implementation
stage must price coefficient precision, phasing and cleanup together
under the **467.07**-equivalent arithmetic allowance at the incumbent
rotation price. This evidence covers the fitted numerical phase and
native checkpoint bits. Reversible phase emission and complete circuit
cost remain open. The best complete cloud score is **33.20483975**.
[Measured checkpoint return](degree35-invsqrt-checkpoint-return-27-11-2026-03-24-19.md)

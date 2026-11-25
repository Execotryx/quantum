# D4 affine escape at the captured second-head pole

## Exact local change

Let `h` be the first head of a finite incoming chart and let `q` be
the active irreducible quadratic. If the second head collapses,
`N = hD mod q²`. For nonzero `h`, replace `D` by
`D + (X+t)N`, with `t=0` unless this denominator vanishes at the
active node. In that case use `t=1`. Since `N` is nonzero at the
node, the second denominator is finite. Both choices give an
invertible polynomial shear.

The new first head `h'` satisfies `h + h'(1+(X+t)h) = 0 mod q`.
The polynomial on the left has degree at most three. It is nonzero
because `h` and `1+(X+t)h` are coprime and the latter is
nonconstant. It therefore cannot vanish modulo `q²`, and the new
second-head pivot is finite. The zero-first-head case still uses the
existing collapsed chart.

On any other node the same shear adds `(X+t)N` to the denominator
and `N²` to the Wronskian. The controlled emitter uses a single masked
numerator word for both updates. The normalized local version computes
the escape and translation bits from the live jet. It borrows
the admitted normalization and retains the measurement tokens. In the
inverse, computing the shear denominator on the normalized numerator
produces the reciprocal of the forward denominator. After recovering the
original jet, the forward denominator is recomputed to repay both
measurement phases and clear the two bits.

## Frozen capture and native extraction

The scalar audit ran on twelve captured inputs. Only s2 / 45440
selected the group-6 escape. Its original head was `[3499, 3356]`.
With `t=0` the first and second heads became `[2465, 37]` and
`[3903, 3957]`, respectively. All seventeen incoming and second-head
charts were finite on the resulting trajectory. The final scalar tail
was `([1282], [0])`. Reversing the folds and the shear restored the
exact original numerator and denominator.

The native integration keeps both escape flags through later external
transports and through the trailing scalar jet. Six real syndromes
matched independent head and projective tail values. The full inverse
restored their syndromes, cleared all scratch, and repaid phase at both
seeds. The standalone local test also exercised the `t=1` choice,
a zero first head and an ordinary control. Phase in the normalized
forward snapshot includes outstanding measurement terms, which the
complete inverse repaid.

The integrated extraction and tail probe used 946 declared qubits.
Its two closed means were 218,506.33 and 218,462.33 executed
Toffoli-like gates. The standalone normalized escape used 74 scratch
qubits and averaged 1,441.33 gates for evaluation and inverse. The
ordinary extraction test also computed a termination predicate, so
its observed gate counts are for a different selector.

## Synthesis constraint

The captured input has weight 31. At group 6 the unpadded degrees
change from `(20,19)` to `(20,19)` through the affine pair; the
original collapsed pair would leave `(19,16)`. The affine trace fits
the unpadded regular caps `(22,21)` at that boundary. Padding both
polynomials to weight 35 first would increase the affine continuation
to `(24,23)`, outside those same caps. A successor must either
reconstruct before padding or derive a layout that retains these
coefficients. It must also recover the exact tail without fixture
inputs, restore the denominator shear on the synthesis side, and
price the complete decoder. The current measurements cover the
extraction and tail boundary.

## Degree reduction before the shear

An exact polynomial-division test applied a second variant on the same
capture. At group 6 it used the infinity quotient
`N div D = 1114 + 1167X` to replace the numerator by its remainder
modulo the denominator. This removes its two leading degrees. It
preserves the first collapse while changing the first head to another
nonzero value. The subsequent lower shear restores a finite second
head with continuation degrees `(18,17)`. Adding four to each
nonzero degree fits the nominal `(22,21)` group-6 caps. All finite
groups through group 15 fit their padded caps in the scalar check.
The last group was an incoming, collapsed termination with exact
unit tail up to scale. Both shears and all folds reversed to the
original pair.

This test uses the exact polynomial quotient as input. The live kernel
still needs to obtain that quotient from the circuit's state and
carry it through extraction and synthesis. For an implementation
that verifies the degree reduction, the final zero-head suffix
allows the existing divisibility certificate to select the unit tail.

## Verification

All 36 tests in the staged revision passed locally. Google Cloud ran
the six focused native tests against the hash-verified source bundle.
It reproduced the gate counts and the twelve-input scalar report
byte for byte. The subsequent scalar preshear regression passed
locally. The downloaded cloud receipt archive matched SHA-256
`798c2302643241e01acec4b936529568bcf732d6f4b7b417f20a49945f8daace`.
Compute Engine confirmed the VM was terminated after receipt collection.

[Twelve-input scalar audit](evidence/d4-compact-repair-20261115/affine-s2-final.json)
· [Cloud scalar report](evidence/d4-compact-repair-20261115/cloud-affine-chart/report.json)
· [Cloud native test log](evidence/d4-compact-repair-20261115/cloud-affine-chart/run.log)
· [Staged source and launcher hashes](evidence/d4-compact-repair-20261115/cloud-affine-chart/stage.sha256)
· [VM stop receipt](evidence/d4-compact-repair-20261115/cloud-affine-chart/vm-stop.json)

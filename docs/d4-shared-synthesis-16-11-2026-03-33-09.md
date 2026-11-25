# Shared D4 synthesis and degree padding

One native emitter now handles the captured second-head and
first-head poles in the same circuit. It uses two numerator
slots and one denominator slot for the tail, then grows both
banks by two words at each reversed doubled-node pair. Chart
bits come from live extraction. A collapse needs its highest
incoming V word to be zero. An incoming swap needs the excess
output numerator word to be zero. The compact folds count both
violations as well as any clipped zero pivots. All counts
reverse from the same registers.

The tail uses the constant coordinates obtained by replaying
the extraction at zero. If the denominator is nonzero, its
assumed constant value divides the Wronskian to get the numerator
slope. A zero denominator requires a nonzero numerator and zero
Wronskian. The reconstructed pair then agrees with the original
projective jet modulo X². The external-node transfers give modular
agreement at all doubled quadratics. The final degree check
computes the coefficient of X³⁵ in q₀E + h₀D. If it vanishes and
all guard counts are zero, the reconstructed numerator and
locator have degree at most 34. Their cross product with the
original pair has degree at most 69, below the degree-70 joint
modulus.

The projected pair is padded in place by public monic factors of
degrees 8, 4, 2, and 1, in descending order. A factor is applied
only when the locator's top slots leave that much room. The first
three factors are products of distinct irreducible quadratics.
The last factor X adds only a zero root, outside the scan. The
common factor cancels between the evaluator and locator derivative
at each original nonzero root. The padded pair is scaled to monic
and handed to one degree-35 converter. The residual phase is
disabled for a rejected layout, invalid tail or locator that cannot
reach the target degree. The converter, normalization, padding,
guards, synthesis and extraction reverse on the same physical banks.

## Resource screen

The native regression compared the projected coefficients with the
exact classical pair on all 12 frozen failure and control rows from
the original and residual capture directories. The linked circuit
matched the full expected phase with the frozen masks at seed 761
and fresh masks at seed 762. It restored every syndrome, mask and
scratch wire, including the zero-syndrome control. The captured
weights were 26 through 34.

A separate native padding check compared all 36 possible starting
degrees with exact field polynomials and verified a clean round
trip. Degrees 20 through 35 reached 35, with degree 35 unchanged.
Lower degrees restored correctly and lacked the final nonzero
leading coefficient needed to enable the scan.

| Padding schedule | Qubits | Largest measured mean Toffoli-like gates |
| --- | ---: | ---: |
| Five individual quadratic factors and X | 972 | 493,671.00 |
| Three grouped quadratic factors and X | 970 | 486,989.54 |

Grouping public factors reduces the number of controlled rotations
and masks. It saves about 6,681 gates per shot and two qubits on
this test. The optimized route still exceeds the 970-qubit budget
of 368,417.66 gates by approximately 118,572 gates per shot, before
adding a fallback. Width reduction alone would require at most
843 qubits at the measured gate count, leaving three qubits beyond
the 840 syndrome wires.

The native static profile reaches 920 qubits in extraction, 924 at
the coefficient certificate, 935 after padding, and 970 before
the scan. Forward extraction emits 67,277 Toffoli-like gates and
its inverse emits 134,047. Forward padding emits 5,764 and the
guarded scan emits 48,300. The closed circuit emits 495,188
static Toffoli-like gates.

The shelf has no slot for an unpadded degree-35 locator. Other
tail shapes, layout overflow and insufficient padding also require
a fallback. This is a shared captured-input repair and its resource
screen. It has no complete matched-batch or pooled pricing receipt.

## Cloud verification

Google Cloud passed all four selected tests in 108.26 seconds.
The shared emitter reproduced the local coefficient, phase and
restoration results and the same gate counts at each seed. The
retrieved receipt archive matched the cloud SHA-256. Compute Engine
confirmed the VM was terminated after collection.

[Cloud log](evidence/d4-compact-repair-20261115/cloud-shared-synthesis/run.log) ·
[Staged inputs](evidence/d4-compact-repair-20261115/cloud-shared-synthesis/stage.sha256) ·
[Receipt archive hash](evidence/d4-compact-repair-20261115/cloud-shared-synthesis/receipt-archive.sha256) ·
[VM stop receipt](evidence/d4-compact-repair-20261115/cloud-shared-synthesis/vm-stop.json)

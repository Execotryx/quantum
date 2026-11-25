# D4 live unit-tail preshear recovery

## Unit-tail certificate

The captured s2 input has finite incoming charts, one intermediate
collapse at group 6, and a final collapse. The unaltered compact
extractor gives a nonzero numerator value, zero denominator value,
and zero Wronskian at the trailing scalar node.

Let `M` map the raw tail to the original pair. Its determinant is
the product of the 17 squared node quadratics. A regular inverse
factor carries a row `(A,B)` to `(qA+h1(B+h0A), q(B+h0A))`.
The collapsed inverse carries its A column to `B+h0A`, because
the two terms `qA` cancel, and its B column to
`q(B+(h0+q)A)`. After the first regular factor the numerator
row caps are `(2,3)` and the denominator row caps are `(1,2)`.
Ordinary factors advance both caps by two. An intermediate
collapse and the next regular fold advance both by five, one
more than ordinary. The final collapse saves one on the A
column. If the two collapses are adjacent, the two factors
instead advance the A cap by four. Thus the unit-tail candidate
has root degrees at most `(34,33)` in this family.

The scalar jet makes the cross product of the live tail and
`(1,0)` divisible by `X²`. Applying `M` multiplies this cross
product by its determinant. The resulting root cross product is
divisible by a degree-70 polynomial and has degree at most 69.
It vanishes, so the unit-tail reconstruction has the original
rational function. Since the determinant is nonzero, the tail
cross product also vanishes and the exact tail has `V=0`.
The original primitive pair equals U times the first column
of M, so U is a nonzero constant. This proves the unit tail up
to scale on the detected chart and jet. Other charts need their
own tail recovery.

## Two leading quotient coefficients

The last collapsed inverse maps the unit tail to `(h,1)`. The
kernel reverses the intervening regular folds while retaining four
leading coefficients of each polynomial. The higher coefficients
under polynomial multiplication depend only on these bands. It
reuses the same interpolation-based head products as pooled replay.

At the selected collapsed fold, `D=U+qV` and `N=hD+q²V`.
Check that U reaches its leading degree and that V's first two
band words vanish. Then qV changes only the second leading word
of D, and the top two coefficients of q²V come directly from V.
The resulting degree-one division computes both coefficients of
`N div D`. Initial tests exposed the lower-word mismatch when
the qV contribution was omitted, and the correction is included
in the native implementation.

The two zero V slots are reused for the quotient intermediates.
They can contain arbitrary values on off-chart branches. There
the output is disabled and the slots are restored by multiplying
again before any zero predicate is erased. Forward and inverse
both preserve all live heads, flags, and tail words.

## Native result and resource implication

The six-input test feeds the original syndromes into native
extraction, computes the tail jet, and evaluates the quotient
without supplied coefficients. The guard selects only the exact
s2 capture and emits `1114 + 1167X`. The other five cases leave
the outputs zero. The test uses the selected quotient in a phase
fingerprint, clears it, reverses extraction, restores the
syndrome, and checks all scratch at both simulator seeds.

The complete extraction and quotient probe used 1,043 declared
qubits and averaged 231,292.67 and 231,293.67 executed gates
per shot across the two seeds. The banked price allows about
318,651 gates per shot at that width. The remainder of about
87,357 gates must cover synthesis, conversion and scan.
Re-extracting the whole suffix with the preshear would add
further work. The result establishes a coherent quotient and
a unit-tail certificate for this chart family. It does not
qualify the existing stage composition. A subsequent synthesis
design can use the certificate directly, without first
replaying the full affine extraction, if it preserves the
unpadded degree and register layout through the collapsed fold.

With a unit tail, the last inverse pair is just `(h,1)`. The
regular prefix of the inverse then needs one more U slot than V.
At the captured middle collapse, the two top V coefficients vanish.
The usual two finite absorbers with a substituted second head of
one give `D=U+qV` and a numerator off by `qD`. The top D slot is
zero in this chart, so removing `qD` fits the one-slot difference
between the output banks. This is the layout to verify in the
next native synthesis probe.

## Verification

All 38 local tests passed. The eight focused Google Cloud tests
passed and reproduced the local width and gate counts. The
downloaded cloud receipt archive matched SHA-256
`43cdd99714f90851350aacecb231f008c9240e115cf57b4c9f3c52ca6b9e1850`.
Compute Engine confirmed the VM was terminated after receipt collection.

[Cloud test log](evidence/d4-compact-repair-20261115/cloud-unit-tail-preshear/run.log)
· [Staged source and launcher hashes](evidence/d4-compact-repair-20261115/cloud-unit-tail-preshear/stage.sha256)
· [VM stop receipt](evidence/d4-compact-repair-20261115/cloud-unit-tail-preshear/vm-stop.json)

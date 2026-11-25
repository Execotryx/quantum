# D4 tail for separated outer poles

The guarded route handles collapses at groups 0 and 2, a
regular group 1, and a regular suffix. It recovers the
degree-(4,3) tail from live heads and the scalar jet. This
chart includes the previously rejected separated weight-35
witness.

## Prefix series

The forward divisions leave U of degree at most 32 and V
of degree at most 29 after the three-pair prefix. Write
z=1/X. Let Qᵢ=1+z+kᵢz² be the reversed node quadratics
and Hᵢ=sᵢ+cᵢz the reversed heads. Put P=H₃H₄+Q₁ and
K=s₀+(c₀+s₀²)z. The root degree caps give the triangular
condition

```text
F·Ũ + G·Ṽ = 0 mod z⁴
F = P + z² K Q₁ H₄
G = Q₂² H₃ + z Q₂ P + z² K Q₁ Q₂ (Q₂ + z H₄)
```

Here Ũ and Ṽ reverse the polynomials from degrees 32
and 29. The first two high coefficients cancel in the
denominator of the first collapse. The next two cancel
in the root numerator. The divisor G has constant s₃,
so the circuit checks that head slope before using the
series. It builds six descending slots per bank with
origins 32 and 31, leaving two zero slots before Ṽ.
One direction consists of Ũ=1 and Ṽ=F/G mod z⁴.
The next three directions are its shifts. The last two
independent U slots carry no V coefficients in this band.

## Tail solve

The 28 regular suffix heads send these origins to 4 and 3.
The two independent low directions can affect only the
constant and negative-degree positions. With a=u[0],
b=v[0], and Δ=b·u[1]+a·v[1], the cross combination
b·U[4]+a·V[4] eliminates the first of those directions.
At the next slot, b·U[5]+a·V[5] eliminates the second.
Use the v row as the remaining pivot when b is nonzero
and the u row when b is zero. Its leading coefficient
is p. If L selects that row, the four coefficients at
each weight j are

```text
b·u[4-j]+a·v[4-j]
p·(b·u[5-j]+a·v[5-j])+Δ·L(u[4-j],v[4-j])
v[3-j]
d₀·u[3-j]+n₀·v[2-j]
```

The right-hand sides are b·n₀, Δ·L(n₀,0), d₀ and W.
The second row also imposes the absent negative-degree
coefficients. The augmented solve uses live pivot swaps,
checks for missing pivots, and restores every row and
work register after use. On the inverse it applies the
same coefficient products to the retained tail masks.

The linked emitter trims the wider banks only after
checking the excess high words. The ordinary root degree,
layout, and rejection conditions remain in force.

## Linked verification and price screen

The linked native tests recovered both projected coefficient
banks up to a common scale and applied the correct phase on
three weight-35 separated-pole inputs at two simulator seeds.
One is the archived witness and the other two use different
prefix heads. The denser three-pole witness set the explicit
rejection wire. The zero syndrome stayed clean. Work registers
were restored on both accepted and rejected inputs.

The existing regular and adjacent-pole paths reproduced their
earlier widths and executed means. A separate native test used
an invertible augmented matrix requiring row swaps and a
singular matrix, and verified exact solution selection, cleanup
and phase repayment.

The linked separated path uses 1,503 declared qubits and averaged
560,781.40 and 561,014.80 gates at seeds 761 and 762. The native
builder counted 1,503 peak live qubits and 570,240 static
Toffoli-like gates. The ceiling at minimum pooled repetition is
153,449.66 gates per shot. The largest mean exceeds it by
407,565.14 gates.
Banked D4 remains selected. This route covers the guarded
outer (0,2) pattern with nonzero intervening second-head slope.
The denser and other unsupported charts still need exact
decoding, and the lane did not qualify for full pricing.

## Zero-slope scalar check

Three additional valid weight-35 inputs had intervening second
heads 1, 38 and 220, all with zero slope. The same separated
pole pattern occurred on each. For this case G has zero constant
and F has constant one. A scalar audit used Ũ=G/F and replayed
the independent U direction separately for the auxiliary
eliminations. It recovered exact tails with lengths (3,2),
(4,3), and (4,3), respectively. The native lane still rejects
the zero-slope chart.

## Cloud reproduction

The staged source and launcher matched their pinned hashes on Google
Cloud. All four targeted native tests passed in 567.65 seconds. The
widths and executed means matched the local regular, adjacent and
separated lanes at both seeds. The receipt archive matched the VM
checksum `56ae9b707c72fe27624b3a034d7675bbe9bed0d0ed82985daee7830f16682a00`.
Compute Engine confirmed the VM was terminated after receipt collection.

[Run log](evidence/d4-compact-repair-20261115/cloud-separated-mixed-tail/run.log) ·
[Input hashes](evidence/d4-compact-repair-20261115/cloud-separated-mixed-tail/stage.sha256) ·
[Receipt archive hash](evidence/d4-compact-repair-20261115/cloud-separated-mixed-tail/receipt-archive.sha256) ·
[VM stop receipt](evidence/d4-compact-repair-20261115/cloud-separated-mixed-tail/vm-stop.json)

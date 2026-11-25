# D4 tail for adjacent outer collapses

The new lane tests a mixed chart with genuine poles at groups
0 and 1 and a regular suffix. It recovers a degree-(3,2) tail
from the live extracted heads and scalar jet. The previous
shared lane rejected this tail.

## Prefix constraints

Let U,V be the continuation after the first two collapsed
pairs and q₀,q₁ their node quadratics. Let h₀ and h₂ be their
first heads. Their exact inverse is

```text
D = (h₂+q₀)·U + q₁·(h₂+q₀+q₁)·V
N = h₀·D + q₀²·(U+q₁·V)
```

Forward division bounds U by degree 33 and V by degree 31.
With h₀ = c+sX, the numerator cap gives

```text
V₃₂ = 0
U₃₃ = V₃₁
U₃₂ = V₃₀ + (1+s)·V₃₁
U₃₁ = V₂₉ + (1+s)·V₃₀ + (q₁(0)+c+s²)·V₃₁
```

The V₃₁ direction starts at U=(1,1+s,q₁(0)+c+s²,0)
and V=(0,1,0,0) in descending degree. The V₃₀ and
V₂₉ directions are its shifts modulo the independent U₃₀
direction. Each regular transfer acts triangularly on these
bands, so shifting commutes with replay. Thirty regular
heads reduce the origins to degrees 3 and 2, and U₃₀ can
affect only n₀ and the formal V coefficient at degree -1.

## Reduced solve

After replay, write the primary bands as u,v with leading
coordinates a=u[0], b=v[0]. The combination b·n₀+a·V[-1]
eliminates the independent U₃₀ direction, whose contributions
to those positions have coefficients a,b. The degree -1
coefficient of the polynomial V must be zero. The three
remaining weights at indices j=0,1,2 have equations

```text
b*u[3-j] + a*v[3-j]     right-hand side b*n₀
v[2-j]                   right-hand side d₀
d₀*u[2-j] + n₀*v[1-j]   right-hand side W
```

Negative indices denote zeros. The third row binds the
observed Wronskian. The five nonconstant tail coefficients
follow from the three weighted shifts. The emitter checks
the live chart and rank before using these coefficients,
then reverses the solve and band replay. After unsynthesis it
pays the same products into the measured tail masks.

The linked route reuses the in-place synthesis and projected
phase stages. It checks both excess high words before trimming
to 35 evaluator and 36 locator slots. The root degree and
layout checks and the explicit rejection output still apply.

## Linked verification

The native test recovers both projected coefficient banks up to
scale and the correct full phase on three independent weight-35
inputs with adjacent outer collapses. It uses the original
witness and two independently generated supports. The same
circuit explicitly rejects the weight-35 separated-collapse
witness and gives it the projection phase. The zero syndrome
stays clean. Every input, mask, and work wire restores at both
simulator seeds, including after tail phase repayment.

The ordinary shared lane reproduced its earlier 1,011-qubit
results on the frozen and regular full-weight controls. The
new lane uses 1,240 declared qubits with executed means of
540,341.60 and 540,441.00 at seeds 761 and 762. The native
builder counted 1,240 peak live qubits and 549,478 static
Toffoli-like gates. The price ceiling at minimum pooled
repetition is 225,444.96 gates per shot. The larger measured
mean is 314,996.04 gates above that ceiling. Its coverage
is specific to this adjacent-collapse chart. The separated
and denser charts still need an exact route. Banked D4 remains
the selected component.

## Cloud verification

Google Cloud passed both selected tests in 365.33 seconds.
The mixed and regular probes reproduced the local widths and
executed means at both seeds. The VM's configured three-hour
runtime limit stopped it after the test had finished and before
receipt retrieval. Collection therefore used a brief restart
of the existing VM with its completed stage intact.
The retrieved archive matched the SHA-256 recorded at the
end of the original run, and Compute Engine confirmed termination
after collection.

[Cloud log](evidence/d4-compact-repair-20261115/cloud-adjacent-mixed-tail/run.log) ·
[Staged inputs](evidence/d4-compact-repair-20261115/cloud-adjacent-mixed-tail/stage.sha256) ·
[Receipt archive hash](evidence/d4-compact-repair-20261115/cloud-adjacent-mixed-tail/receipt-archive.sha256) ·
[VM stop receipt](evidence/d4-compact-repair-20261115/cloud-adjacent-mixed-tail/vm-stop.json)

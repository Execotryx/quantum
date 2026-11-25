# Regular full-weight D4 tail and synthesis

The shared emitter previously allocated a two-word numerator and
one-word denominator for the tail. It could only reconstruct locators
through degree 34. The extended emitter uses degrees (2,1) at the
tail and grows both banks by two at each inverse pair. The projected
evaluator and locator have 35 and 36 slots. A degree-35 locator now
enters the existing monic conversion without padding.

## Tail equations

On an all-regular extraction, the two upper numerator coefficients
of the reconstructed root pair must vanish. Let t and s be the root
denominator coefficients of degrees 35 and 34. Replay the root band
(N₃₆,N₃₅,D₃₅,D₃₄) = (0,0,1,0) through the 34 regular head transfers.
Write its resulting tail band (n₂,n₁,d₁,d₀) as (a,c,b,d).
The companion root direction (0,0,0,1) maps to (0,a,0,b).
The upper-band map equals the diagonal low-band map at every
transfer, so the second column follows from the first.

The denominator constant observed at the scalar node is d₀. Its
Wronskian W equals d₀·n₁ + n₀·d₁. Substitute
n₂ = a·t, n₁ = c·t + a·s, d₁ = b·t, and d₀ = d·t + b·s.
The equations for (t,s) have rows (d,b) and
(d₀·c+n₀·b, d₀·a), with right-hand side (d₀,W).
Cramer's rule computes the three tail coefficients without
forming separate four-word columns for all three unknowns.
Each intermediate is reversed before the corresponding scratch is freed.

The reduced implementation carries (a,b,Δ) with Δ = a·d + b·c.
For a head h = L + H·X, the top pair becomes (b,a+H·b) and
Δ changes by a·b+(L+H)·b². This follows by substituting the
two-band transfer into the determinant. It removes the need to
materialize c and d. Eliminating s yields

```text
det = d₀·Δ + n₀·b²
t   = (d₀²·a + b·W) / det
n₁  = (W·Δ + n₀·b·d₀·a) / det
n₂  = a·t
d₁  = b·t
```

These expressions also work when d₀ is zero and the determinant
is nonzero. A native regression uses the same jet on a regular
chart and a forced mixed chart. It checks the exact solution for
the regular case and a single invalid-jet count for the mixed
linear fallback. Both cases reverse and repay the selected phase.

The circuit uses this result only if every chart is regular and the
determinant is nonzero. Otherwise it emits the prior linear seed
and counts an invalid zero-denominator jet. The polynomial certificate
checks both extra root numerator coefficients, N₃₅ and N₃₆, and
the live pivot and layout counts. The tail matches the scalar jet,
so the cross product is divisible by the degree-70 joint modulus.
The verified root degree caps force that cross product to vanish.

An independent scalar check recovered the exact coefficients on
48 nonsingular deterministic weight-35 inputs. All 17 singular
weight-34 inputs had the expected linear seed. The native linked
test adds three regular weight-35 inputs to the 12 frozen rows,
with an incompatible mixed full-weight tail and zero syndrome as
restoration controls.

## Linked resource screen

The linked native test reconstructed the projected pair up to
scale for all 15 accepted rows, including the three unpadded
degree-35 inputs. It matched phase with frozen and alternate
masks and restored the syndrome, masks and every work wire.
The incompatible mixed degree-35 control was rejected at
the coefficient certificate and received only the projection
phase. The zero input also restored cleanly.

| Tail replay | Qubits | Largest executed mean gates per shot |
| --- | ---: | ---: |
| Four-word band and two-by-two solve | 1,063 | 491,869.76 |
| Three-word band with determinant recurrence | 1,039 | 491,617.76 |

The reduced variant removes two words at the solver peak and
252 gates from the observed mean on the same test cases. The
native static profile first reaches the 1,039-qubit declared
width in the forward tail solver. Each tail invocation emits
9,985 static Toffoli-like gates and the closed circuit emits
499,826. The reference budget at 1,039 qubits and minimum repetition is
321,109.25 gates per shot. The reduced route exceeds it by
170,508.52 gates. The extended circuit is still a development
probe. A mixed full-weight tail can require degrees (3,2) or
larger, and the linked emitter still needs an exact residual
route or verifier-visible failure for rejected inputs. Full
matched-batch acceptance and official pooled pricing remain open.

## Cloud verification

The four-word baseline passed its three selected native tests
in 198.20 seconds on the existing VM. Its width and gates
matched the local measurements at both seeds. The downloaded
receipt archive matched the VM's SHA-256.

[Baseline cloud log](evidence/d4-compact-repair-20261115/cloud-regular-full-weight/run.log) ·
[Staged inputs](evidence/d4-compact-repair-20261115/cloud-regular-full-weight/stage.sha256) ·
[Receipt archive hash](evidence/d4-compact-repair-20261115/cloud-regular-full-weight/receipt-archive.sha256)

The reduced solver passed four selected tests in 193.83 seconds.
This included the zero-denominator and mismatched-chart controls.
The VM reproduced the linked width and per-seed gate counts, and
the downloaded receipt archive passed the SHA-256 comparison.
Compute Engine confirmed that the VM was terminated afterward.

[Reduced solver cloud log](evidence/d4-compact-repair-20261115/cloud-regular-tail-determinant/run.log) ·
[Staged inputs](evidence/d4-compact-repair-20261115/cloud-regular-tail-determinant/stage.sha256) ·
[Receipt archive hash](evidence/d4-compact-repair-20261115/cloud-regular-tail-determinant/receipt-archive.sha256) ·
[VM stop receipt](evidence/d4-compact-repair-20261115/cloud-regular-tail-determinant/vm-stop.json)

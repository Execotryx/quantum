# Adaptive64 changes classical phase weights, not the admitted decoder domain

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

Public v6 uses internal `integration_v7`. All extractor, carry-chart, Euclidean,
preimage, infinity-three finish and ten-helper point-cell arithmetic remains the
accepted public-v5 composition. The only changed whole-decoder operations are
the purely classical weight transport, its original-syndrome Z compensation,
and the extra scan at the released public point 70.

Let g(x)=x times the product of (x+r) for r=1,...,69. After the old seventy-point
gauge is open, normalize each of the 4,025 remaining trace-dual masks by g(a).
Choose a label among 0,...,63 using only those classical masks: saturate each
count at seven, give zero the virtual-pivot count one, and retain the smallest
label on a tie. No syndrome, error support, degree, chart, exclusion flag or
quantum data participates in this choice.

The original selected interpolation masks stay intact. The selected label has
its own twelve-bit classical word. Shift each normalized residual mask by that
label, and scan point 70 with the separate word. Scale each point mask by
`g(a)/(a*U(a)*M(a))`, using the same live Finish provider and modulus M as the
accepted pipeline. Points 1,...,69 remain omitted, where g vanishes. All point
operations use the unchanged ten-helper ladder and restore their logical masks.

For every physical vector, S_j=sum_a e_a a^j. The added scan phase therefore
agrees with the separately emitted original-syndrome compensation
Tr(lambda * sum_{j=1}^{70} g_j S_j), where lambda is the trace-dual interpretation
of the selected label. Applying both phases cancels the gauge change. This
identity holds pointwise for every selected classical label, including a
nonlinear function of the masks. It does not require an independence assumption
between the selected label and shifted residual masks.

Closing inverts every shift and normalization, clears/frees the separately
owned pivot label and closes the unchanged original gauge. No compensation is
applied twice. The explicit Record is checked against the builder and original
mask words, consumed by exactly one full scan and closed exactly once.

The selector and compensation add zero T and zero qubits. The released pivot
adds eleven static T, but executed scan T is eleven times the number of nonzero
chosen masks. The zero-first capped selector never decreases the actual number
of zeros relative to keeping label zero: choosing a nonzero saturated winner
requires its true count to exceed the old zero count including the virtual
pivot. Hence executed scan T never increases on any classical mask input.

The exact model replaces the independent-cell scan discount with the stored
capped64 finite-occupancy expectation. Fresh HMR discounts elsewhere remain
unchanged. Neither that expectation nor finite native tests is an official
measured mean. New canonical bytes require four fresh original verifier salts,
each priced using its actual integer error count and failure factor.

The admitted event is unchanged: cutoff15, the existing unit and half-core
conditions and already declared gap exclusions. No new exception, low-weight
rule, support restriction or denominator condition is introduced. The accepted
500-million-draw certificate is evidence about that same declared event only,
under its existing source-transfer, ideal-IID/fixed-PRNG and numerical-ABI
qualifications. Both historical provenance exceptions stay disclosed. A final
release must preserve those source bindings and separately pass every required
current native, phase, restoration and official test.

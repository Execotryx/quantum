# Compact D4 local-pole fold

The [isolated absorber](../src/qcompile/vendored/dqi_d4_compact.py)
reuses the first and second head registers and the continuation denominator
for the reconstructed numerator. The continuation numerator becomes the
reconstructed denominator by alias. The primitive requires a nonzero
continuation numerator modulo the quadratic and a known-zero second head.

For q = X² + X + kappa, emit the contribution of h*U in coordinates
r0 + q*r1 + q²*C, where r0 and r1 each have two coefficients. Accumulate
r1 and C into the zero second head and continuation denominator. Replace
h with r0 by multiplying in the quotient field by U mod q. Two triangular
linear maps expand the coordinates into ordinary coefficients. The inverse
undoes those maps, restores h using the live quotient factor and erases
the added terms. The phase corrections use the same factor in its original
or reciprocal form, matching the measured operand.

The first implementation used low monomial coefficients of the remainder
modulo q² where it needed r0 modulo q. Both native coordinate tests detected
the value mismatch. After the coordinate correction, both tests passed.
They cover 64 inputs at each of two D4 coordinates and two simulator
seeds, with exact output words, complete inversion, phase fingerprints
and clean scratch. Pyright and Ruff passed.

The native resource profile at coordinate 12 used 66 additional declared
qubits for each of three input layouts. The closed fold used 1,752 static
Toffoli-like gates for 6 and 4 continuation words, 4,104 for 20 and 17, and
6,792 for 36 and 33. These are standalone counts including the inverse.
An integrated budget must include control and live registers at each fold.
[Resource profile](evidence/d4-compact-repair-20261115/local-pole-fold-resources.json)

This primitive covers a supplied genuine-pole chart. The common layout
for coherent regular, pole and terminating branches, the mixed-chart
tail and the streamed converter transition remain to be verified.

[Control manifest](evidence/d4-compact-repair-20261115/controls.json)
· [OpenSpec design](../openspec/changes/optimize-d4-pole-safe-decoder/design.md)

# D4 pooled aligned replay

## Shared spill storage and cheaper shears

One row now traverses all 17 folds using the same spill bank. Each shift
rotates the affected coefficient band together with the spill bank.
Displaced coefficients enter at its front. The output bands receive zero
at their high end as long as enough trailing slots are unused. Reverse
rotations restore every displaced word in the opposite order. The first
chart initializes the same representation and has no incoming or previous
collapse flag.

The overflow predicate reads the flags. The first shift is one plus the
first collapse bit. At later folds, with previous and current collapse
bits `p,c` and incoming flag `i`, the shift count is
`(p XOR c) + 2i + 2ipc`. The counter adds these to one less than the
negative capacity, copies the nonnegative comparison and erases itself.
Every shift is reversible even when the guard reports overflow. In that
case old spill data can reach a band, so the band is ineligible for use.

The first reversed head is a polynomial of degree at most two. The
circuit conditionally shifts the two stored head words and adds the
collapsed quadratic to the three coefficients. The second head adds
the collapsed unit term. Both shears reuse the admitted interpolation
and rank-affine kernels. The kernels XOR only the requested low
coefficients of the head product and restore the head and source.
With width `w`, the two shears make at most `w+2` and `w+1`
field products. The previous schoolbook shears each used `2w-1`.

## How spill capacity bounds the band precision

Let `s` be the total number of displaced words. The two degree origins
start at zero and grow by four plus the number of displaced words at
each fold. Adding the numerator's degree shift of one makes the two
column bounds sum to `70+s`. The determinant has degree 68 before that
shift and degree 69 after it. Hence the total gap from the column bounds
to a basis with distinct leading rows is `s+1`.

After scaling columns to their bounds at infinity, the determinant's
first nonzero term has order `s+1`. Each cancellation or removal of
a leading zero lowers the sum of the bounds. A pivot step combines
normalized columns by a scalar when canceling at a matched leading
degree. It consumes precision only as the bounds decrease. Keeping
`s+2` terms therefore leaves enough precision to detect both leading
rows and finish the reduction. One extra initial zero aligns the
denominator row with the numerator's shift. The prior scalar audits
agreed with this bound on all 53 cases in each witness set. The native
probe reserves eleven words per band and nine spill words.

## Measured resource gate

The single-factor tests exercised all eight flag combinations with
nonempty prior spill data. The five-word factor averaged 1,079.50 and
1,079.63 executed gates at two seeds, down from 1,409.48 at the previous
boundary. The ten-word factor averaged 1,811.50 and 1,811.63. Both
used 17 scratch qubits besides the supplied words.

The full live replay checked both rows separately on eleven inputs.
It reproduced the expected bands and spills on all nine inputs that
fit the pool, including the four-separated-pole witness. The live
predicate detected both overflows. Phase was applied only to eligible
outputs. Every input restored the heads and chart flags and cleared
both bands, the spill bank and the overflow flag on inverse.

The probe used 1,239 declared qubits and at most 72,786.55 executed
gates per row for the full query and erase with the overflow check.
The two row receipts sum to 145,573.09 gates. At 1,239 qubits the
banked price allows about 225,809 gates per shot. That would leave
about 80,236 gates for everything else. The already measured
extraction alone averaged more than 215,000 gates on its validation
set. The pooled replay therefore does not support integrating the
existing stages into a budget-qualified candidate. The measurements
are stage probes on different input sets.

The overflow flag also leaves a correctness requirement. The caller
needs a certified unit tail or an exact alternative when the spill
pool overflows. Both row results in this probe are consumed separately.
Coherent pivot selection, normalization, and the converter handoff
still require a smaller circuit.

## Numerator-only reduction

The numerator equations and tail jet appeared to determine the same
solution space as both rows on the earlier fixtures. An exact weight-35
construction exposed an ambiguity. It has three initial collapsed
charts and two regular charts with prescribed heads. On seven
admissible tail coefficients, the numerator degree equations plus the
jet have rank six. Adding the denominator degree equations raises the
rank to seven. The scalar regression constructs the alternative tail,
preserves its two values and projective derivative at zero, and
reconstructs a numerator within the degree limit and a denominator
above it. This rules out replacing the two-row solve by a numerator-only
solve on all legal inputs.

## Verification

All 30 tests in the staged revision passed locally. The four focused
cloud tests passed with exactly the local resource measurements. The
separate local numerator-only counterexample regression passed after
the cloud source was frozen. The downloaded cloud archive matched
SHA-256 `996d7486f6a927b21cf51479a55b13bde6ccb129c39683203512331a60a82fd1`.
Compute Engine confirmed the VM was terminated after receipt collection.

[Cloud test log](evidence/d4-compact-repair-20261115/cloud-pooled-replay/run.log)
· [Staged source and launcher hashes](evidence/d4-compact-repair-20261115/cloud-pooled-replay/stage.sha256)
· [VM stop receipt](evidence/d4-compact-repair-20261115/cloud-pooled-replay/vm-stop.json)
· [Numerator-only witness](evidence/d4-compact-repair-20261115/single-row-counterexample.json)

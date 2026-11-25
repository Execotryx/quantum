# D4 live chart routing and termination

## Reversible termination predicate

The predicate reads the 68 live head words and the extraction flags.
Starting from the last fold, it computes suffix membership by requiring
an incoming chart, a collapse, a zero first head, and membership of the
next fold. The first fold has no incoming flag and cannot join a suffix.

Let `k` be the suffix length and let `j=17-k`. The denominator bound
at the end of the prefix is `35-2j` plus one or two for each incoming
fold after the first, according to the previous chart gap. A finite
regular fold after a collapse adds one. Subtracting the suffix divisor's
degree `4k` yields `1-2k` plus the prefix adjustments. A signed
seven-bit register covers the entire range from -31 to 33. The predicate
copies the sign to the caller's target and reverses both the sum and the
suffix flags. A negative sign certifies the unit tail up to scale.

The native test covers 544 assignments with all 17 possible suffix
lengths, including comparisons on both sides of the bound at the same
suffix length. It tests XOR into alternating initial bits, uses the
predicate in a phase fingerprint, and checks every input and scratch
wire. The extraction integration test drives it from six actual
syndromes that include terminating and nonterminating cases. It
validates heads, charts, the tail jet and the combined phase fingerprint,
then checks restoration of the syndrome and scratch.
The stand-alone predicate used 46 extra qubits and averaged 2,030.20 and
2,032.59 executed Toffoli-like gates across the two measurement seeds.

## One live aligned factor

The chart step routes equal-width reversed bands using three live bits.
It accepts an incoming swap, the previous collapse, and the current
collapse. If the incoming bit is set, the B shift is two plus the
previous collapse bit plus the current collapse bit. Without the swap,
B shifts once on a transition from regular to collapse. A shifts once
on a finite transition from collapse to regular. The two shifts never
take place together. The current circuit uses separate registers for the
one A and four B displaced words.

The first product uses a single conditional source offset, with the
linear quadratic contribution added on the collapse chart. The second
product uses the initialized zero second head of a collapsed fold and
adds the corresponding unit term. The quadratic update remains
triangular. Controlled rotations follow disjoint cycles, including the
two-word shift. The inverse reverses the operations and clears the
spills. The native test uses all eight live flag combinations across
64 randomized input rows. It checks the full bands and spill contents,
preserved flags and heads, phase, and the cleared workspace.
The five-word factor used 17 extra work qubits besides the supplied
spills and averaged 1,409.48 executed Toffoli-like gates at both seeds.

The test emits one noninitial factor with five words per band. It
allocates its worst-case spill wires locally. Multiplying that
allocation by sixteen would reserve 80 field words just for spills.
A full replay needs shared spill storage or another way to reclaim
these words, a proof of legal capacity, and a coherent handoff of the
two row results to the pivot and normalization circuits.

The direct per-factor spill allocation fails the resource gate at a
ten-word width. The live heads, chart flags, one row's bands and retained
spills alone require 2,049 qubits. At that width the banked cost allows
about 82,566 executed gates per shot. The two head shears in the
sixteen noninitial factors use 102,144 unconditional rank-42 gates to
query and erase both rows. That excludes routing, the first factor,
extraction, the tail solve and the scan.
Even sharing the A spill with one B spill in every factor would
leave a 1,857-qubit floor and a budget of about 100,522 gates.

## Verification

All 27 local pole-transfer tests passed. Google Cloud reran the two
new native tests and the extraction integration test against the
hash-verified source bundle. The three tests passed and the measured
gate counts matched the local run. The downloaded receipt archive
matched SHA-256
`f712fdd3f29fce93545dec92473b4db8d709b791855e00b7d5ac96a210839ea2`.
Compute Engine confirmed the VM was terminated after receipt collection.

[Cloud test log](evidence/d4-compact-repair-20261115/cloud-live-chart/run.log)
· [Staged source and launcher hashes](evidence/d4-compact-repair-20261115/cloud-live-chart/stage.sha256)
· [VM stop receipt](evidence/d4-compact-repair-20261115/cloud-live-chart/vm-stop.json)

# Coherent guard for the padded DQI derivative chart

The projective Euclidean action already retains its divisor heads
in the polynomial banks. A later frame can scale a retained head
by a nonzero factor, which preserves its zero predicate. The guard
tests the heads together at the deepest frame, then erases its
temporary tests. The reverse action visits that frame with the
same predicates and erases the guard bit.

When a divisor head is zero, the guarded action temporarily
extends it to the unit before computing its inverse. The original
head restores at the end of each scale. The resulting extended
action is reversible on these nonregular inputs. The retained guard
suppresses their root phase. A routed decoder still needs to recover
their correct phase.

| Full 4,095-position software replay with orientation | First-fit qubits | Explicit controlled products | Equality calls |
| --- | ---: | ---: | ---: |
| Unguarded | 886 | 192,852 | 8 |
| Guarded | 888 | 196,947 | 338 |

The guarded fixture mixes both orientations, one regular case per
weight, and four genuinely nonregular input syndromes of weights
32–34. A separate classical division checked chart validity. The
packed phase replay checked the live guard decision, the correct
regular phase, zero phase on rejected inputs, exact coefficient
banks, the degree, orientation, masks, and clean scratch. Both
measurement seeds passed.
[Guarded software receipt](evidence/aggregate36-20261126/dqi-padding-guard-software.json)

These are software emitter counts before lowering the equality
gates. The guarded stage leaves at most **83,053 gates** under the
280,000-gate allocation for those comparisons, the locator from
raw syndrome, and recovery. The native WSL run on drive E still
has no receipt. The full decoder has yet to qualify for cloud
verification and the degree-35 submission archive.

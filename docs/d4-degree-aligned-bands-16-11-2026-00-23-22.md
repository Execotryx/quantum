# D4 degree-aligned bands

For one row of the chart matrix, store the top coefficients of each
polynomial in descending order from its degree bound. The incoming
chart can exchange the banks and their bounds. For bounds `a,b` after
the exchange, set `c=max(b,a+deg(H0))` and
`u=max(a+2,c+deg(H1))`. Use degree bounds 1 and 1 for a regular fold
and 2 and 0 for a collapsed fold. The new origins are `u,c+2`.

The first shear shifts the target's old words by `c-b`, then adds the
first head times the source in its output coordinates. The monic
quadratic uses the triangular map `1 + t + kappa*t²` in reverse
coordinates. The second shear shifts its target by `u-a-2`, then
adds the second head product. A second triangular update finishes the
fold. All head product offsets are nonnegative, so omitted coefficients
stay outside the band. For the inverse, undo the triangular updates in
the opposite traversal order. Undo each shear by subtracting its product,
recovering the displaced words, and reclaiming the zero prefix.

Every completed regular fold leaves the degree origins one apart.
A collapsed fold leaves them two apart. With signed incoming gap
`g=b-a`, the total number of displaced words is
`abs(g-1)` for regular and `abs(g-2)` for collapse, capped separately
by the band length for each shear. The native probe assigns its chart
sequence ahead of time, so wire relabeling implements these shifts
without runtime routing. It retains every displaced word.

The scalar audit checked every forward band against full polynomial
arithmetic and restored both initial rows on all 53 inputs. The native
probe ran two rows separately on seven fixed schedules. It checked the
resulting bands, live heads, phase and cleanup at two seeds. The Google
Cloud report was byte-identical to the local report and the targeted
native single-factor test passed. The downloaded receipt archive matched
SHA-256 `0ad1cabd222273cabc5e69c04173057b0eee7ff64ac23355881c654e98e0c425`.
Compute Engine confirmed the VM was terminated after the receipt transfer.

| Fixed schedule | Band words per bank | Retained words per row | Qubits per row | Query and erase gates per row |
|---|---:|---:|---:|---:|
| Regular weight 35 | 2 | 1 | 876 | 8,568 |
| Historical s2 / 45440 | 5 | 4 | 984 | 23,688 |
| Historical s6 / 102316 and s7 / 52983 | 4 | 3 | 948 | 19,992 |
| Three separated poles | 8 | 7 | 1,092 | 38,052 |

Each row's width includes 816 head qubits. A decoder needs both row
results, live chart routing, pivot selection, and storage for the
normalized tail. The two row replays on the three-pole fixture together
use 76,104 executed Toffoli-like gates for query and erase, before
charging any of those operations. The fixture measured eight words per
bank. A production implementation needs a bound over legal nonterminating
charts and a proof for how two live results share workspace.

## Termination without the leading query

An incoming collapsed fold with both first-head words zero divides the
previous denominator by `q²` to obtain the new denominator. For a suffix of `k` such folds, the
distinct node quadratics have product of squares of degree `4k`.
If this exceeds the degree bound on the denominator entering the suffix,
that denominator is the zero polynomial. The final numerator is a nonzero
constant because the primitive root pair is a polynomial-linear image of
the final pair. Thus the unit tail `(1,0)` is admissible up to the
usual monic normalization.

The first incoming flag is false for a primitive pair whose denominator
splits over the base field. For a prefix of `j >= 1` complete folds,
the denominator bound equals `35 - 2j` plus adjustments after
the first fold. Each incoming fold adds the previous gap (1 for regular
and 2 for collapse). A finite regular fold immediately after a collapse
adds 1. The other adjustments are zero. The closed form matched the
separate degree envelope on all 53 inputs.

The shortcut certified 37 inputs. The 16 remaining inputs needed at most
eight words per bank and seven displaced words per row in this audit.
This identifies which large windows can be bypassed and gives a way to
calculate the check from extraction controls. The native probe does not
yet evaluate that check or select charts at runtime.

## Denser pole stress cases

The four-separated-pole witness `1010101` is an exact weight-35 input.
It needs ten words per bank and nine displaced words per row, including
five nonzero displaced coefficients in each row. This rules out using
the three-pole measurement as a universal capacity. Four and eight
consecutive poles each used four words per bank and three displaced
words per row. Pole spacing and chart transitions determine the storage
cost in these witnesses.

The local native check passed on all three new schedules. Each row of the
four-separated-pole circuit used 1,164 qubits and 46,536 executed gates
for query and erase. The four-consecutive and eight-consecutive circuits
both used 948 qubits per row, with 16,800 and 13,776 gates respectively.

[Local measurements and 53-case audit](evidence/d4-compact-repair-20261115/aligned-native-final.json)
· [Cloud report](evidence/d4-compact-repair-20261115/cloud-aligned-band/report.json)
· [VM stop](evidence/d4-compact-repair-20261115/cloud-aligned-band/vm-stop.json)
· [Dense-pole witnesses](evidence/d4-compact-repair-20261115/dense-poles.json)
· [Dense-pole native measurements](evidence/d4-compact-repair-20261115/aligned-dense-native.json)

# Source-level inverse-square-root alternatives

The Academic Research quick brief used inline source verification and local
measurements. Its selected change adapts Litinski's add/subtract construction
to the two rounded, signed products in the existing 192-interval quadratic.
The best serialized arithmetic slice costs **181,472**, down **33.8%**
from **273,980**. The complete inverse-square-root component would need to
cost at most **52,119.68** to reach score 35 with the source-built companions
held fixed. The slice excludes coefficient access, exponent routing, and
rotations. The previous **33.20483975** aggregate remains the highest full
cloud comparison.
[Litinski's construction](https://arxiv.org/abs/2410.00899)
· [Previous native arithmetic comparison](degree35-invsqrt-borrowed-carry-27-11-2026-01-57-09.md)

## Signed rows

For an `n`-bit signed multiplier `s`, replacing each binary digit `b` with
`2*b - 1` and retaining the negative weight of the top bit gives `2*s + 1`.
The emitter shifts the rows one bit further down and subtracts the fixed
half-row to remove the midpoint bias. Each digit selects between adding and
subtracting by conjugating the target of an unconditional adder with CNOTs.
Truncation applies to the unsigned row before the digit supplies its sign.
The guard residue stays live until the inverse. The model keeps the original
coefficient tables and the two distinct rounding orders.

| Roundtrip arithmetic layout | Qubits | Executed Toffolis | Width times gates |
| --- | ---: | ---: | ---: |
| Previous best, source-borrowing carry | 103 | 2,660 | 273,980 |
| Signed digits with native adder | 107 | 1,696 | 181,472 |
| Signed digits with source-borrowing carry | 104 | 1,994 | 207,376 |
| Signed digits with dirty upper increment | 86 | 3,612 | 310,632 |

The one-guard model applies the pinned verifier's targets to all **3,133,452**
inputs and uses at most **80.71%** of tolerance. Using two guards in each
product lowers that to **73.45%**. Each new forward and roundtrip slice passed
**1,536** native trajectories across all 192 addresses, checking operands,
guard residue, scratch, and phase. The 20 existing slice hashes matched.
[Registration](evidence/aggregate36-20261126/invsqrt-signed-digits-registration.json)
· [Full-domain phase model](evidence/aggregate36-20261126/invsqrt-signed-digits-screen.json)
· [Native slice receipts](evidence/aggregate36-20261126/invsqrt-signed-digits-native.json)

## Alternative phase representations

- On the legal octave `[2^20, 2^21)`, a fixed sum of unwrapped input-parity
  rotations needs at least 722 nonconstant Walsh terms by the numerical RMS
  screen. The calculation allows a free constant and globally optimal support
  in the Walsh basis. Giving 700 fine rotations the maximum possible phase
  slack and charging only the 22 input qubits already costs **110,525**.
  The result covers one direct rotation per parity in that representation.
  [Welch et al.](https://arxiv.org/abs/1306.3991)
- Splitting the mantissa into two contiguous parts behind a common prefix and
  phasing their tables additively cancels the four-corner mixed difference.
  The target has a nonzero mixed difference. Among all splits with at most
  16,384 entries, the most favorable witness exceeds the allowed error by
  5.82 times. The smallest rectangular layout surviving this necessary test
  has **32,768** entries. A mixed correction, finer conditioning, or a
  different encoding changes this bound.
  [de Dinechin and Tisserand](https://doi.org/10.1109/TC.2005.54)

[Reproducible additive phase screens](evidence/aggregate36-20261126/invsqrt-additive-phase.json)

## Creative Investigator cross-check

The practical run completed three rounds and 14 searches. It independently
identified the controlled add/subtract construction. Its proposed application
is inside the 39-qubit source control's arithmetic, subject to establishing
that the candidate rows still use conditional addition. The signed-digit
measurement here validates the construction on the rounded quadratic's own
rows. The source control's recovered divider already contains specific carry
and half-cell rewrites, so the arithmetic count alone cannot establish the
savings from replacing its rows. At 39 qubits, saving one third would require
roughly 737 eligible charged gates across the complete forward and inverse
paths. At a fixed 33 rotations, even zero phase error could save only about
22 charged equivalents per input. The verifier prices executed fine rotations
per shot, including conditioned rotations when they run.
[Add/subtract source](https://arxiv.org/html/2410.00899v1)
· [Competition phase and resource contract](../contracts/contract.json)

The native stage profile reproduces the 39-qubit control's exact KMB hash.
On 8,192 matched inputs, the work before the first fine rotation used
**611** mean Toffoli-like gates, the window through the last rotation used
**71**, and cleanup after that window used **657.88**. Replaying the three
fragments in one simulator reproduced the complete circuit's phase, counters,
restored input, and clean scratch. The first two windows total 682 gates,
so a 737-gate opportunity spans work after the last fine rotation as well.
Classify the forward and paired inverse arithmetic rows before substituting
an add/subtract kernel. The window profile alone establishes where to look.
[Matched native control profile](evidence/aggregate36-20261126/invsqrt-incumbent-phase-window.json)

## Where a complete source rewrite can gain

The 39-qubit Tony Li control uses **1,278 unconditional Toffoli-like gates**,
including **149 controlled swaps**. A diagnostic with three measurement
seeds (`1`, `2`, `3`) on 131,072 uniform inputs from seed `20261127`
gave **61.87** mean additional charged gates
under classical guards. The full publisher receipt reports about **1,582**
charged equivalents per input after rotations. A 35-qubit derivative may
spend about **1,489**. Even eliminating all sampled guarded charge at that
width leaves roughly 31 equivalents to remove. At the original 39 qubits,
the remaining gap is about 184. Both figures hold the measured rotation
charge fixed. Prioritize a rewrite of a complete carry or routing block that
shrinks the live width and the unconditional cost together. Re-evaluate the
rotation charge and require whole-circuit restoration and phase before cloud
qualification.
[Rebuildable source control and budget](degree35-invsqrt-source-research-27-11-2026-01-39-29.md)

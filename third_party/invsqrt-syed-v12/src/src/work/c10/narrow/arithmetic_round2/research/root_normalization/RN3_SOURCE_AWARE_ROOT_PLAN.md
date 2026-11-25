# RN3-A: source-aware final root carry and residual conversion

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

Status before experiment: concrete paper candidate; no native construction.
This changes only the198E consuming-root component. The original normalized
input map, signed residual, root, physical body interface, exponent flags,
coefficient model, endpoint phase and accuracy are unchanged.

## Exact relations and preparation/cleanup

After j11's appended00 pair is processed, its low pair is11. Thus j12's first
high target bit is1. Its carry-in is b, and the conjugated target is1 xor b.
The first full-adder carry is therefore the first older-root source a, since
majority(a,1 xor b,b)=a. The first sum is written Clifford-only and a becomes
the preserved incoming carry for the remaining11 target bits. It is disjoint
from that target and from the remaining9 source bits. Inverse subtraction has
the same outgoing-carry alias: its complemented first target equals a.
This replaces11 ANDs by10 in each direction at j12, saving2 round trip.

Immediately before the final residual conversion, the low four remainder
values are W0=W1=W2=1 and W3=1 xor Q1 xor Q2. Clear them with Clifford gates;
they need no measurement. The outgoing carry into W4 of the old low-three-bit
addition is computed from the root alone:

    p = (Q0 xor Q2) * (Q1 xor Q2)
    a2 = 1 xor Q0 xor Q1 xor Q2
    c2 = Q1 xor p
    c3 = a2 xor ((Q3 xor a2) * (c2 xor a2))

Two ANDs prepare p,c3. The remaining10-bit target W4..13 adds Q4..11+c3 in
the original Q0-conjugated frame, with the original leading-one term at W12.
That adder costs9 ANDs. Both helpers are erased locally by their exact AND
measurement corrections while all Q controls remain restored; no residual
phase survives. Inverse applies the same2-AND preparation, inverse10-bit
adder, helper cleanup, and Clifford recreation of the low four remainder
values. This includes every preparation and return cost.

## Complete delta ledger before execution

| Component | Baseline forward/inverse | Candidate forward/inverse | Saving |
|---|---:|---:|---:|
| j12 high addition | 11 /11 | 10 /10 | 2 |
| Final residual conversion, including low cleanup | 13 /13 | 11 /11 | 4 |
| Other root steps | unchanged | unchanged | 0 |
| Complete root | 99 /99 | 96 /96 | 6 |

Paper peak prediction: at most39 including flags4, below baseline41 and the
unchanged global48. Every body boundary still has root12+residual10+flags4=26.
T delta0; R delta0; phase/accuracy delta0. No helper remains through the
coefficient/phase lifecycle.

Complete candidate expectation if proved:1578Toffolis+4T+33R atQ48;
per-shot1810.848059461612; full cost86,872.70685415737. This is a modeled
gate only until exact source proof, parent review, native proof and the
unchanged four original salts pass. No current qualified result is changed.

## Bounded exact certificate

The planned script uses only a source counter and a Boolean bitset builder,
never a native CircuitBuilder or simulator. It checks the16 low-root states,
the complete owned source, every normalized n in[2^20,2^22), all original
input/flag restoration, every zero release, and each independent local HMR
phase. Chunk65536 limits memory. Source inputs and guard/window hashes are
pinned before execution. Guard timeout60s, hard per-process512MiB, original
shared serial lock and unchanged process/headroom constraints.

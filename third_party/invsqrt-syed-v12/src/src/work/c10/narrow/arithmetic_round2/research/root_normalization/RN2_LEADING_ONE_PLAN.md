# RN2-A: clear the leading one in the forward pair normalizer

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

Paper candidate before any experiment. Replace only normalization.forward;
the existing inverse is byte-identical and the body n22/flags4 interface is
unchanged. No endpoint, shared phase cleanup, coefficient loader or numerical
model is altered.

## Construction and complete ledger

Extend the existing leading-zero prefixes P1..P20 by P21 using one extra
AND. Positive original x has at most21 leading zero bits. The original
maximum excludes both highest input bits being1, so the existing freeP2
identity is retained exactly on the official domain.

The indicator that x_i is the leading one is P_(21-i) xor P_(22-i), with
P0=1 and P22=0. Clear that bit from every original input position using
only X/CX. The odd-position lane's highest pair is now zero regardless of
the leading-bit parity. Its physical top owner x21 is therefore zero.
Compute H=1 xor P1 xor ... xor P21 into x21 using Clifford gates; H is the
normalized top bit.

Route odd input positions1..19 as a10-position zero-supported lane using
15 controlled swaps. Route even positions0..20 as the original11-position
lane using17 controlled swaps. Their shared shift is k, selected from the
existing even prefixes T1..T10. Finally toggle x20 by1 xor H to restore
the removed leading one in its normalized position; x21 already equalsH.

Erase odd prefixes P1..P19 using the unchanged local quadratic identities.
The extra P21 equals T10*(1 xor H) and also has a Clifford-only HMR phase
correction. Erase even prefixes with the existing threshold code and one
helper, exactly as before. Every prefix and helper is gone at the body cut.

| Part | Old forward | Proposed forward |
|---|---:|---:|
| Prefix preparation | 18 | 19 |
| Pair routing | 34 | 32 |
| Threshold-cleanup helper preparation | 1 | 1 |
| All other Clifford/HMR cleanup | 0 | 0 |
| Forward total | 53 | 52 |
| Unchanged inverse | 44.5 | 44.5 |
| Complete normalization | 97.5 | 96.5 |

The extra prefix raises local allocation peak46→47, still below the frozen
global48. Complete savings1 expected Toffoli; T/R/phase/accuracy changes0.
Unchanged-root candidate:1583Toff/4T/33R, Q48, modeled87,112.70685415737.
Combined with separately proved RN3-A only if both interfaces pass:
1577Toff/4T/33R, Q48, modeled86,824.70685415737. Neither is a native result.

## Exact bounded proof requirements

Use the frozen source's truth-vector builder, not a native CircuitBuilder.
Prove every original x=1..3,133,452 simultaneously: n=x*4^k, exact binary
flags, all independent local HMR phase coefficients, complete inverse,
original owners and zero scratch. Price the actual new forward emitter
and unchanged inverse with the paper allocator. Record modeled peak47,
not a measured native resource. New guard60s/512MiB/shared serial lock;
wait for the parent to announce slot availability after the current queue
expiry. No automatic or immediate unchanged retry.

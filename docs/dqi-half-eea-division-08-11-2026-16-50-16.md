# Fixed multi-digit half-degree EEA division

Extended the prior monomial fixture to a complete fixed-degree polynomial division step with multiple quotient digits. The three-word test divides a degree-two selected numerator by a degree-one selected denominator. It computes the denominator inverse once, forms quotient digits for shifts one and zero in descending order, applies both updates to the remainder and Bézout row pairs, clears the inverse, and exchanges rows only after the complete division. The two quotient words and zero-denominator flag remain as explicit history. The inverse first restores the row positions, then reverses the two updates in ascending shift order, reconstructs and clears each quotient digit, clears the denominator inverse and flag, and restores all scratch.

A zero selected denominator sets the flag and leaves all rows and quotient words unchanged. As with the monomial fixture, the caller must establish that the selected degree indices are actual leading positions and that omitted high shifted terms are zero. A zero selected coefficient can also mean that the caller supplied a stale degree. Dynamic degree selection, checking these preconditions, history addressing, repeat-until-gcd control, and a complete reversible reciprocal remain outside this slice.

The measured three-word, two-digit native circuit uses 1,242 Toffoli-like gates and 292 declared qubits in each direction. Its count is 204 for the shared pair of denominator-inverse calls, 108 for quotient formation, 810 for both three-row product updates, 108 for one controlled row exchange, and 12 for the zero flag. Reusing the denominator inverse avoids repeating the 204-gate inverse pair per quotient digit. The two 12-bit quotient words and one flag are retained until the inverse.

For a fixed `w`-word row and `k+1` digits at shifts `k..0`, the current unoptimized structure has static count `216 + 36w + 54(k+1) + 162*((k+1)w - k(k+1)/2)` Toffoli-like gates per direction, excluding dynamic control, validity checks and history addressing. At `w=18,k=17` this is 29,538 gates and 217 retained quotient/flag bits for this one division. This is a circuit-structure projection, not a measured degree-35 reciprocal or full Euclidean schedule.

The native fixture exercises both nonzero quotient digits, a zero high digit, a zero low digit, a zero selected denominator, random row words, phase, scratch and exact reverse cleanup on 128 shots. Focused WSL testing, Ruff and Pyright passed. Forward and reverse receipts are under `docs/evidence/dqi-half-division-20261108/`. No full reciprocal or DQI admission is claimed.

The fixture also supports a fixed constant denominator (degree zero), producing three quotient digits from a degree-two numerator before its single exchange. This native forward and reverse case uses 1,458 Toffoli-like gates and 304 declared qubits, tests zero high digit and zero divisor, and verifies all three quotient words, phase, scratch and reverse cleanup. Its receipts are `three-digit-forward.json` and `three-digit-reverse.json` in the same evidence folder. Both fixed-degree tests, Ruff and Pyright passed; the degree is still selected before circuit emission, not dynamically in superposition.

An independent rebuild with the final generator reproduced all four
KMB hashes and resource counts. The original receipts retain their
scope labels.

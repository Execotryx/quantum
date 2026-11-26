# DQI runtime-mask scan width and cost

The native bilinear phase scan now uses its low locator bit as a temporary parity.
The retained root flag implies that bit was zero when its phase is enabled.
Each parity is XORed out before the next column, and flag erasure sees the
original locator evaluation. Mixed classical and quantum controls emit
conditional CNOTs without the outer branch instructions.

A second scan accepts the reduced Forney residue polynomial
`omega * inverse(locator') mod locator`. At each root its value is the error
magnitude, so the runtime mask is a Clifford phase controlled by the root flag.
This removes the separate reciprocal word bank from the scan and avoids the
charged bilinear phase at each position.

| Native scan at 4,095 positions, maximum degree 35 | Declared qubits | Toffoli-like gates |
| --- | ---: | ---: |
| Prior supplied locator, evaluator and reciprocal scan | 1,331 | 94,185 |
| Bilinear scan with the temporary locator bit | 1,319 | 94,185 |
| Supplied locator and Forney residue scan | 887 | 45,045 |

The pinned simulator tested both new layouts on 72 trajectories covering
weights zero through 35. It checked the decoded mask phase, exact restoration
of each input register and clean ancillary outputs. Focused tests also covered
reduced scans, direct Forney composition, and mutations of phase and cleanup.
All 56 focused tests passed and Pyright reported zero diagnostics.
[Prior scan](evidence/dqi-phase-scan-20261108/full-scan.json) ·
[Bilinear scan](evidence/aggregate36-20261126/dqi-phase-pilots/lent-parity-scan.json) ·
[Residue scan](evidence/aggregate36-20261126/dqi-phase-pilots/residue-scan.json)

The supplied-residue scan leaves one qubit under the 888-qubit DQI budget.
The existing generic quotient multiplication charges 260,820 Toffoli-like
gates at degree 35 for one clean XOR application. With the scan, that exceeds
305,000 gates even before locator construction, derivative reciprocal or the
outer inverse. The scan therefore needs a lower-cost in-place preparation
schedule before it can be evaluated as a complete decoder.
[Generic quotient emitter](../src/qcompile/dqi/quotient.py)

The separate gate-sharing screen examined 277,317 product gates across the
three hot stages of the 900-qubit source comparator. The symbolic windows
found no already-live conjunction and only two disjoint repeated-product
pairs with a single cache slot. The emitted direct reuse rewrite reproduced
the exact control circuit hash. Both 256-shot matched panels also reproduced
the executed counts and verifier-visible error offsets.
[Repeated products](evidence/aggregate36-20261126/dqi-phase-pilots/repeated-products.json) ·
[Matched source replay](evidence/aggregate36-20261126/dqi-phase-pilots/decoder-decision.json)

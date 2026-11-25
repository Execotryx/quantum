# D4 field multiplier audit

The traced decoder regenerated the exact banked D4 KMB, SHA-256
`53d8b2edf251e2a0c54c401a97d1396c7ed309e1cbfaab8d54a2c99a11ed6552`.
The decoder has 897 declared qubits, a peak of 897 live qubits, and
444,667 static Toffoli-like operations. Its eight-draw pricing mean
was 430,823.03.

| Full-field product routine | Static calls | Mean calls per shot | Toffolis per call | Extra qubits | Runs at decoder peak |
| --- | ---: | ---: | ---: | ---: | --- |
| `mul_xor0` | 4,290 | 4,290 | 42 | 0 | Yes |
| `mul_xor` | 306 | 306 | 42 | 1 | No |
| `mul_xor_noscratch` | 523 | 523 | 42 | 0 | Yes |

The calls execute unconditionally in the 0x1053 polynomial basis.
The inventory also records inversion, phase erasure and composite
helper variants with their allocation peaks. Nested routines can
count the same gates. The `q_inverse` context manager appears as
separate generator entry and resume segments. The conditional Toffoli counts reported for
phase helpers are static bounds. Extra live qubits are measured
above function entry and include locally allocated result registers.

The rank-15 GF(64) tensor passed all 4,096 subfield pairs. Its
45-term lift and Nasir Ali's rank-42 tensor each passed all 16,777,216
products in the 0x1053 polynomial basis. Two regenerations of the public
tensor matched its published hash. Both tensors already express their
linear forms in the decoder's basis.

The outcome is **no transplant**. The rank-42 candidate saves zero
Toffolis across the 5,119 calls per shot. The 45-term candidate would add
15,357. The required improvement is 4,308.23 Toffolis per shot. The
banked `dqi-v8` circuit remains selected.

[Inventory](evidence/dqi-multiplier-audit/inventory.json) ·
[Decision](evidence/dqi-multiplier-audit/decision.json) ·
[Rank-42 verification](evidence/dqi-multiplier-audit/scheme42.json) ·
[Tower check](evidence/dqi-multiplier-audit/tower45.log)

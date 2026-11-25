# AR005 isolated native v3 retirement

Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
Credits: Opus and Astra.

The parent accepted the complete paper gate in
`arithmetic_round2/receipts/PRODUCT_V3_PAPER_ACCEPTED.json`, SHA-256
`72fe5dcd5afb57baea23099619bcec05d4ca738a6787d289bd0badfb0ec6b80f`.
This directory implements only that accepted arithmetic component. Protected
loaders, phase endpoint, rotations and external seed cleanup are unchanged.

The adapter takes the mutable current root-owner list explicitly. At the
44-owner product-inverse cut it X-measures raw v3, removes that wire from the
dirty list, and marks the logical slot absent. The ordinary disposable-carry
inverse runs at 43 data owners. It preserves all ten product CarryDebts and
charges conditional regeneration of seven owned rounding carries. Row8 has
literal False carry; row9 aliases an existing product owner and is never freed.
After exact seed6 is restored, one CCX reconstructs a new v3 output, the actual
measurement sign is paid on that output, and its current physical handle is
returned through the original mutable root list. The seed token is untouched.

The expected pair is 103+124.5=227.5 Toffolis, plus one reconstruction. This is
228.5 versus the accepted AR002 238, a complete 9.5 saving at Q48. AR002's
known-zero row9 optimization is deliberately not added to this price: the
ordinary row is cheaper with the extra carry slot. The old seed lifecycle is
17.5, so the isolated seed/product/recovery fixture must total exactly246.

The native fixture has 27 finite inputs (D13,h10,raw low root4), eleven formal
quantum spectators (v4,R,a5,flags4,Hlow3,savedA6), and one known-zero forward
occupant. Its real seed/product forward runs at45 owners. The zero occupant is
freed before the inverse's44-owner cut. v3 retirement gives43; restoration gives
44; unchanged seed cleanup returns38. A proof-only generalized Clifford
permutation returns the new logical input values to all original physical
register owners without adding Toffolis or exceeding48.

The care set is every model root v=0..4095 and every ten-bit residual pattern
h=0..1023: 4,194,304 assignments. This is a superset of the normalized input
charts, and requires no signed15 product promise. The emitted-text checker
treats all eleven spectators and all HMR outcomes as independent symbolic
variables. It checks exact data restoration, scratch zero, every reset and
integral phase cancellation. Start with1,024 diagnostic assignments, then
65,536-assignment chunks, writing a partial receipt after each. Bound polynomial
size and process memory as in the frozen checker; split on a limit, never relax.

Meaningful negative controls omit the new v3 phase correction, a real original
row9 carry phase, and the linear v2 term in reconstruction. The first two must
fail phase with data restored; the third must fail data/reset checking. Four
seeded native diagnostics cover all4,096 roots twice and preserve arbitrary
spectators. Sampled resource means remain labelled sampled; exact expected cost
comes from the emitted-source counter.

The worker checks its frozen source manifest, the authorization, and all304
inherited input pins before imports. Use only the fresh round2 strict guard,
512MiB hard address-space limit, CPU110s and outer120s, shared lock unchanged.
This is component proof only. A composed all-input/all-HMR proof and all four
original official salts remain necessary for a qualified complete circuit.

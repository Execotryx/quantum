# Compact candidate06 phase adapter

Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0. Credits: Opus and Astra.

Authorized by `PAPER_GATE_RECEIPT_018_VARIANT.json`, SHA
99ef9a891d4e99b262b1a452ea48b18c536e91e7017f018b77bc37f1793ccffd.
The complete Q48 gate is1591 expected Toffolis,4T,34R and cost
87842.32264250425. This file owns only its145-Toffoli phase block.

Parent installs its pinned candidate05 variant first, then calls
`phase06.install(previous05)`. The adapter takes this explicit module argument;
it never imports `variant` and introduces no recursive installer. It keeps
candidate05's shifted route and exact(stage0,0,26) omission in both directions.

The endpoint data ownership is43. Two initialized1 wires give45. Only p is
retained, giving46. A nonlinear threshold plus feature AND gives peak48.
Retained c is removed. Replace every threshold ANF mask32 (c) by mask10
(f1*f3), using the actual five variables flags+[p]. The final overflow phase
is CZ(f1,f3). Every erased threshold is still degree at most2 in its live
variables, so its entire X-measurement sign is repaid by Clifford operations.

Complete phase ledger:128 route swaps+2 endpoint frame gates+1 p preparation
+7 threshold ANDs+7 feature ANDs=145 Toffolis,4T,34R. All candidate04 angles
and phase predicates remain identical. The inherited exact angle proxy is
specialized to require exactly(34 generic,4T,0 direct Clifford Z_POW) calls.
The absent direct Clifford call has been explicitly replaced by CZ; it is
not ignored by a permissive assertion.

The adapter asserts43 owners at entry/exit, observes its allocation peak48,
and records angle substitutions and phase allocation diagnostics. All other
native sources remain unchanged. No independent native execution; parent
owns full construction, exact all-input/all-HMR proof and official salts.

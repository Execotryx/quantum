# Reversible padding exchange for the open DQI successor

The early-tail decoder reached the converter with a correct
degree-35 projected pair. The synthetic padding made the even/odd
half-Euclidean sequence drop 5, 9 or 13 degrees on weights 0–5.
Its converter supports drops of at most two.

For these low-weight inputs, the locator and numerator have a
common product of three fixed node quadratics. The product starts
at node 4 for the even cases and node 5 for the odd cases. The
scalar screen replaced each common product with three distinct
irreducible quadratics. The chosen constants took all six captured
failures into the converter's tested gap range.

The emitted circuit divides each coefficient bank by the fixed
product in place, retaining the quotient in the high slots and
the remainder below it. It chooses the replacement only when
both remainders are zero. The inverse restores the original
product, recomputes the predicate and frees it. A fixed-factor
replacement preserves the rational function and its phase
residues. The builder checks that the new factors have no
base-field roots and differ from the extraction and finish
quadratics. This leaves the scan's original coordinates in place.

Two separate Ubuntu builds produced the same 891-qubit circuit
with 395,571 static Toffoli-like operations, SHA-256
`c726a6426612ce094ac0ea98d0fabafbe323c09d4fd078e3d2b037fa4bd5c5f7`.
The extra two qubits retain the two branch predicates across the
converter and scan. The targeted native replay cleared all 40
fixtures at both simulator seeds and with two mask patterns.
The separate native kernel test checked the live transformed bank,
rejection when either remainder is nonzero and exact inverse
cleanup and phase.

The full native replay cleared the six historical batches, with
1,536 shots per role. Both 4,096-shot panels were clean. Their higher
executed mean was 394,197.29 Toffoli-like gates per shot, below the
891-qubit ceiling of 436,645.01. The matched D4 control's higher
mean was 430,822.60. The candidate's development estimate at the
minimum pooled repetition factor was 374.51 billion, 9.72% below
the historical banked price. A separate panel verified 24 cases
per weight from zero through eight at two simulator seeds.

The Apache-2.0 source package is retained byte for byte with its
upstream notice and 431-file manifest. The paired campaign
registration binds both builds and the native report, and reserves
eight fresh development salts distinct from the verification
and confirmation histories. The cloud runner checks that its
preflight report matches before issuing the registered draws.

The project source passed Ruff and Pyright. The new native padding
test passed and five manifest and registration checks passed. A
separate Pyright check of the unmodified upstream package reported
2,219 diagnostics. Its imported sources retain the published hashes.

The instrumented build reproduced the frozen KMB and observed an
891-qubit live peak. Static counts reached 74,954 after extraction,
102,919 after synthesis, 163,671 after the outer preimage and finish,
207,957 after the scan, 271,960 after the shared return and 395,571
after complete cleanup.

The unmodified standalone adaptive-gauge checker stopped on its
classical-size assertion. A scratch-only diagnostic recorded
49,463 classical bits for the scan versus the predicted 49,462.
With that assertion recorded as an observation, its independent
oracle passed all 80 cases and three simulator seeds for the
gauge prefix, closed gauge and full scan. The diagnostic matched
expected phases, named input restoration and executed counts.
It preserves the standalone scan checker's original scope for
unregistered classical scratch.

The initial cloud package produced a byte-identical preflight and
then failed to import the helper used by the official evaluator.
No draw started in that attempt. A retry package includes the local
tool modules and passes the verifier-module import check from a
fresh extraction. The KMBs and campaign registration are unchanged
across attempts.

The retry completed all sixteen official draws. Both decoders
passed eight draws of 102,400 shots. Banked D4 recorded four phase
errors and zero value errors. The repaired decoder recorded six
value errors and zero phase errors. The pinned pooled price was
375,969,428,171.05 for the repair and 416,454,209,396.28 for banked
D4, a 9.72% reduction. This qualifies the repaired circuit for the
separate aggregate archive and confirmation.

[Build A](evidence/d4-open-successor-20261116/repadding/build-a.json) ·
[Build B](evidence/d4-open-successor-20261116/repadding/build-b.json) ·
[Preflight registration](evidence/d4-open-successor-20261116/repadding/preflight-registration.json) ·
[Native report](evidence/d4-open-successor-20261116/repadding/native-preflight.json) ·
[Low-weight panel](evidence/d4-open-successor-20261116/repadding/low-weight-panel.json) ·
[Source manifest](../third_party/dqi-syed-v12/SOURCE.json) ·
[Official campaign registration](evidence/d4-open-successor-20261116/repadding/campaign-registration.json) ·
[Stage profile](evidence/d4-open-successor-20261116/repadding/stage-profile.json) ·
[Gauge and scan diagnostic](evidence/d4-open-successor-20261116/repadding/adaptive-gauge-diagnostic.json) ·
[First cloud attempt](evidence/d4-open-successor-20261116/repadding/cloud-first-attempt/run.log) ·
[Completed cloud decision](evidence/d4-open-successor-20261116/repadding/cloud-official/campaign/decision.json) ·
[Qualified DQI member](evidence/d4-open-successor-20261116/repadding/dqi-open-repadding-member.json)

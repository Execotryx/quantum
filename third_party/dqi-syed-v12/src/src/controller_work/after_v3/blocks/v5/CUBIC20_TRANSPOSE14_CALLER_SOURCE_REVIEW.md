# Independent cubic20 / transpose14 caller source review

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

**Source review: no blocking issue found.** This is a separate addendum to CUBIC20_QUOTIENT62_SOURCE_REVIEW.md. The earlier source review and all emitter, checker, v4 and historical files remain unchanged. I performed bounded source reads and standard-library AST, hash and literal-copy checks only; I did not import the runtime, build or simulate a circuit, or run a native job.

## Binding

The reviewed file is `blocks/v5_cubic_phase20/check_preimage62_transpose14.py`, SHA-256 `df8087025095caa231bdbc186d93f399b157c6e8a3769278bdf3af2c8a86d169`. Its frozen parent is `k24/v5_transpose14/check_transpose14_preimage.py`, SHA-256 `64b8e50eb58f1310c1f79faec0a47c97db42807ffae5a6d5b358574f583e15fb`. I independently reconstructed all 21 declared once-only text substitutions and obtained exactly the actual derived body. The wrapper verifies this derivation again before runtime work.

The new paired, quantum phase and cubic leaf providers are pinned respectively to `b1e4b759b384a28b1ac557d6b5674319b5403cf53aa03cc0f196b03356d0d150`, `510b413697d3cd50b3d2c024252552bf294875ab5ff7ffe253f75b437b2fdc06`, and `5c4e5c8e8241aca141db76d2ce3bc9580a9647e72e895ac6ee9729c1351c6205`. Their actual loaded paths and the imported leaf identity are checked. Both core and outer paired-scale call sites use the same new module; the seam retains the selected outer. The custom event hook is attached after the existing event installation, and the tracked quotient function delegates to the original new-module function without recursion.

Preservation checks continue to identify the actual replacement providers honestly. They recheck accepted normalized sources, the frozen v4 component manifest, exact public transpose14 derivation and source snapshots. They do not temporarily substitute the old provider to satisfy an old identity assertion.

## Counts and lifetime gates

The checker requires exactly 18 paired-phase calls, static 89 per exclusive paired wrapper, and 22 helper availability at the caller. No paired quotient call may occur in the prefix. The required event triples are exactly 18 occurrences each of `(paired_dual62_exclusive_overlap,27,0)`, `(paired_dual62_rhs_zero,35,24)`, and `(paired_dual62_all_masks_zero,27,36)`. Old paired-converter, rare27 and dual63 event names are rejected.

Every other baseline event must remain byte-for-byte equal after the explicit name and 36-to-35 discount substitution. The exact Fraction equality requires the old preimage expectation minus 38 for transpose14 and minus `18*(1-2^-24)` for the new phase. The resulting required pair is 115025 static T and 114458.8700796295 model mean T, with prefix 57034 and Q889. The three nonlinear probe gates are separately identified and excluded from component cost.

The unchanged lifecycle checks require four forward calls, four transpose calls, four actual flag handoffs at the restored size-12 and size-15 witnesses, all 32 local debts retired, no pending source or quotient records, 14 park/unpark pairs and two parked-phase payments. A retained flag may not allocate an additional query, and the handoff with existing masks pays them before source mutation. The new phase helper must restore its inputs and all helper bits before returning. These remain native assertions; this review does not assert that the full caller has already passed them.

## Fixture and phase scope

The full panel retains all 256 original component fixtures and the same ten qualified profile supplements from the pinned transpose14 parent. The original fixtures have only the ordinary size-14 local mode; the supplemental fixtures explicitly supply the missing admitted modes. They are component-domain additions, not new physical syndrome samples or a population census. No additional gap pair is excluded.

The prefix checks the independently recomputed full preimage, all denominator and gauge data, and clean scratch, while explicitly leaving inherited phase debts open. The full pair checks arbitrary classical diagonal masks, three nonlinear probes, all data and bystander restoration, and all scratch over three HMR seeds. Both complete and prefix tapes are rebuilt and required byte-identical. The original fixture hash and reference preimage/profile evaluations remain mandatory.

This source gate supports a root-run full caller check. It does not itself bank a whole-decoder gain, alter the admitted event, replace an official run, or qualify a v5 release.

# V6 eleven-gate binding: independent source review

Copyright 2026 Syed Asad Ali. Licensed under Apache-2.0. Credits: Opus and Astra.

## Conclusion and scope

No source blocker was found in the held V6 binding, component-receipt producer,
or wrapper derivation below. This review used source reads, AST comparisons,
streamed file hashes, and reads of existing JSON receipts. It did not import
the project, invoke the producer, classify or sample any input, emit a circuit,
or run a native simulation. The V6 native component manifest was absent during
the review. A complete V6 circuit, joined panels, reproducible builds, and four
fresh original official runs remain separate requirements.

Paths in the following table are relative to `controller_work/after_v3/`.

| Reviewed input | SHA256 |
|---|---|
| `integration_v6/v6_binding.py` | `46476d02e7b76464e163622e22eb16e024a179c22fda916e233b86573f9f846b` |
| `integration_v6/prepare_component_gates.py` | `f3b11a10365acd1641ac02b627be73828ec933b0e3d9093d03ad848717615d0d` |
| `integration_v6/COMPONENT_GATE_PLAN.json` | `62caf1f761113ae527d1715c9aaf06f3094bfa02aaf5f9abaae8d938c9e9b627` |
| `integration_v6/COMPONENT_VALIDATOR_DERIVATION.json` | `21b0be90d872804e7e07f1409753b52728242927e92111a0b1af9b2279ff6b78` |
| `integration_v6/SOURCE_DERIVATION.json` | `897bbd459c69619cb845673425ee5ff1088c56822024f24635c0f012c9a98b48` |
| `integration_v6/JOINED_PANEL_PLAN.json` | `9adb5bba21de563991065793e4ffc24fcbe7351a5381952ed6a247bd601d97b0` |

The final plan has 132 exact source/evidence pins. They all matched current
file sizes and SHA256 values. The preceding 125-pin plan was also checked;
the final update preserves it and adds distinct corrective-preparation and
review evidence. All 78 source/evidence entries from the frozen V5b plan are
preserved. The 21-file V5b source packet is retained without assuming that a
V5b circuit or official result exists.

## Preservation and refusal behavior

The new binding independently retains the earlier 17-gate V4 manifest,
112-file V4 runtime inventory, initial V5 source packet/plan, and V5b source
packet/plan. It hashes contained canonical relative paths and checks sizes;
it does not read an old compiled tape. New emission requires an actual
eleven-component manifest matching the current plan and producer hashes.
Smoke receipts, the source plan alone, and historical official scores do
not satisfy that requirement.

The producer has exactly eleven named components and requires completed,
unstopped, exit-zero guards. It binds the actual checker, Python 3.13 command,
workspace, and output directory. Only the reviewed option set is accepted.
The new optional `--require-gauge1` flag is restricted to the third-chart key
checker; actual gauge-one coverage is required by the report validator even
when that flag was not supplied. The final input recheck precedes the
exclusive temporary-file creation and manifest replacement. A missing or
invalid input aborts without a successful manifest.

The nine existing V5b validator functions, `Inputs`, `cover`, and `require`
are AST-identical. Only `check_guard` and `main` change among prior functions.
The five additions are two receipt constructors and the isolated-chart,
deterministic-input, and physical-key validators. No earlier panel is dropped.

## New isolated third-chart gate

The validator matches the actual report
`blocks/v6/runs/third-chart-full/report.json`, SHA256
`f5d140bb46f1b84886c21cde6bff4e8cbe993d4e572a2e8ec9ecb28f6f943efb`.
It requires all 20,480 inputs across five declared local modes, including
4,098 actual zero raw inputs and 4,096 zero cross-coefficient cases, three
fixed HMR seeds, and two identical builds. The eight alias/type/lifecycle
rejection cases are explicit.

The open prefix is 620 T with three child masks and one predicate mask. Its
phase is deliberately untested. The paired component is 1,274 T before three
probe gates, with six child masks and two predicate masks; it requires full
phase, value, and scratch restoration. Executed counts are recomputed from
the observed three return-child zero masks and the return-predicate mask.
Both panels require Q889, 864 retained wires, the caller-owned 24-bit bank,
and the recorded distinction between resetting the borrowed prefix predicate
without freeing it and allocating the return predicate separately.

## New physical production gate

The validator matches the actual report
`blocks/v6/runs/first3-full/report.json`, SHA256
`923df5eb0f79f2090f012cc5286267c1de5b3444177516658c4901fd348f9cb4`.
It requires all 783 inputs: the original 781 key-domain inputs, the preserved
old rare input, and the new deterministic raw-zero input. The original 76
key-domain exclusions remain explicit. All three seeds must cover every
input exactly once in both prefix and paired panels and both carry-seam
panels.

The actual changed chart has 782 gauge-zero inputs and one gauge-one input.
The pinned fixture map binds that positive to case
`54d38bf59904d025bfe626a0db3007111eb8d6c3e975bf0dda3a99d8a4cba57a`,
weight 18, carry `(0, 2229)`, selected scalar 2229, and zero other half.
Old fixture names are not used as evidence of the new gauge branch.

The physical key count is 216,928 T, with prefix 101,087 T and three paired
probe gates. The exact source mean is `28402108715/131072`; it remains a
source expectation, not an official measured mean. The complete six-entry
event multiset is checked, including 32 direct quotient phases, 66 phase-27
calls, seven scalar-inverse mask events, and 21 remaining 22-T predicate
events. Six inverse-mask debts and the third-chart predicate debt must close.

The full paired key checks phase and restores every input. Prefix and both
public-carry seams are value-only because their HMR debts are still open.
The seam checks explicitly require carry one on physical indices 840 through
863, and the prefix also checks the owned tail bit. The scope is production
initial carry one; it does not claim a new arbitrary-initial-carry API.

The deterministic zero-residue input is bound to its exact preparation
report, case file, source map, and normally completed guard. That report
records unchanged complete-classifier admission, unchanged support,
nonzero magnitudes, exact old raw residue zero, and zero population draws.
These are preparation facts; the later native key receipt supplies the
component value/phase evidence.

## Wrapper and joined-panel scope

The build wrapper, public generator, physical checker wrapper, and equality
checker are byte-identical to their renamed V5b counterparts. The key wrapper
adds the exact 32-T prefix adjustment, uses the reviewed third-chart scale
oracle, and reports actual changed-gauge and raw-zero identifiers. Its old
fixture loader and native error checks remain intact.

The documentary joined plan preserves all five original roles: 781-key,
10,073-case corpus, physical 42, legacy rare key, and legacy rare full decoder.
It adds the actual new gauge-one key/full roles and the constructed raw-zero
full-decoder role. The legacy rare case is explicitly allowed to be gauge
zero in the new chart. The special-input preparation and these joined native
gates are not claimed by the plan.

The initial special-panel preparation failed on a case-identity convention
before producing its requested outputs. The final source plan preserves that
failed source/guard/stdout and pins a separate corrected preparer and review.
This review does not recast that failure as a successful preparation or infer
new joined results from the correction.

# Independent review of the initial v5 component gates

Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0.
Credits: Opus and Astra.

## Conclusion and scope

**No remaining source-level blocker was found in the reviewed version.** This
review covers the new pure source binding, component receipt producer, fixed
component plan, and five exact v4-to-v5 wrapper copies. It does not execute the
producer, import an emitter, build a circuit, simulate a native panel, or certify
an official price. At the final source check, `NATIVE_COMPONENT_GATES.json` was
absent, as intended.

The selected initial v5 changes are the production first-two 195-T closed
inverse and the additional public transpose window at 14. The paired phase
provider remains the qualified v4 `paired_phase63`. The separate paired62 caller
is not selected by this plan. The cutoff remains 15, the full scan remains 4095
positions, and the declared maximum is 889 qubits. The new component gates do
not constitute the complete new tape, joined panels, two identical full builds,
or four fresh original official runs.

## Exact reviewed sources

Paths in this table are relative to
`controller_work/after_v3/integration_v5/`.

| File | SHA256 |
|---|---|
| `v5_binding.py` | `6483e60a487e4783ebe63f47705b7ca2bf3d1ec17e4f54431983f22727792df2` |
| `prepare_component_gates.py` | `b6b206fe355bdc8724db3eb22920276538f156ef0fb970216317c1a8494a9988` |
| `COMPONENT_GATE_PLAN.json` | `0b4932be57dadb5ea3f70794d7635ed9b5db09a34f4ed4a05e5a3acf6d4b0518` |
| `SOURCE_DERIVATION.json` | `d86eca1067754f80c93f5e343b16b9735ae51ae531f426568d27da391abde3de` |
| `SOURCE_PREPARATION_CHECKS.json` | `07a2dabfa6f6a739833a0ee80426793e444876e761c6641f8058e396ab8bf593` |

All 39 files in the final plan were independently read and checked against their
declared byte counts and SHA256 values. The source binding retains the exact
frozen v4 17-component/163-file manifest and 112-file runtime inventory. It
rehashes those sources and receipts without reading the old compiled tape or
representing old official results as v5 results.

## Resolved finding: bind the original key fixtures before the run

The initial 34-file plan did not pre-pin the original prepared key corpus, its
rare physical gauge-one supplement, or the three reused key checking helpers.
The component checker recorded the current hashes, and the producer checked
those records against the current files; that alone did not establish their
identity with the specified original corpus. Counts of 782 cases and the gauge
histogram were insufficient to supply that identity.

The final plan adds exactly these five established identities:

| Input or helper | SHA256 |
|---|---|
| `night_c27/arithmetic/panel_audit/prepared/cases.json` | `eb9216d25bd69f17179533932f0ec6a8704860a366117bd370b6eec35495e339` |
| `after_c5/arithmetic_t/runs/first2-physical-gauge1/cases.json` | `149d50ccac0d343e4479444f1804a01127be648750f12ed9a99b1acc04f5b3d4` |
| `night_c27/arithmetic/panel_audit/check_key_boundary.py` | `2a5af18b8b0bd0bc0fef2cacf88dfcf58ce9a88d4c5f8790251f108f2f1a11a2` |
| `night_c27/arithmetic/panel_audit/physical_boundary_oracle.py` | `b2d7871501afdb528820c78989e408098ca441153fa16f98d4b5f9697810db99` |
| `after_c5/extractor_width/boundary_scale_adapter.py` | `573434146bd6eb945a524ded811ccc0f245d83e9ab53a98464d9c1c0593b1037` |

These paths are relative to `controller_work/`. Removing only these five
entries and using the original JSON serialization reconstructs the old plan
byte for byte, with SHA256
`12f2cb5358c427f799f0d03d367d67eff92e42200e189bd99658b0ae1e812463`.
The binding, producer, pipeline, events, wrappers, and native checkers did not
change to resolve this finding. The producer's existing duplicate-input
equality and final rehash now tie report-time source records to these exact
precommitted inputs.

## Required native evidence

The producer requires all four actual full reports and their normal completed
guards. Missing inputs exit with incomplete status before a native manifest is
created. Smoke commands, another checker, unsupported options, an incorrect
output directory, incomplete or stopped guards, and unsuccessful exit codes
are rejected. It captures the parsed JSON bytes, records all consumed source
identities, rechecks them before publication, and refuses to overwrite an
existing native manifest.

| Gate | Required scope |
|---|---|
| Retained-norm inverse | Five modes, 4096 sources per mode, 20480 cases, three HMR seeds, three prefix/pair/deferred-pair panels, two identical builds, Q889, and actual observed-mask T totals. Static component counts are 195, 390, and 387. |
| Production first-two key | All 781 original key cases plus the one recorded physical gauge-one case; 76 original exclusions remain explicit. Complete prefix/pair and public-carry-seam coverage across three seeds is required. The public initial carry is 1; no arbitrary-carry extension is claimed. Pair/prefix counts are 216986/101058, with three complete clean-bank lifecycles. |
| Isolated transpose handoff | Public size 11, all 256 cases, three seeds, prefix and pair, two identical builds, returned flag checks, Q889, core 2724, and full counts 2768/5561. |
| Full preimage caller | All 256 original cases plus ten fixed supplemental component cases, two identical prefix/pair builds, three seeds, Q889, prefix 57034, pair 115043, and the original conditional event multiset. |

The 266-case preimage gate preserves every original index. Its supplement is
bound to the exact five saved physical records at indices
3205, 3320, 3605, 5894, and 6385 and the unchanged classical reference. Each is
used in both gauge charts. The added modes are `100`:2, `010`:4, and `001`:4.
Four added component cases originate from fully admitted physical inputs; six
originate from inputs excluded from the whole decoder only by the cutoff.
Those six remain explicitly labeled as such. No population draws or newly
generated physical inputs are claimed.

The full preimage gate checks four exact source-flag handoffs at parent sizes
12 and 15 in both directions, all 32 created/retired local masks, 14 gauge
parks/unparks, two parked payments, and the one existing top-16 requery. It
compares the complete conditional event lists with the pinned v4 report and
requires the exact -38 T source-mean difference. It therefore does not obtain
extra credit by counting an existing local-mask discount twice. Prefix phase
remains deliberately open and is labeled value-only; full paired phases and
restoration are separately required.

## Exact wrapper derivations and remaining gates

The five wrapper bytes were independently reconstructed from the pinned v4
parents by the two declared global literal substitutions, `v4` to `v5` and
`V4` to `V5`. No other byte differed. All five reconstructed Python files were
AST-parsed without importing them.

| New wrapper | Occurrences replaced: lower / upper case |
|---|---:|
| `build_v5.py` | 4 / 2 |
| `gen_dqi.py` | 3 / 0 |
| `check_build_equality.py` | 1 / 1 |
| `check_candidate.py` | 3 / 1 |
| `check_key_boundary.py` | 4 / 1 |

The production entry point retains its fixed public argument surface. The
engineering scan-size option remains confined to the builder. Fresh loaded
source inventories identify the actual v5 imports and preserve the old source
maps without rewriting them. Output counts and exact event expectations are
checked during later emission; they are not reported here as measured values.

The completed scope of this review is source reading, literal reconstruction,
AST parsing, and hash/size comparison. Root must still run or validate the four
native component gates, invoke the receipt producer, build and qualify the
complete selected v5 tape, and obtain its fresh official prices. No native
success, new failure certificate, target attainment, or delivery completion is
inferred from this source review.

# FA004-v6: verified fusion circuit

Copyright 2026 Syed Asad Ali. Apache-2.0 for the team’s own code. Credits: Opus and Astra.

**Q57, exact expected cost 89,799.18999469919. All four official salts meet the 89,987 target.** No submission was made.

The accepted circuit is `candidates/fa004_v6/invsqrt.kmb`. Its SHA-256 is:

`0f11b8db5240aa1acffb38b40ac07ed1fad077c8008d979f55369dfb2eb0c934`

The selected source is `source_fa004_v6`; its 208 files are checked against the immutable source manifest. The selected acceptance record governs this result; earlier candidates, paper prices and unfinished research remain separately identified in the checkpoints.

## Complete resource result

| Quantity | Stage 97 | Accepted FA003 | This revision |
|---|---:|---:|---:|
| Physical qubits | 56 | 57 | 57 |
| Exact mean Toffolis | 1332.125 | 1296.249999046 | 1259.710936546 |
| Exact mean T | 14 | 14 | 14 |
| Generic rotations | 43 | 43 | 43 |
| Expected equivalents per shot | 1647.838449325590 | 1611.963448371916 | 1575.424385871916 |
| Expected Q×E | 92,278.95316223303 | 91,881.91655719919 | 89,799.18999469919 |

The exact expected improvement over FA003 is 2,082.72656250000 cost (2.266743%). The expected margin below 89,987 is 187.81000530081. Rotation charge is 312.213449325590 equivalents at the official measured epsilon `1.725066196935686e-13`. Branch expectations and sampled verifier outputs are kept distinct.

## Four unchanged official salts

| Salt | Result | Verified shots | Sampled Toffolis | Sampled T | Sampled E | Sampled cost |
|---|---|---:|---:|---:|---:|---:|
| default | PASS | 200,540,928 | 1259.709848705 | 13.999225565 | 1575.423104421531 | 89,799.11695202728 |
| 1 | PASS | 200,540,928 | 1259.711542379 | 14.001002000 | 1575.425242204598 | 89,799.23880566208 |
| 2 | PASS | 200,540,928 | 1259.709961998 | 13.999740921 | 1575.423346554150 | 89,799.13075358653 |
| 3 | PASS | 200,540,928 | 1259.711284885 | 14.000180382 | 1575.424779306570 | 89,799.21242047451 |

Every salt checks all 3,133,452 official inputs with 64 shots per input: **802,163,712 official shots total**. The official full input domain, tolerance, register checks and salt implementation are unchanged. Each salt runs under the original process-tree memory guard with four workers; the complete guard logs, commands, raw results and hashes are retained.

The worst error/tolerance ratio is **0.979939356955965** at **x=55,049**. The model, angle and numerical-profile files are byte-identical to FA003. The arithmetic/loading changes therefore do not claim extra accuracy margin or looser synthesis tolerance.

Official verifier SHA-256: `ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a`.

On this run the guarded full build took 615.054 seconds, and the four guarded salts took 1963.259 seconds combined. The build’s peak process-tree RSS was 231.164 MiB; the largest official salt peaked at 653.246 MiB. These timings and memory measurements describe this machine and run.

The official report lists 99,922 serialized operations and reaction_depth=1220, compared with 61,434 operations and reaction_depth=707 for FA003. The competition objective charges the specified qubits, Toffolis, T and rotations; Clifford work and the reported reaction depth are separate implementation tradeoffs.

## The two requested gaps

Each cell below is exact mean Toffoli / T / generic-rotation count. Groups are disjoint and sum to the full circuit. The public comparator is the actual embedded a15 predecessor analyzed earlier; it is not a claim to possess or measure the absent 6c6a734d binary. Its source material supplied ideas only.

| Functional block | FA003 | This revision | Public a15 at Q62 |
|---|---:|---:|---:|
| Normalization and shifter, round trip | 122 / 0 / 0 | 122 / 0 / 0 | 127 / 0 / 0 |
| Forward coefficient loading | 275 / 0 / 0 | 266 / 0 / 0 | 243 / 0 / 0 |
| Forward arithmetic | 290 / 0 / 0 | 290 / 0 / 0 | 284 / 0 / 0 |
| Phase application and local cleanup | 154.999999046 / 1.5 / 43 | 154.999999046 / 1.5 / 43 | 153.960781068 / 1 / 41 |
| Remaining uncomputation | 454.25 / 12.5 / 0 | 426.7109375 / 12.5 / 0 | 411.873046875 / 0 / 0 |

Forward coefficient loading improves by **9 Toffolis per shot**; remaining uncomputation improves by **27.5390625**. The comparison includes complete cleanup: cost moved into address restoration is not also claimed as a separate eliminated table-bank cost.

## Exact disjoint regions and live width

| Region | FA003 Toffolis | This revision Toffolis | T | Rotations | Live entry→exit | Exact local peak |
|---|---:|---:|---:|---:|---:|---:|
| normalization | 61 | 61 | 0 | 0 | 26→29 | 55 |
| pack_shift | 0 | 0 | 0 | 0 | 29→25 | 29 |
| high_phase | 56 | 56 | 1 | 15 | 55→53 | 57 |
| initial_lookup_and_address_retirement | 230 | 222 | 0 | 0 | 25→51 | 57 |
| forward_curvature_low | 72 | 72 | 0 | 0 | 51→53 | 56 |
| curvature_to_derivative_high | 45 | 44 | 0 | 0 | 53→51 | 56 |
| forward_curvature_high | 7 | 7 | 0 | 0 | 51→50 | 54 |
| forward_result | 211 | 211 | 0 | 0 | 51→53 | 57 |
| low_phase | 98.999999046 | 98.999999046 | 0.5 | 28 | 53→50 | 57 |
| backward_result | 243 | 230.75 | 12 | 0 | 50→48 | 57 |
| restore_curvature_carry | 15 | 11 | 0 | 0 | 48→49 | 51 |
| backward_curvature_high | 7 | 7 | 0 | 0 | 49→49 | 55 |
| derivative_high_to_curvature | 65.25 | 59.5 | 0.5 | 0 | 49→49 | 57 |
| retire_constant_workspace | 0 | 0 | 0 | 0 | 49→48 | 49 |
| backward_curvature_low | 63 | 58.5 | 0 | 0 | 48→45 | 56 |
| restore_address_and_erase_coefficients | 61 | 59.9609375 | 0 | 0 | 45→23 | 57 |
| repay_table_measurements | 0 | 0 | 0 | 0 | 23→23 | 23 |
| restore_input | 61 | 61 | 0 | 0 | 23→22 | 43 |

Widths count allocated owners, including zero scratch and spectators. Independently compiled branch bodies are checked separately; their widths are not added as if they coexisted. The selected production builder has all 18 regions and agrees with the native serialized circuit’s global width.

## Selected own-source changes

The following entries are the pre-build component ledger. Negative values are savings against FA003. Their sum is checked against the full emitted expectation.

| Idea | Change in E per shot |
|---|---:|
| L2 initial coefficient converter with deterministic output priority171 | -5 |
| L1 last forward delta-pair output frame | -1 |
| Seven inverse output relation recipes, decoder44 | -4 |
| Late Fourier repayment after mandatory outputs | -1.25 |
| Main inverse branch with zero suffix phase | -0.25 |
| Eight conditional cleanup growth helpers | -1.0234375 |
| Conditional outer Blo8 plus inner Blo3 curvature shortening including complete29-code return penalty | -3.5 |
| Joint late phase pair on odd Fourier branch | -0.5 |
| Transfer original main parent top into restored output and shorten ten inverse rows | -10 |
| High-word decoder32→30 with exact product refactoring and staggered three-helper lifetime | -2 |
| Zero-Pauli owner main inverse terminal partition | -2 |
| Branch-specific conditional Blo3 retention and exact common-address join | -0.5 |
| Original Blo9 restoration using analytically certified liveR12..16 inputs and two locally repaid helpers | -4 |
| High4 fixed-lifetime kernel refinement, complete high loader30-to29 | -1 |
| Local L3L5 product only on light final return, including complete changed growth | -0.015625 |
| Even-first semantic address output priority on the local light L3L5 return, complete growth included | -0.5 |
| **Total** | **-36.5390625** |

## Proof and acceptance boundaries

Each changed component was priced first and then checked on its declared mathematical input code. The component evidence includes exact symbolic HMR phase ownership, clean scratch, preserved spectators and native kickmix checks. Component proofs are not labeled full invsqrt verification. The final source was frozen before its guarded complete build, and all listed source and component-evidence hashes were checked again during acceptance.

The complete native integration probe passed **41,984 shots over 10,418 distinct inputs and four seeds**, including boundary/tail inputs, exact phase agreement with the certified baseline relation, input restoration and clean scratch. It is a targeted integration check; the four full official salts provide the separate exhaustive official domain check.

The exact resource counter retains the original region/hash/static-inventory checks. It splits the two literal Fourier outcomes into four exhaustive cases, uses Gaussian affine conditions and bounded Boolean diagrams for remaining guards, and preserves stale classical destinations under inactive HMRs. It never assumes overlapping guards are independent. Its small-case crosscheck and per-case accounting are included with the resource report.

No public circuit blocks, public code, public numerical tables or saved public gate sequences are generator inputs. The selected source derives the circuit from the team’s own mathematical model and compiler recipes. The official verifier and bundled runtime retain their original notices and licenses.

## Reproduction and evidence

Use Linux CPython 3.13 and the bundled compatible kickmix extension. The verified release contains `REPRODUCE_COMMANDS.json` with exact argument arrays, the selected generator, original official verifier, memory guards, native probe, exact counter and all acceptance evidence. Use fresh output paths. Run the complete generation, native probe, region accounting and original four salts; compare the generated binary SHA-256 above before adopting it on another machine.

Primary acceptance record: `fa004/accepted/FA004-v6.json`.

Candidate evidence directory: `candidates/fa004_v6`.

Source manifest: `candidates/fa004_v6/source_manifest.json`.

The full research checkpoints additionally contain `RESUME.md`, `PLAN_FA004.md`, scoped rejected families, unbuilt drafts and the preserved earlier accepted revisions. A bounded search closure describes only its stated family; it is not a general lower bound on circuits.

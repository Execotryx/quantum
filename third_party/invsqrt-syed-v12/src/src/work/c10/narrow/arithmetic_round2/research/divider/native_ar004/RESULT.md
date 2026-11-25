# AR004 native divider pass

Copyright2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0. Credits: Opus and Astra.

The native history12-retirement divider passes with **578 expected Toffolis,0T,0R at Q48**. Its unchanged forward costs270; cleanup costs308. This saves9.5 expected Toffolis from the original587.5 divider, or8.5 beyond the preserved native AR003 fallback. These are exact expected instruction counts from the emitted native classical guards, separately checked from sampled simulator statistics.

The emitted forward text is byte-identical to the accepted frozen forward. It retains the same43-owner endpoint. After that endpoint, history12 is measured out with its exact Clifford correction, inverse arithmetic uses42 data owners, and a one-Toffoli reconstruction restores the current sign owner before AR003's final row. The adapter returns current logical P15 owners; the caller must propagate that array.

Native checks passed:

- All3,133,452 original inputs in48 contiguous chunks, with all583 HMR transcripts symbolic.
- Exact zero roundtrip phase, original input restoration, zero scratch, every reset valid, and all24 CarryDebts consumed.
- The full encoded input digest equals the frozen AR003 digest.
- Four simulator seeds, each with16384 valid original-domain cases and8192 root-boundary inputs covering both ends of all4096 root intervals.
- Independent forward endpoint remainder/history checks.
- Two deliberate complete-circuit errors rejected specifically as unpaid phase: omitted history12 retirement CZ, and omitted original forward CarryDebt Z.
- Three positive and four negative tests of the unchanged31-input/modulo2 native checker.

The native proof took5.787seconds. The strict shared guard completed with exit0 in6.755seconds, peak aggregate RSS48,803,840 bytes, and complete child cleanup. All7 frozen source members and326 input pins were rechecked afterward.

The supported promise remains the actual frozen numerical model on original x=1..3,133,452. The retained abstract root4095/product counterexamples are outside that promise. No arbitrary unrelated root/product-domain claim is made.

## Handoff

Call `native_ar004.adapter.install(divider_module)` after installing the original candidate02 initializer and the existing forward divider. It changes only `cleanup_divider`; it does not change the phase endpoint or forward arithmetic. Alternatively use `bind(divider_module)` for a standalone cleanup callback. The preserved complete43-owner endpoint is the parent integration boundary.

Production caller state remains31 owners on entry and exit: root12, product15 and exponent4. Proof-only Clifford swaps restore registered physical input positions; the production adapter instead returns explicit current logical owners. Parent whole-circuit generation must retain the unchanged exact50-bit phase oracle.

This is a **native component pass, not official full-circuit qualification**. Applied alone to candidate07 it models Q48,1574.5 expected Toffolis,4T,33 rotations and cost86704.70685415737. The parent owns composition with other round2 savings, whole native verification and four official salts at original tolerance.

## Evidence hashes

| Artifact | SHA-256 |
|---|---|
| NATIVE_PROOF.json | `b1e9bf4f4696a25a92512d9f0cba394b8e65be616a368cd506a8a9676907699f` |
| native.guard.json | `b287a438f15a21bcdc92c1e8df85973855eded5ef1f43aaa7234dcd903649889` |
| divider_roundtrip.kmb | `a3061154341f4f52f318132815758cc7042a5d7cb1c4ca40acdfc898253dfe91` |
| divider_roundtrip.kmx | `92eac7b70271fc6687a55317db88f0451a29a7568442c8a970da0f78bd78abc9` |
| SOURCE_READY.json | `6b33c3b0e619d90bd5bc4674fdc075a91b7170475816ac787b7da8a9f4c6dcfe` |
| INPUTS.json | `89ca5d0a650e132b92f56c26e4d0c4e14d1d4aecca9224471577bc6906350aed` |

`AUDIT.json` checks resources, guards, data coverage and source bindings; `AUDIT_CHUNKS.json` explicitly checks every native chunk's HMR, phase, restoration and reset fields. `MANIFEST_RESULTS.json` freezes the complete local result set.

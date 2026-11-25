# Candidate04: exact quantized angle refit

Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0. Credits: Opus and Astra.

This isolated variant is authorized by `PAPER_GATE_RECEIPT_014_VARIANT.json`
(SHA-256 `d3ece51a8a4443080d4899f1076cbc1ef85d263057e364de79e1a4cc43ad8a18`).
It inherits candidate03's proved complete arithmetic, owners, measurement
corrections and input layout. Only the 34 existing generic rotation angles
change. Candidates01, 02 and 03 and all prior research sources remain frozen.

## Complete paper gate

| Item | Complete value |
| --- | ---: |
| Peak qubits, including both coefficient preparations | 49 |
| Expected Toffolis, inherited native count | 1,562.5 |
| T gates | 4 |
| Generic rotations | 34 |
| Proved accuracy margin lower bound, in 2^-64 turns | 124,286,782 |
| Rotation charge upper bound | 238.0530968204069 |
| Complete cost upper bound | 88,276.10174419993 |

The margin is a rigorous bound, not a measured quantized margin. The previous
exact full-domain refit margin is124,397,056; the exact sum of absolute angle
rounding changes is110,274. Every affected phase predicate is Boolean, so the
triangle inequality proves the lower bound above on the original domain and
unchanged tolerance. Every new angle is a rational multiple of2^-50 turns and
remains a generic rotation. The arithmetic and both preparation peaks are
unchanged. No new register, carry, measurement debt, routing or phase feature
is introduced.

## Implementation boundary

The new variant loads the source-pinned candidate03 installer. During the
existing endpoint phase call only, a builder proxy checks each of the34 old
generic angles in its exact order and substitutes its new Fraction. The four
T rotations and the Clifford phase are delegated unchanged. All other builder
operations and all logical owner handoffs are delegated unchanged. Emission
must prove that the complete parsed native circuit differs from candidate03
at exactly these34 angles, with every gate, operand, condition, HMR event,
register and other angle unchanged.

## Guarded execution sequence

1. Run the frozen `quantize50.py` on all3,133,452 original inputs. Require zero
   failures, the original tolerance, exact34 generic/4T classes and an exact
   minimum margin at least124,286,782. This is required before emission.
2. Emit the isolated candidate04 and perform the structural angle-only diff
   and exact native resource check against the complete gate.
3. Run new positive and negative exact checker tests at modulus2^50. Include
   one-unit positive/negative phases, incorrect units, omitted HMR correction,
   dirty reset, wrong input restoration, HMR-dependent fractional phase and
   wrong expected phase. The pinned checker is loaded in a separate module
   and explicitly set to2^50; its old2^37 selftest is never reused.
4. Run8,192 native shots under each of seeds0,1,2,3, checking exact Fraction
   phase, original input restoration and every scratch wire.
5. Prove a1,024-input exact native-text diagnostic, then all3,133,452 inputs
   and all HMR transcripts. The phase oracle uses exact integer2^-50 units;
   its full-domain digest must equal the independently screened digest.
6. Parent runs the unchanged official verifier at default,1,2,3. A native
   proof or paper cost is not official qualification.

The batch requires the parent's shared strict guard and inherited512MiB hard
address-space limit. It runs serial subprocesses and stops on the first
failure. Symbolic representation limits require splitting the affected input
chunk; no phase, reset, transcript or tolerance check may be skipped. No
submission is authorized. Stop heavy work by02:20UTC and all work by02:30UTC.

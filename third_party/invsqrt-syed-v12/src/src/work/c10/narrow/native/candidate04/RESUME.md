# Candidate04 source handoff

Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0. Credits: Opus and Astra.

This directory contains the isolated angle-only variant authorized by
`narrow/PAPER_GATE_RECEIPT_014_VARIANT.json`. At source handoff it has not been
emitted or natively proved. Its complete conservative paper gate is Q49,
1,562.5 expected Toffolis,4T,34R, margin at least124,286,782 in2^-64 turns,
rotation charge at most238.0530968204069 and cost at most88,276.10174419993.
The margin is a proved lower bound, not the result of the pending full scan.

All execution belongs to the parent shared strict guard. Run under the
inherited512MiB hard address-space limit:

```
/usr/bin/python3.13 narrow/native/candidate04/run_batch.py --full-proof
```

The first subprocess runs the frozen full-domain `quantize50.py`. The next
subprocess refuses emission unless that exact scan passes, matches every
frozen angle and proves at least the authorized margin. Native generation
then uses the candidate03 installers and replaces only the34 generic angles
inside the old endpoint phase emitter. A complete parsed-native diff requires
all other instructions, operands, conditions, HMR events, registers and phases
to match candidate03 exactly.

`oracle50.py` starts from the independent signed-remainder mathematical model,
reconstructs the34 phase predicates, and agrees exactly between a direct new
angle sum and the old phase plus quantized perturbation. `prove50.py` explicitly
uses modulus2^50. It loads the pinned exact symbolic engine in a new module,
sets only its candidate modulus, and runs new positive/negative unit tests.
The baseline2^37 wrapper and its selftest are not used. Every reset, original
input, scratch value, fractional phase and HMR transcript remains checked.
The final full-domain oracle digest must equal the independent quantize scan.

The batch runs4 seeds of8,192 native shots, a1,024-input/all-HMR diagnostic and
the full3,133,452-input/all-HMR proof. It stops at any failure. A symbolic
representation limit splits only that interval and repeats the full exact
check on each smaller interval; no check is relaxed. The official verifier
at four unchanged salts remains the parent's separate qualification gate.

Preserve candidates01,02,03 and all research source pins. Store new run
receipts here, not in earlier candidate directories. `SOURCE_READY.json`
pins this handoff and `INPUTS.json` pins every inherited source and receipt.

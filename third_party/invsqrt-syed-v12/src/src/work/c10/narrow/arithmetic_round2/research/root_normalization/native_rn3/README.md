# RN3-A isolated native root component

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.

Authorized only after `arithmetic_round2/receipts/ROOT_RN3_PAPER_ACCEPTED.json`.
`root192.py` exports `forward(builder,norm22)` and `inverse(builder,norm22)`.
The return map and physical root/residual layout match the original root.
Four exponent flags may remain live spectators. No helper or phase debt
survives the component boundary. This module does not install monkeypatches.

The root and arithmetic helpers are loaded from their pinned original bytes
into private module instances. They never use the mutable global
`consuming_odd_sqrt._root_step` modified by an old candidate's installer.
All prior candidate/source files remain immutable.

`prove_root192.py` builds the native forward96 and roundtrip192 with localQ39,
and a new-forward/original103-inverse hybrid199 with localQ42. It checks
forward values, phase, flags and scratch on every root interval endpoint and
four seeded sample sets, then proves the roundtrip and hybrid on all3,145,728
normalized inputs and every native HMR transcript. The exact unchanged
checker uses the actual integral phase modulus2 for this arithmetic-only
component. This is not a complete invsqrt or official qualification.

Run only under the new round's strict guard and shared serial execution slot.
Freeze and verify `SOURCE_READY.json` before execution or integration.

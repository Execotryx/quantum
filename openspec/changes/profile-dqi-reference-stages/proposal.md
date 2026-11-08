## Why

Replacing every controlled product in the pinned synchronized-EEA decoder
with the tower-field product cut DQI cost by only 5.09%. Mean
Toffoli-like gates went from 5,725,109 to 5,433,437 at 1,893 qubits.
Field multiplication is therefore a minority of the reference budget.

Gu et al. (arXiv:2610.22367, SI I.1) attribute 3.8 million Toffolis of
their 5.1 million reimplementation to the forward Euclidean solve and its
reversal, and 1.3 million to the scan. The official reference exceeds
their reimplementation by about 0.6 million, which no source attributes.
Building the next decoder without a measured breakdown risks optimizing
the wrong stage again.

## What Changes

- Add a stage-attributing builder proxy around the pinned reference
  emitter. It records Toffoli-like gates, other gates and live width per
  decoder stage.
- Measure at reduced shapes and at full size.
- Report static counts and reconcile them with the verifier's executed
  means. The reference's maximum and mean differ by about 352 gates.
- Write a decision record that sets the build order for
  `build-routed-bm-dqi-decoder`.

## Impact

- Code: new `tools/dqi_stage_profile.py`, reusing the proxy pattern of
  `tools/dqi_decoder_screen.py`.
- Evidence only. No circuit enters an archive.
- Timebox: two engineering days.

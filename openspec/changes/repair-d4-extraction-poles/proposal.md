## Why

Banked D4 passed all eight full pricing draws but produced four wrong-phase shots
with clean registers and scratch. Replaying the three affected salts in Google
Cloud reproduced every historical receipt. All four failed trajectories entered
the converter with a denominator that omitted every true error position. Each
converter degree drop was one. See the
[cloud replay](../../../docs/dqi-phase-replay-cloud-15-11-2026-16-20-00.md).

Astra's scalar reconstruction of D4's geometry found nonterminal extraction
poles on all four failed inputs. Three take an ordinary jet at zero with a
nonzero derivative. The fourth reaches a genuine pole at the local inverse.
The passing controls have no nonterminal pole. A native observation at the
extraction boundary will verify the modeled divergence before repair.

## What Changes

- Freeze a reduced diagnostic from the four captured batches and reproduce the
  divergence immediately after extraction, before synthesis.
- Preserve homogeneous coordinates through intermediate poles and account for
  genuine poles at a repeated node across extraction and synthesis. Preserve
  restoration, including measured uncomputation and its phase corrections.
- Validate a separate candidate against the original batches and a fresh,
  preregistered full cloud campaign. Retain the original banked D4 receipts.

## Capabilities

### New Capabilities

- `dqi-d4-pole-safe-extraction` covers native root-cause confirmation,
  pole-safe reversible extraction and synthesis, and full-strength testing.

## Impact

The work targets the D4 adapter, diagnostic drivers, and release evidence.
The vendored D4 tree remains byte-identical to its provenance manifest. The
candidate has its own circuit hash and receipts. Banking or submitting it is
outside this change.

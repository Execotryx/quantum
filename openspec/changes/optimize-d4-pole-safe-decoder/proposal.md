## Why

The full-grid D4 repair cleared all four historical phase errors in the exact
1,024-shot replay. In eight fresh official draws it produced two value errors
and zero phase errors, while banked D4 produced no errors. The repair used
4,081 qubits and cost 63,747,071,243,053.88 under the pooled metric, versus
897 qubits and 414,840,001,725.70 for banked D4. The cause of the two new
value errors remains open. See the [verification report](../../../docs/d4-cloud-verification-15-11-2026-20-32-51.md).

## What Changes

- Replay the two value-error draws with the frozen full-grid circuit and
  identify the first failing boundary and any intentionally retained flags.
- Test whether a pole-aware implementation can reuse the low-width D4
  extraction, conversion and phase path. Use the full-grid repair and
  independent algebraic references as differential controls.
- Consider source-admitted open circuits and kernels that fit the same
  verifier contract. Evaluate their integration cost and reversible interfaces.
- Measure the exact candidate against a priced resource gate before a full
  campaign, and retain both correctness and cost evidence for the decision.

## Capabilities

### New Capabilities

- `dqi-d4-compact-pole-repair` covers compact repair synthesis, source admission,
  deterministic fault reproduction, and resource and verification gates.

## Impact

The implementation can touch DQI development adapters, diagnostic drivers,
tests and evidence. Source admission follows the existing provenance policy.
The work produces a selection decision and keeps the banked component and
previous certification available by their original hashes. Archive release
and submission remain separate workflows.

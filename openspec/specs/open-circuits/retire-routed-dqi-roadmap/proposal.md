## Why

Vendored public members should make two research lines unable to change the
score:

| Line | Best case | Public member |
| --- | --- | --- |
| Routed BM decoder, 1,942 qubits | Even Gu et al.'s published 4.4×10⁵ Toffolis at 1,837 qubits gives only ≈ 13.8×, because cost scales with Q² | ≈ 63× |
| Compressed DF-THC fits at `(9, 143, 40)`, stalled at 41.6 mHa | — | A public table at the same shape already passes |

But no public member has been regenerated and verified by us yet. Retiring
the old lines first would leave no path if a vendored member fails. So
retirement happens in two phases.

## What Changes

- **Phase 1, now:** mark the listed changes `paused`. Nothing is deleted
  and nothing is closed.
- **Phase 2, per task:** when the replacement member is banked, mark that
  task's changes `superseded`. If the replacement ends in `no_go`, mark them
  `resumed` instead.
- Keep the round-11 routed-decoder changes out of the repository while
  their task is paused.

## Impact

- No circuit, member or receipt changes.
- The routed decoder stays the DQI fallback member for releases throughout.

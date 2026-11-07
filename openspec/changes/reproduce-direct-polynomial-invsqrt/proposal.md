## Why

The hybrid branch has a locally verified archive scoring 1.0286345856615866
relative to the official reference. Its inverse-square-root component costs
1,971,483.438323478 at 256 qubits and uses 84.6925% of the allowed phase error
at its worst input. The existing optimization narrows widths within the
reference construction. Direct polynomial phasing tests whether changing the
construction can deliver a larger reduction while retaining the measured
chemistry improvement.

## What changes

- Work on `codex/invsqrt-chemistry`. Leave the inverse-square-root-only branch
  and its release plan separate.
- Audit and reproduce a source-available direct-phasing design before
  optimizing it. Record an independent implementation as such if the source
  audit rules out exact reproduction.
- Add a generator and a finite-width phase model, then screen piecewise
  approximations, fused arithmetic and earlier scratch cleanup using the
  pinned verifier contract and complete rotation-inclusive cost.
- Require full verification and fresh confirmation on one frozen winner.
  Build a successor hybrid archive with only the inverse-square-root member
  changed. Reverify the complete extraction and compare it to the current
  hybrid as well as the official reference.
- Specify how the successor release can inherit already certified chemistry
  evidence. The unchanged chemistry component keeps its original identity,
  confirmation history and cost. The new inverse-square-root component
  requires its own independent confirmation.

## Boundaries and dependencies

The existing [hybrid certification change](../certify-hybrid-release/proposal.md)
owns certification of the current archive and the benchmark-scoped ledger.
Direct-phasing research and local comparison can proceed independently.
Formal certification of the successor requires the parent hybrid certificate
and the carry-forward checks specified here.

This change leaves the pinned official verifier, the accepted reference
artifacts, DQI and chemistry optimization logic, and the previous campaign
records intact. It covers local implementation and verification. Cloud runs
and external submission are separate operator actions.

## Success criteria

The screen records either a qualifying improvement or a reproducible no-go.
A qualifying component must clear the registered complete-cost and phase
gates in both full runs. A release claim also requires an independently rebuilt
archive, byte-for-byte retention of every chemistry and DQI member, and a
complete extracted-archive score above the current hybrid.

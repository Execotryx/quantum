## Control and decision order

Use the fully measured v2 archive, SHA-256
`9aac7afcd0ff3bbff7f4c65c85cf1b331e67b3fd9893ec83b8499d0f223bb841`.
Local source `01ffb4b` and published `44fa28c` identify the same
verification tree. Treat formal candidate-store certification and any
external receipt as separate state. Retain the measured aggregate
1.3779715417804443 and each original raw component receipt.
[Paired comparison](../../../docs/evidence/next-hybrid-20261108/paired-archive/comparison.json)

| Component | v2 cost | Full shots | Initial admission gate |
| --- | ---: | ---: | --- |
| DQI | 24,439,466,510,149.91 | 102,400 | Exact architecture, cost at most half the control. Record 8× as a stretch checkpoint. |
| DFTHC | 3,247,752,448.668952 | `(76 + R*B)*64` | At least 10% lower measured cost and all strict official gates. |
| Inverse square root | 820,078.9505284121 | 200,540,928 | At least 10% lower measured complete cost and at most 90% tolerance use. |

DQI is the primary implementation path. Chemistry ranking and numerical
pilot and inverse-square-root control profiling can begin in parallel
once their inputs are pinned. A candidate that changes one component
and improves its cost by factor `g` projects a new aggregate of
`1.3779715417804443 * g**(1/3)` when the retained costs agree. An
8× DQI reduction projects 2.756. A 2× reduction projects 1.736. The
roadmap's multipliers and public-frontier numbers are planning hypotheses.

## Shared workflow

1. Reuse `prepare-next-hybrid-verification` for artifact-bound coverage,
   parent lookup and release lineage. Create a prospective registration
   with the control identity, locked source and native assets, changed set,
   independent generation recipe, parameter grid, tie-breaks, execution
   roles, resource caps and distinct reserved salts. Keep an immutable
   terminal or interrupted receipt for each attempt. Maintain separate
   environment and backend receipts for each location.
2. Keep the official reference and the current v2 component as applicable
   controls. Use reduced exhaustive fixtures, native mutations and
   deterministic rebuilds locally. For DQI use the existing paired
   2,560-shot development path with shared cases and keep the disjoint
   value and phase failures. The 256-shot run is a confidence rejection
   control. Pin the selected full-strength salt schedule before seeing
   data. Retain every result and prohibit choosing the best salt.
3. Evaluate `kickmix-engine` as an optional scouting adapter after pinning
   a commit, wheel or build hash, license, native verifier and sampler.
   Use `--cross-check` against the pinned official verifier with identical
   cases, phase, register cleanup, error counters and applicable counts.
   Include seeded measurement and malformed-circuit controls. Require zero
   unexplained differences and a measured resource advantage. On a
   mismatch or unsupported opcode fall back to the official development
   path. Keep this dependency out of the production verifier lock.
   [Engine source and parity commands](https://github.com/manwithacat/kickmix-engine)
4. Profile one candidate on the actual runner before booking a larger
   tranche. Use WSL for small fixtures, numerical screens and low-memory
   work. Use a bounded approved x86-64 cloud job with frozen Python 3.13
   and dependencies for memory-heavy official controls, large fits and
   archive verification. The existing two-vCPU VM's prior paired archive
   took about 32 minutes. A separate full pass and confirmation can
   exceed the one-hour VM window. Schedule distinct durable jobs with
   a receipt upload after each terminal stage and stop the VM after
   verified collection. Quote any larger VM separately. Record peak
   process-tree PSS, swap PSS, summed RSS, wall/CPU time, and disk use.
   [Measured cloud and WSL run](../../../docs/next-hybrid-paired-archive-08-11-2026-01-13-24.md)
5. For each qualifying candidate run official full-strength verification
   and a distinct one-use confirmation on the same frozen bytes. Record
   worst phase tolerance or decoded residuals, actual coverage, failure
   counters and complete costs. Independently build the ZIP twice.
   Run `tools/hybrid_preflight.py` and the pinned full metric on a fresh
   extraction, using an archive seed separate from component confirmation.
   Reconcile retained DQI costs under matched draws if historical counts
   differ. Keep the v2 component for any lane that fails its gate.
   Add negative packaging cases for out-of-range physical IDs,
   invalid register names and caps, forbidden gates, malformed archive
   paths and NPZ header, dtype or allocation violations. Derive each
   boundary from the pinned metric and distinguish extra local guards.
6. Publish a comparison with component cost, actual aggregate, resource
   use, and exact archive and receipt hashes. If implementation is later
   authorized, update README and the dated change log after measurement.
   A leaderboard upload, team action or public notebook is outside this
   implementation plan. For all source-derived methods preserve the source
   revision, license and independent derivation notes.

## Lane plans

- [Exact DQI decoder](dqi.md)
- [DFTHC shape and loader search](chemistry.md)
- [Inverse-square-root width and cleanup](invsqrt.md)

The prior plans retain their receipts and unresolved evidence gates.
[Shared verification](../prepare-next-hybrid-verification/design.md) ·
[DQI](../prototype-qubit-first-dqi/design.md) ·
[DFTHC](../screen-dfthc-refactorization/design.md) ·
[Inverse square root](../screen-compact-invsqrt/design.md)

# Hybrid roadmap investigation, 8 November 2026

Three Astra subagents investigated DQI, DFTHC and inverse square root
in parallel. The [OpenSpec implementation plan](../openspec/changes/advance-hybrid-optimization/design.md)
integrates their findings with the pinned verifier and v2 receipts.
The [task list](../openspec/changes/advance-hybrid-optimization/tasks.md)
defines the implementation and verification checkpoints.

The reviewed attachment was the quantum circuit compilation roadmap,
SHA-256 `09b2ca401b22feedf795c693be93d26e2cd59b4682c837c936c954148a3ccab6`.
The active source was `01ffb4b` on `codex/invsqrt-chemistry`.

- DQI retains the exact-first 2× gate. The cited research result used a
  different field encoding, fixed masks and a bounded approximate
  schedule. The plan prices clean forward and reverse arithmetic under
  the pinned runtime-mask contract.
- DFTHC starts with a numerical feasibility bound and a profiled fit.
  The ANGLE precision is separate from alias-sampling precision. The
  shifted residual, one-body eigensolve and full scored workspace
  determine whether a compact shape is eligible.
- Inverse square root uses the measured 175-qubit v2 circuit and a
  new 738,071.06 admission ceiling. The plan requires a branch-phase
  proof and native cleanup fixtures before testing measurement unlookup.

This entry records the planning work. The proposed execution, publication
and submission decisions are tracked separately.

# Direct polynomial phasing plan on the hybrid branch

Added the [direct polynomial phasing OpenSpec](../openspec/changes/reproduce-direct-polynomial-invsqrt/proposal.md)
on `codex/invsqrt-chemistry`. The proposal, design, requirements and task
checklist target the currently verified hybrid. They pin the inverse-square-root
incumbent and require the successor archive to preserve all chemistry and
DQI members by hash.

The plan separates source provenance, faithful reproduction, exhaustive
phase and rotation-cost screening, and full verification with fresh
confirmation. The existing hybrid certification proposal now identifies
its role as the parent certificate for a future successor. An unchanged
certified chemistry family can be linked as parent evidence without
reserving another confirmation or weakening the current release gates.

This change records the implementation plan. Implementation, candidate
execution and release certification are tracked as OpenSpec tasks.

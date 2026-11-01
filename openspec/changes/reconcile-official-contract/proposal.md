# Reconcile the official competition contract

## Why

Official verifier and reference assets are now available. Replace report-derived
requirements with evidence from the exact acquired source bytes before optimizing.

## What Changes

- Pin official pages, source files, bundled paper, starter-kit metadata and backend.
- Resolve per-field conventions and document source/code disagreements explicitly.
- Preserve measured baseline gates; do not replace execution evidence with claims.
- Verify provenance rejection and independent numerical comparisons.
- Validate supplementary provenance and map disjoint official failure counters.

## Capabilities

### New Capabilities

- `contract-evidence`: source provenance, measured gate boundaries and actual
  official failure-counter mappings.

### Modified Capabilities

None; no existing OpenSpec capabilities are present.

## Impact

Contracts, source locks, documentation and contract regression tests. No upstream
competition files are changed or redistributed in tracked project files.

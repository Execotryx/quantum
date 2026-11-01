# Official asset acquisition and compatibility check

Created: 01-11-2026-22-31-15 (Asia/Qyzylorda).

## Changes and reasoning

- Inventoried the user-downloaded `vendor/competition_data.zip` and extracted
  `vendor/official/` files to establish that the missing competition inputs are
  now locally available. All 34 archive members match their extracted SHA-256
  hashes; total uncompressed size is 1,042,374,683 bytes. The original archive is
  preserved unchanged, with SHA-256
  `908ed2e587ca4ed500ddac7b6da4b473af3c8779c983d5022de620b357791a30`.
- Saved the complete local inventory in `vendor/acquisition-checks.json`.
- Acquired official metric notebook v10 into `vendor/metric/`; its bytes match
  the existing reviewed SHA-256
  `df418aff0d6eff16ec341da20150255abb49b252256d6abfb253ef8d2643ac73`.
- Established that supplied `kickmix.so` requires Linux x86-64 and Python 3.13.
  Import under Ubuntu's Python 3.14 explicitly failed with a version mismatch.
  Created an isolated Python 3.13.15 environment using the existing frozen lock
  at `vendor/linux-env/`, without changing the Windows environment or project
  dependency declarations.
- Created `vendor/backend.json` through the existing `assets pin-backend` command
  in Ubuntu WSL. Its paths are Linux paths and it is intended for WSL execution.
- Ran the unmodified official inverse-square-root verifier against the original
  reference circuit, with `--max-x 256 --shots-per-x 1 --max-workers 1` and salt
  `qcompile-bounded-smoke-2026-11-01`. The verifier reported PASS and 256 verified
  shots. Raw output is `vendor/invsqrt-bounded-smoke.json`; stderr is retained
  beside it. This establishes bounded backend execution only, not official full
  coverage, baseline normalization, or candidate/release eligibility.

## Remaining work

The historical HTTP 401 acquisition blocker has been bypassed by manual download.
G0 still requires official-contract reconciliation, complete reference evaluation,
component profiles, negative controls, and remaining source provenance. No gate
has been promoted and no optimized circuit or competition submission was created.
Full inverse-square-root reference coverage alone requires 200,540,928 trajectories;
the bounded result must not be substituted for that coverage.

## Review

Simplicity review: reused the project's acquisition, inventory and environment
commands; no new application code or dependency changes were needed.
Performance review: streamed archive hashing and bounded circuit execution avoid
loading the 886 MB DQI circuit into Python memory or launching an unprofiled full
baseline. Neither review identified a necessary application-code change.

## Validation

All 267 tests passed under Ubuntu WSL with Python 3.13.15 in 42.22 seconds,
including the exhaustive independent numerical control and acquired metric NPZ
preflight. Pytest emitted one cache-write permission warning; no test failed.
No Python or Rust source files were modified.

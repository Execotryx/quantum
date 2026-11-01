# Reproduce and profile the accepted reference baseline

## Why

Step 1 established compatibility and local reference acceptance from a dirty
development checkout. Step 2 needs clean committed source, separated costs and
resource measurements, repeatability evidence, and a frozen comparison bundle.

## What Changes

- Add opt-in observation of parsing, canonical hashing, verification and scoring
  while delegating to unchanged pinned upstream functions.
- Add a serial, preregistered three-run baseline campaign: A, A, B salts.
- Require clean committed source, a frozen dependency lock and original artifact
  hashes; preserve incomplete jobs instead of manufacturing completed results.
- Measure wall/CPU time, process-tree sampled PSS/RSS/swap, I/O counters, output
  disk use and throughput, with their measurement limits recorded explicitly.
- Freeze source, original input archive, environments, costs and raw diagnostics
  into a deterministic, hash-verified versioned reproduction bundle.

## Capabilities

### New Capabilities

- `baseline-campaign`: clean-source profiling, repeatability and frozen baseline evidence.

### Modified Capabilities

None. Existing official metric acceptance and release gates remain authoritative.

## Impact

Opt-in profiling, worker/CLI wrappers, campaign execution, tests, documentation and
ignored run/bundle artifacts. Official source files and reference bytes stay intact.

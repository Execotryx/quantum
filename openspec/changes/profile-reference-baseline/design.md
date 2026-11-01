# Design

The main checkout has a pre-existing deletion and is preserved. After testing and
committing the instrumentation, create an independent clean local clone under
ignored vendor storage. Use Linux Git metadata and a fresh uv environment pinned
by the committed lock. This avoids rewriting the existing checkout's history or
modifying its local deletion. Acquired immutable inputs remain outside the clone,
with checked aliases for contract provenance and canonical paths for artifacts.

Register three serial full-strength runs before starting: A, A, B. A is the
previous documented public local salt; B is a new fixed public local salt. These
are baseline observations, never candidate confirmation. Record actual verifier
order and cache conditions; do not claim a controlled cold-cache experiment.

Stage observation uses context wrappers around the actual metric readers and
verifier hashing/parallel-verification functions. It records inclusive wall time,
self/waited-child CPU and I/O deltas. Nested stages are not added together as if
exclusive. No sampler thread is introduced into the forking verifier worker.

An external sampler observes the verifier CLI and descendants through Linux procfs.
Record sampled proportional memory (PSS) as the shared-memory-aware footprint;
also retain summed RSS with a double-counting caveat. Record races/missing samples,
sampling interval, profiler CPU, swap, host RAM and disk capacity. Distinguish
logical I/O bytes from physical-storage counters, especially on WSL/DrvFS.

Same-salt costs must reproduce exactly. Report observed ranges for all runs and
the alternate salt; three observations do not estimate population quantiles.
Use the exact pinned score() for normalization and separately label self-controls.
Derive planning budgets from observed maxima with explicit headroom factors;
they are neither official limits nor proven minimum hardware requirements.

The frozen bundle includes only allowlisted input/source/measurement records,
the original competition archive and a Git source bundle. Check two deterministic
builds for byte equality and verify all members against the frozen manifest.
Record relocation requirements for absolute backend paths; never silently rebind
old contract hashes. Keep raw competition assets out of tracked Git files.

# Step 2: clean-source baseline campaign

Created: 02-11-2026-01-19-10 (Asia/Qyzylorda).

## Changes and purpose

Step 1 accepted the original references from a dirty development checkout. Step 2
adds a reproducible campaign from clean committed source, stage-level resource
measurements and a frozen versioned baseline for future comparisons. Existing
local history and the pre-existing `vendor/README.md` deletion are preserved.

`qcompile baseline campaign` records its source revision/tree, lock, package
versions, host CPU/RAM, allowed cores, original artifact hashes and configuration
before any run. It rejects dirty/uncommitted or wrongly imported source and uses
an independent clean local clone with its own frozen Linux Python 3.13 environment.
It never rebases, resets or autostashes the existing checkout.

The committed `configs/baseline-campaign-v1.json` preregisters three serial runs:
A1 and A2 use the previous public local development salt; B1 uses a second fixed
public local salt. All use the actual pinned metric, full-strength coverage,
unchanged reference bytes and role `official_local`. They are not confirmation
data. The per-run timeout is 3600 seconds and execution is limited to two cores.
No cache clearing is performed. Actual verifier order and cache effects remain
part of the observed environment rather than being relabeled as a cold-cache test.

## Measurement definitions

Optional `QCOMPILE_PROFILE_DIR` enables contextual observation in the existing CLI
and worker. The metric's real circuit/NPZ readers, verifier canonical hashes,
target/reference setup, parallel trajectory checks and selected scoring routines
are wrapped by delegation. Arguments, return objects, exceptions and scored
trajectories are preserved. The metric and verifier source bytes stay unchanged.

Each stage records inclusive wall time, current-process CPU, waited-child CPU and
current-process `/proc/PID/io` deltas. Direct child-stage times are subtracted for
exclusive time summaries; inclusive parent/child intervals must not be added as
independent work. Logical rchar/wchar includes cached reads and observer logging;
storage-layer counters do not necessarily describe physical Windows-host I/O on
DrvFS. I/O deltas are inclusive and current-process scoped, not invented totals
for vanished children.

An external sampler observes the verifier CLI and descendants. It adds no sampler
thread to the worker that forks simulator processes. It records process-tree PSS,
summed RSS, proportional swap, peak process count, samples by stage/benchmark,
requested and observed sample spacing, and profiler thread CPU. PSS apportions
shared pages; summed RSS double-counts them. Reads across processes are not an
atomic snapshot and short-lived events can be missed. Missing memory reads are
counted; campaigns reject more than 2% missing reads instead of treating them as
zero-valued complete evidence. These definitions follow the
[Linux kernel procfs documentation](https://docs.kernel.org/filesystems/proc.html).

The execution record's wall/CPU totals cover the verification CLI and sampler
shutdown. Post-run study analysis, integrity snapshots and bundle construction
are separate work. Retained run disk bytes are measured after stage metadata is
written. Verification throughput is actual completed trajectories divided by
observed simulation/check time. Per-stage memory peaks are sampled observations;
unobserved short stages are not assigned fabricated zero peaks.

## Evidence and analysis

Every run retains launch arguments, boot/PID identity, public seed policy, raw
stdout/stderr, exact requests/returns, stage events, resource samples, normalized
metadata and hashes of all run files. Full counters must equal the resolved
contract for all three benchmarks. Changed source, locks, backends, contracts,
salts or copied input bytes invalidate the run. Interrupted or failed execution
is retained as incomplete; it cannot be promoted because its process exited.

Same-salt reference costs must reproduce exactly. The exact pinned metric score
function supplies normalization; A1 against itself and A2 must yield 1.0. B1 is
compared against the same fixed local A1 costs. This is a local normalization
control and salt-variation study, not a private-split result. Three observations
support observed ranges, not population quantiles or worst-case guarantees.

Planning limits are derived from observed maxima using preregistered multipliers:
2x wall/CPU, 1.25x sampled PSS+swap working set, and 2x retained per-run disk use.
CPU budgets include the observer CPU. These are transparent planning margins,
not official timeouts, empirically established minimum RAM or a guarantee on
different hardware. The actual CPU model, available memory/swap and two-core
affinity are retained for interpreting those estimates.

## Frozen bundle

`qcompile baseline freeze` accepts only a completed three-run campaign. It checks
the original registration, raw run-file hashes, original input archive, committed
Git bundle and current pinned contract. The bundle includes the source Git bundle,
lock (inside the committed source), original competition archive, required official
snapshots/backend inventory, environments, profiles, costs and raw diagnostics.
Only allowlisted inputs are included; unrelated vendor files are not scanned into
the bundle. Repeated per-run submission input copies are omitted because their
exact bytes occur once in the original archive; their hashes remain preserved.

Two independent deterministic ZIP builds must be byte-identical, all members are
verified against the manifest, and the Git bundle is restored into another clean
checkout whose tree must match the recorded source tree. The bundle is a baseline
reproduction artifact, not a competition submission ZIP. It stays under ignored
release storage; tracked reports contain its digest rather than upstream data.

Absolute backend paths are recorded. Relocation needs a new backend inventory and
explicit contract review; an old contract hash is never silently reassigned.

```bash
qcompile baseline campaign --config configs/baseline-campaign-v1.json --output /absolute/path/to/runs/baseline-campaign-v1
qcompile baseline freeze --campaign /absolute/path/to/runs/baseline-campaign-v1 --output /absolute/path/to/releases/baseline-v1.zip
```

## Simplicity and performance review

Simplicity cycle 1: use standard-library observation and delegate to existing
upstream functions rather than creating a second verifier or new dependency.
Keep profiling opt-in; ordinary verification retains its existing behavior.

Simplicity cycle 2: one serial campaign owns preregistration, source/input checks
and immutable run identities. Reject incomplete coverage and stale raw records.
Use actual metric timing fields rather than zero placeholders in score details.

Performance cycle 1: sample externally to avoid added forked-worker threads;
measure shared-memory-aware PSS and profiler CPU. Stream large hashes/archives.

Performance cycle 2: keep one original input archive in the bundle rather than
three gigabytes of duplicate reference copies. Compute nested exclusive stage
times in linear time. Include sampled swap working set in memory headroom.
No further simplification or performance change is needed before execution.

## Validation and execution status

The new control tests include an actual allocated grandchild process, preserved
return/exception identities, dirty committed-source rejection, stale/incomplete
coverage/role/identity rejection and archive mutation/path controls. Full suite,
The Linux suite passed 291 tests. Pyright reported zero errors, lint and format
checks passed, and both OpenSpec changes passed strict validation before commit.
The three full-strength measured runs and final frozen-bundle audit follow that
commit; implementation/test fixtures are never substituted for those runs.

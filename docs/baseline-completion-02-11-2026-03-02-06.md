# Step 2 completion: measured and frozen reference baseline

Created: 02-11-2026-03-02-06 (Asia/Qyzylorda).

Step 2 is complete. Three serial full-strength official reference runs passed
from a clean independent Linux checkout and a fresh frozen production environment.
The [machine-readable completion audit](evidence/step2-baseline-campaign-20261102.json)
contains identities, counters, raw-file rehash results, stage/resource measurements,
normalization, budgets and excluded interrupted attempts.

## Execution identity and complete coverage

- Source revision: `4ff6c1e6080053e66459e08441a2777002c02cfa`.
- Source tree: `546cf5644423c492e7fadf84bd9a19400b181274`.
- Lock SHA-256: `4f06a31150b1944e0818a5260aedee16c28cbfd233dd0baa4f7d0ce03b657ea8`.
- Original archive SHA-256:
  `908ed2e587ca4ed500ddac7b6da4b473af3c8779c983d5022de620b357791a30`.
- Metric: exact pinned v10; Python 3.13.15; NumPy 2.3.5, SciPy 1.17.0,
  pandas 2.2.3; locked production dependencies installed with `uv sync --frozen --no-dev`.
- Host: Intel Core i7-12650H under Ubuntu WSL; affinity CPUs 0 and 1;
  BLAS/OpenMP/NumExpr worker settings limited to one thread.
- Observed execution environment: about 7.6 GiB RAM and 10 GiB swap.
  The task-created 8 GiB extra swap was deactivated and removed after completion;
  the existing 2 GiB swap remains. No persistent WSL/fstab settings changed.

Each run confirmed all required counters independently of process exit status:

| Benchmark | Completed / required per run | A1 and A2 cost | B1 cost |
|---|---:|---:|---:|
| Inverse square root | 200,540,928 / 200,540,928 | 2,076,774.233715282 | 2,076,774.233715282 |
| DQI | 102,400 / 102,400 | 24,439,461,432,712.35 | 24,439,474,367,740.598 |
| Chemistry | 254,464 / 254,464 | 3,355,599,588.3155375 | 3,355,599,588.3155375 |

All actual verifier returns report `PASS`. DQI value and phase error counts are
zero in all runs. Each run's source was clean and matched the registered revision,
lock, backend, contract, salt and original copied-reference hashes.

## Repeatability and exact normalization

The committed configuration preregistered A1/A2 with
`qcompile-public-development-salt-2026-10-30`, followed by B1 with
`qcompile-public-baseline-salt-B-2026-11-02`. Their role is `official_local`.

A1 and A2 reproduce every cost exactly. The pinned official `score()` function,
using A1 costs as the fixed local baseline and actual metric timing fields,
returns `1.0` for A1 and A2. B1 returns `0.9999998235773496`.
DQI's observed relative cost range is `5.292681379950601e-7`
(approximately 0.00005293%); the other cost ranges are zero.

| Run | CLI wall seconds | Waited CLI/descendant CPU seconds | Profiler CPU seconds | Peak sampled PSS GiB | Peak sampled PSS + swap GiB |
|---|---:|---:|---:|---:|---:|
| A1 | 1145.506 | 1863.070 | 40.248 | 6.993 | 9.006 |
| A2 | 1112.867 | 1840.650 | 38.433 | 7.008 | 8.944 |
| B1 | 800.775 | 1284.020 | 20.451 | 7.056 | 8.995 |

A1/A2 verifier order was inverse square root, DQI, chemistry; B1 order was
inverse square root, chemistry, DQI. Cache clearing was not performed. Timing
differences therefore cannot be attributed solely to salt. Three observations
establish observed ranges, not population quantiles or worst-case guarantees.

## Separate stage and resource measurements

These wall times sum exclusive nested stage records, avoiding parent/child
double counting. Per-stage self/waited-child CPU and current-process I/O deltas,
sampled PSS/RSS/swap by stage and benchmark, raw events and timestamps are retained.

| Run | Parsing seconds | Hashing seconds | Simulation/check seconds | Retained run bytes |
|---|---:|---:|---:|---:|
| A1 | 14.765 | 53.536 | 907.522 | 910,394,006 |
| A2 | 14.727 | 52.318 | 915.918 | 910,374,241 |
| B1 | 9.480 | 43.818 | 635.009 | 910,205,003 |

Copying, target setup, reference loading, scoring and remaining verifier work
are recorded separately. Full CLI timing also includes startup and adapter work;
post-run analysis, integrity snapshots and bundle construction are outside it.

The sampler recorded 2,112 / 2,035 / 1,498 observations with mean spacing
0.543 / 0.547 / 0.535 seconds versus the requested 0.5 seconds. Missing memory
reads were 0/7,282, 0/7,186 and 4/5,146 (B1: about 0.078%, below the 2% gate).
Short peaks can be missed and process reads are not atomic. PSS apportions shared
pages; summed RSS is retained separately and can double-count sharing. Stage I/O
is current-process scoped; WSL counters do not establish physical host-disk I/O.

## Measured planning budgets

The preregistered multipliers applied to observed maxima give:

| Resource | Budget | Derivation |
|---|---:|---|
| CPU affinity | 2 logical CPUs | Measured execution allocation |
| Wall time per full run | 2,292 seconds (38.2 minutes) | 2x maximum CLI wall time, rounded up |
| CPU per full run | 3,807 CPU-seconds | 2x maximum CLI/descendant plus profiler CPU, rounded up |
| Workload memory | 12,088,289,280 bytes (11.26 GiB) | 1.25x maximum sampled PSS + proportional swap |
| Retained disk per run | 1,820,788,012 bytes (1.70 GiB) | 2x maximum retained run size |

Round workload memory to at least 12 GiB for planning, with OS/service overhead
separate; the measured WSL allocation used swap to accommodate the working set.
Disk figures exclude the environment, original assets, source checkout, bundle
copies and temporary swap storage. Budgets are local planning reserves, not
official limits, proven minimum hardware, or guarantees on other systems.

The first attempt was killed by the Linux OOM killer. Two retries inherited a
stale `init.scope` OOM/deactivating state; resetting the idle VM cleared it.
Those attempts are retained as incomplete and excluded from acceptance and
repeatability results. See the [runtime recovery log](baseline-runtime-recovery-02-11-2026-02-05-36.md).

## Frozen evidence and completion audit

Version: `baseline-v1-20261102`. Local artifact:
`releases/baseline-v1/baseline-v1.zip` (130,899,391 bytes; 91 members).
SHA-256:
`d9e58a24e40117a2024920547204a636ce90247a06c75a7b5398b17141760e53`.

Two separately constructed archives are byte-identical. Every member was
stream-rehashed in both archives, and the Git source bundle restored to the
registered clean tree. The final audit separately rehashed all 38 files in each
of three run directories, checked copied reference bytes, recomputed official
normalization/budgets, and repeated bundle/source-restore checks.

| Step-2 objective | Authoritative evidence | Result |
|---|---|---|
| Clean locked full reference acceptance | Three complete verification reports, actual `PASS` returns, clean source/lock identity | Passed |
| Complete counters and normalization | Exact required counts above; official score controls A1=A2=1.0 | Passed |
| Separate parsing/hashing/simulation and resources | Stage events, exclusive wall/CPU summaries, process-tree samples, I/O and retained disk | Passed |
| Same/alternate-salt acceptance, cost and runtime repeatability | Registered A,A,B sequence; identical A costs; reported B differences and measured ranges | Passed |
| Measured hardware and verification budgets | Host inventory, observed peaks and fixed headroom calculations | Passed |
| Versioned frozen inputs/results/environment/diagnostics | Original input ZIP, source Git bundle, raw campaign records, 91-member manifest, matching builds and clean restore | Passed |

Raw campaign data is under `runs/baseline-campaign-v1-retry3`; acquired assets and
local archives remain ignored by Git. Original reference bytes occur once in the
bundle's input archive; omitted per-run input duplicates remain bound by hashes.
Absolute backend paths are recorded. Relocation requires explicit backend/contract
review rather than silently changing the recorded identities.

Validation: the Linux suite passed 291 tests before execution-source commit;
Pyright for all six changed source/test Python files, lint/format, strict OpenSpec
validation and diff checks passed. Full-strength campaign, freeze, and completion
audit then passed against actual official assets. This baseline is ready for
subsequent experiments; optimized circuit acceptance, candidate confirmation and
remote competition acceptance remain outside step 2.

Simplicity review: one compact audit links to retained raw evidence; no resume
semantics or new acceptance exceptions were added for the interrupted attempts.
Performance review: archives stream their contents and store the original input
ZIP once; profiling stays outside the forking worker. No additional implementation
change was needed after these reviews.

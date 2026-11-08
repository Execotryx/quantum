# Profiled chemistry fit-grid registration

Profiled one full-size joint objective and gradient for each registered shape
against the pinned factorization and native tensor reconstruction. Each used
one OpenBLAS and OMP thread. The table gives one local timing sample and the
process peak RSS for the full profile, including input loading and tensor
comparison; it is not a steady-state memory guarantee.

| Shape | Objective and gradient | Process peak RSS |
| --- | ---: | ---: |
| `(9,143,40)` | 0.583 s | 1,058,168 KiB |
| `(9,129,40)` | 0.506 s | 1,052,096 KiB |
| `(10,129,40)` | 0.698 s | 1,062,396 KiB |
| `(8,120,40)` | 0.415 s | 1,037,344 KiB |

The [profile receipts](evidence/chem-grid-profiles-20261108/) bind the measured
factorization, official backend, computational source hashes and profile
plans. They agreed with pinned tensor residuals to floating-point precision.
The profile wrapper was subsequently hardened to detect plan or wrapper
mutation; the recorded computational runner and factorization modules did not
change during the measurements.

Each shape's I1, both seeded I2 starts, I3, and seeded I4 control were ranked
before optimization. The [ranking receipts and external resource samples](evidence/chem-grid-rank-20261108/)
record separate initializers, scores, initial continuous residuals and hashes.
The projection scores are factor-space diagnostics, not tensor-residual lower
bounds. I1 ranked first by that score for all four shapes, while I3 had the
lowest initial tensor residual for all four; neither ordering rejects a shape.

| Shape | Ranking compute | Sampled peak PSS | Sampled summed RSS |
| --- | ---: | ---: | ---: |
| `(9,143,40)` | 42.15 s | 1,040,005,120 B | 1,066,139,648 B |
| `(9,129,40)` | 37.67 s | 1,028,644,864 B | 1,053,876,224 B |
| `(10,129,40)` | 37.21 s | 988,767,232 B | 1,013,866,496 B |
| `(8,120,40)` | 33.32 s | 978,130,944 B | 1,005,031,424 B |

An external process-tree sampler ran at one-second intervals; PSS apportions
shared pages, summed RSS can double-count them, and samples can miss short
peaks or racing processes. The recorded ranking times exclude earlier input
loading. WSL memory availability was checked before continuing the serial
runs. The supervisor wrapper was subsequently hardened to record its own and
the sampler implementation's hashes for future attempts; the sampled process
records here remain separate and unchanged.

The [ready 24-lane manifest and plans](evidence/chem-grid-manifest-ready-20261108/)
bind the profile, ranking, factorization and per-lane plan hashes. Each lane
registers at most 20,000 evaluations and 18,000 seconds; these are upper
budgets informed by sparse local samples, not a completion-time guarantee.
The fit runner's elapsed check is cooperative; a hard deadline requires an
external process-tree supervisor.
The two seed labels on I1 and I3 are deterministic repeated executions, not
independent starts; I2 uses seeds 184 and 185. The original reference-shape
continuation and I4 on a selected best shape remain separate controls, requiring
their own registration and, for the full reference-shape fit, its own profile.

The 20 generated initializer NPZ files, totaling 21,807,720 bytes, remain in
ignored `runs/chem-grid-rank-attempt-20261108/`; their hashes are in the
compact ranking receipts. The ready-manifest validation references those
local arrays, so regenerating it requires restoring those exact files. The
small receipts, sampled records, 24 generated plans, and manifest are retained
under `docs/evidence/`. The fit runner recomputes the initializer rather than
loading those saved ranking arrays, so the hashes are diagnostic and not a
guarantee of bitwise identity across environments. No 24-lane fit grid,
eligible S1 factorization, S2/S3 result, or chemistry promotion follows from
these registrations.

# Bounded chemistry grid supervisor

Added `tools/chem_grid_run.py` as a separate supervisor for the validated
24-lane chemistry manifest. It reconstructs the manifest from its pinned
profile, ranking and initializer evidence, checks every generated lane-plan
hash, and requires an explicit subset of lane IDs and limits on concurrent
workers, launches per session, worker wall time and session wall time. A
read-only `dry-run` lists the next bounded subset; when given an existing
result directory it also checks completed-lane hashes before listing remaining
lanes. The tested real-manifest dry run listed one lane and started no fit.

`run CONFIG OUTPUT` creates a fresh result directory. `resume CONFIG OUTPUT`
uses the same immutable configuration and source hashes, verifies every file
of each completed attempt and its terminal checkpoint against the S1 decision,
then skips only those validated completions. Failed, timed-out or interrupted
attempts remain separate and can be retried in a new numbered attempt. Each
session has a separate terminal receipt and reports remaining lanes; execution
status is not aggregate chemistry acceptance. A lock prevents simultaneous
writers to the same result directory.

Workers use one BLAS thread each and an external process-tree sampler. The
supervisor applies worker and session deadlines and records sampled PSS and
summed RSS separately. Sampling may miss short peaks or racing processes; it
is not a memory cap. Deadlines bound active workers; sampling shutdown and
receipt hashing can add cleanup time. Termination follows the observed process
tree and is not a guarantee for a deliberately detached descendant. The S1
worker still owns its scientific outcomes and the 19 mHa gate.

The configuration JSON contains `manifest` and `manifest_plan` objects with
`path` and `sha256`, a `lane_plan_directory`, an explicit `lanes` array, and
`limits` containing `max_workers` (1–4), `max_lanes_per_session`,
`worker_seconds`, and `session_seconds`. It requires the ranking initializer
arrays under ignored `runs/chem-grid-rank-attempt-20261108/` to revalidate
the published manifest. Use `python tools/chem_grid_run.py dry-run CONFIG`
before authorizing a run; no long grid was launched in this change.

Small Linux subprocess fixtures tested bounded concurrency, dry-run, timeout,
launch failure receipts, failed-attempt isolation, hash-verified resume and
tamper rejection. Frozen
Ubuntu Pyright, Ruff and the real-manifest dry run passed. These fixtures do
not establish any fit result or release readiness.

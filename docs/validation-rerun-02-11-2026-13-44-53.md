# Steps 1–3 validation rerun

Created 02-11-2026-13-44-53 in Asia/Qyzylorda.

The requested rerun uses a separate checkout of the committed README cleanup
and validation tools, a fresh frozen Python 3.13 environment, original pinned
assets, and new result directories. Earlier evidence remains available for
comparison. WSL initially reported 7.6 GiB RAM and 2 GiB swap, with zero OOM
events. The run adds a temporary 8 GiB swap file for measured headroom and
removes it after execution.

The first setup attempt stopped at Git's ownership check before validation.
The retry uses process-local safe-directory entries restricted to the source
and restore paths. No global Git configuration was changed.

The serial sequence checks the original archive and every extracted file,
validates the contract, executes the full A,A,B campaign and baseline freeze,
reruns each step-3 differential/control tool and the full test suite, and freezes
the new step-3 evidence. Every execution retains separate stdout and stderr.

The live job directory is `runs/rerun-steps-20261102-retry1`. Its `progress.json`,
`completion.json`, or `failure.json` records the actual state. Completion is
pending at creation of this entry.

Simplicity review kept the existing entry points and isolated their hard-coded
output paths by using a separate checkout. Performance review streamed archive
hashes and reused the dependency download cache while creating a fresh environment.
Pyright passed for the orchestration script after its final changes.

## Completion

All three steps passed. The new results are summarized in
[the rerun evidence](evidence/steps1-3-rerun-20261102.json).

- Step 1 rechecked the original archive and all 34 extracted assets. Contract
  validation returned ready with zero blockers.
- Step 2 completed A1, A2 and B1 at full strength. Every run completed 200,540,928
  inverse-square-root, 102,400 DQI and 254,464 chemistry trajectories. Every cost
  dictionary matches its corresponding earlier run exactly. A1/A2 normalize to
  1.0 and B1 to 0.9999998235773496.
- Fresh full-run wall times were 737.515, 719.353 and 786.112 seconds. The new
  measured planning reserves are 1,573 wall seconds, 2,591 CPU-seconds on two
  logical CPUs, 11,996,529,920 workload-memory bytes including proportional swap,
  and 1,820,376,322 retained disk bytes per run.
- Step 3 reran every differential, primitive, structure, cost, representation,
  boundary and rejection control. All 291 tests passed in 26.68 seconds with
  zero skips, failures or errors. The fresh evidence audit passed G0 and G1.
- Both independent builds of each evidence archive are byte-identical. All
  members were verified, and both source bundles restored to clean checkouts.

The rerun used source revision `cc828f9a87ee5751602684c5780c678915deab49` and
the committed dependency lock in a fresh Python 3.13.15 environment. WSL continued
to expose 7.6 GiB RAM. The temporary 8 GiB swap file supplied a total of 10 GiB
swap during execution. It was deactivated and removed after successful completion,
and the original 2 GiB swap remained active. Kernel OOM counters were zero on
the final check.

Fresh local artifacts under `vendor/rerun-source-20261102-retry1/` are
`releases/baseline-v1/baseline-v1.zip` and
`releases/step3-validation-v1/validation.zip`.

Their SHA-256 digests are respectively
`b1da1f4068cd00265014308a3488329a7a38a16883d309b5591ed99f52a097fe` and
`dade7adcb99c5da69a4c41b2a0feab00622d15c6a367ff690014dc65361c6578`.

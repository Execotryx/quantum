# Chemistry polish recovery

The cloud lane completed all 400 sweeps before its polish entered the final
part of the VM window. A fresh attempt can use that complete series through
`--sweeps-from`. The runner checks all 41 checkpoint hashes, the registered
lane and its exact start, then independently recomputes the selected
checkpoint residual on the pinned target. It starts a fresh optimizer with
the original 3,000-evaluation limit and writes a separate attempt. The
original interrupted run remains available for inspection.

The cloud regression, Pyright and Ruff passed. The recovery reader
verified all 41 saved checkpoints from lane A and selected sweep 0 at
41.574942376071344 mHa. The new polish retains the original stopping
criteria and requires its own terminal receipt.

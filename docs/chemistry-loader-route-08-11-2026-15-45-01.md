# Registered chemistry loader ranking route

Added `tools/chem_loader_rank.py` to rank banked ANGLE batch widths for either
the pinned reference control or a terminal-selected S3 passing handoff. It
authenticates the relevant factorization, word table, and S3 receipt bytes;
reference mode requires the established reference hashes and tree. It reruns
the official decoded metrics, checks the project margins and compares them
with the input receipt before constructing any loader family.

The worker evaluates every J from 3 through the 128-qubit cap using the pinned
native forward/reverse verifier and the pinned complete resource-cost model.
Each completed J has a separate trial receipt. It independently rebuilds the
best family twice, compares serialized circuit hashes, and exercises arbitrary
nonzero target words across the full binary address space, including padding,
with selection, phase and workspace checks. The source factorization is
retained once and unchanged. The supervisor records timeout or worker failure
separately from scientific results.

The reference-control plan is `tools/chem-loader-reference-control.json`; run
`python tools/chem_loader_rank.py run PLAN OUTPUT` from a frozen Ubuntu
checkout with a fresh output directory. It registers two shots per valid
address and a one-hour hard supervisor deadline, and is a development run,
not full 64-shot chemistry verification. A future S3 plan supplies the same
factorization and words entries plus pinned `s3_registration`, `s3_decision`,
and `s3_result` entries and `mode: s3`.

Synthetic native fixtures cover both input gates, actual serialized duplicate
builds, all-address nonzero composition and word mutations. No full-size
reference ranking was started in this lane. A successful ranking alone does
not establish the complete chemistry metric, a fresh confirmation, promotion,
or acceptance of a paired archive.

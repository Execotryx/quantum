# Disposable feed-carry source ledger

Copyright 2026 Syed Asad Ali. Apache-2.0. Credits Opus and Astra.

The complete arithmetic source replay saves6.5E atQ48 and19.5E atQ47. AtQ49 throughQ52 it is cost-neutral, so this adaptation is closed as a Q49 cost improvement. These are source-counter results, not native measurements or a complete lower-width circuit.

| Q | Baseline core E | Disposable core E | Saving E | New peak |
|---:|---:|---:|---:|---:|
|47|632.0|612.5|19.5|47|
|48|594.0|587.5|6.5|48|
|49|577.5|577.5|0.0|49|
|50|568.0|568.0|0.0|50|
|51|559.0|559.0|0.0|51|
|52|550.5|550.5|0.0|52|

Every cap includes270E forward computation, the direct triangular u12 initializer and its cleanup. All24 CarryDebt records are consumed once; all recorded carry phases are repaid; every classical bit is freed. All24 inverse owner transitions are checked. The first13 product owners return to their original physical owners, and u12 cleanup explicitly returns the final two current owners. Final ownership is31 qubits.

Entry is root12+product15+flags4=31. Initial remainder allocation reaches45, then two product inputs are consumed and43 remain. An inverse feed row adds one carry, reaching44 before adder helpers. The existing inverse_add interface releases it after the first retained segment, regenerates it under a boundary-measurement condition, pays that phase and erases the regenerated carry. The caller skips its old final erase when released_input is true.

All13 conditional regenerations cost0.5 expected CCX each, totaling6.5E; this is included in every new core price. The exact _feed_erase pays its quadratic HMR sign using Clifford gates. Its controls v0,low,cur,sign lie outside source/target. Any terminal dirty use restores cur/sign before regeneration. No outcome is dropped or counted twice.

AtQ48, a13-bit inverse feed row changes from16E with dirty-terminal partition[4,3,2,1,3] to15.5E with ordinary terminal partition[1,4,3,2,1,2]. AtQ47 it changes18.5→17E while retaining a smaller dirty terminal. These row prices exclude the unchanged initial one-CCX preparation and include the conditional regeneration. AtQ49+ its cost offsets the arithmetic saving.

The old inverse_policy_paper comparison concerned alternative terminal choice in the earlier driven/table-initialized divider; it did not expose this candidate's feed carry lifecycle. Its scoped negative result is not contradicted.

The unchanged endpoint source still fails helper allocation atQ47/Q48. AtQ49+ it remains146 Toffolis,4T and34 rotations. A lower-width composition must separately bind its compact endpoint, both loaders and all other owners. No completeQ48 gate is claimed here.

SOURCE_PINS.json records a fresh checkpoint002 archive digest and byte comparisons for110 extracted engine files, plus nine current source pins. The run took0.84seconds and about22MiB RSS under a10-second alarm and512MiB AS cap. It creates no native builder, KMB or simulator. New native all-transcript proof remains mandatory before adopting the callbacks. study.json contains every row and owner transition; cleanup_disposable_source.py contains the exact source adaptation.

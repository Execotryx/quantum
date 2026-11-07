# Hybrid confirmation and release lineage

The release store now reserves separate confirmations for generated
benchmarks and binds them to complete component hashes. This lets a new
inverse-square-root circuit carry forward the parent chemistry family,
including the matching reference NPZ, without registering chemistry a
second time. Older single-benchmark records retain their semantics.

The historical parent audit checks its archive, pinned source inputs,
canonical component identities and independent raw receipts. The release
runner rebuilds the parent twice and checks the original ZIP hash before
running the full metric. The direct-phasing successor runner builds twice
from a separate generator and verifies that only `invsqrt.kmb` changes.

The reduced successor metric reached 256 DQI trajectories with zero observed
errors, but the pinned verifier's upper bound was 0.2929 against a limit of
1/16. Hybrid selection accepts the stronger, exact-coverage full metric at
that transition and preserves the failed reduced run separately. The
verifier and its confidence procedure remain pinned.

# Shape-generic ANGLE loader groundwork

Added a generic banked XOR-loader family without modifying the historical J9
control. It validates the table, bank split and 128-qubit circuit cap before
construction. Batch candidates are ranked using the pinned verifier's complete
resource model and native forward-and-reverse Toffoli counts, including live
word width. This is preparation for a future eligible factorization.

The pinned address-domain evidence was already recorded in
`contracts/contract.json`, field `chemistry.unused_address_behavior`: the
hashed `dfthcsos/scoreinfra/circuits.py` function
`recover_words_from_circuits` tiles `np.arange(num_vectors)` and checks every
such address, but does not simulate binary addresses beyond that range.
Padding of unused angle slots is still checked. The generic loader itself
also produces zero on its synthetic padded address range.

The independent [synthetic ranking](evidence/chem-loader-synthetic-20261108/synthetic-ranking.json)
uses 82 rows, four-bit words, a 75-angle table, an assumed lambda of 48, and
two shots per address. It covers every batch from 3 to the modeled cap of 29;
batch 19 ranks first for this synthetic table and shape. Native tests exercised
all addresses including padding, arbitrary nonzero target words, both
directions, phase and workspace checks, and bit/order mutation detection.
These results are not an eligible factorization, production loader ranking,
full coverage, or chemistry acceptance.

A [repeat after import cleanup](evidence/chem-loader-synthetic-refined-20261108/synthetic-ranking.json)
retains a separate source-hashed receipt and reproduces the ranking.

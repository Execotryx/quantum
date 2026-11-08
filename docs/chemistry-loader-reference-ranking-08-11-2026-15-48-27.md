# Registered chemistry loader reference ranking

The new loader route ranked all seven batches from J3 through J9 on the
pinned 12-bit reference factorization and the recovered angle table.
The pinned native word recovery checked 7,952 trajectories per batch.
J9 won at a modeled complete cost of 3,250,386,325.02 and used the
128-qubit ANGLE cap. It is 0.081% above the incumbent's full measured
cost of 3,247,752,448.67. This comparison pairs a modeled development
cost with the existing measured control, so the incumbent remains selected.

Two separately emitted J9 families agreed byte for byte with each other.
Their nonzero-output checks each covered all 4,096 binary addresses,
including 120 padding addresses, with phase and workspace restoration.
The nine circuits differ from the existing banked family. The NPZ
matches the retained factorization hash exactly.

The external sampler observed 1.10 GiB peak process-tree PSS with no
swap PSS across 89 samples. The terminal record and seven individual
trials are retained. A compressed S3 handoff and full chemistry
confirmation remain separate acceptance gates.

[Ranking](evidence/chem-loader-reference-20261108/ranking.json) ·
[Registration](evidence/chem-loader-reference-20261108/registration.json) ·
[Resource sample](evidence/chem-loader-reference-20261108/resources.json)

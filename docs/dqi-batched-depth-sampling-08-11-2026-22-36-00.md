# Batched DQI depth sampling

The first cloud window used the scalar routed recurrence and preserved its
completed chunk receipts. The batched runner keeps the pinned verifier sampler,
the same 100 seeds and 100,000 draws per seed, and the same degree and history
gates. It groups independent recurrences to avoid per-symbol Python dispatch.
The first degree violation remains ordered by shot and then round.

The batched implementation changes a source pin and therefore requires a
fresh probe and separate campaign registration. Its adoption gate compares
the recurrence with the scalar oracle and compares sample hashes and exact
statistics against the completed scalar chunks. The scalar receipts stay
under their original registration.

Cloud Pyright, Ruff and three tests passed. The batch runner reproduced
both archived 100,000-shot chunks exactly, including the original draw
hashes, per-round degree maxima and retained-discrepancy histograms. The
two batched replays took 39.74 and 36.30 seconds on the loaded VM. The
scalar attempts ran in an earlier window under different concurrent load.

[Exact chunk comparison](evidence/review-fixes-cloud-20261108/dqi-depth-batched-parity.json)

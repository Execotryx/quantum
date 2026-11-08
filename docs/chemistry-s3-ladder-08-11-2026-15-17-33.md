# Gated decoded precision ladder

Added a separate `tools/chem_s3.py` command. Its plan binds the reference
factorization and the S2 registration, terminal decision, selected checkpoint
receipt, continuous arrays, strict NPZ and decoded words by SHA-256. It
requires the terminal best eligible checkpoint and independently reruns both
the continuous residual and all decoded project margins against the pinned
target and evaluator. A capped S2 run is not sufficient by itself: it needs
an exact-metric eligible checkpoint explicitly selected by its terminal record.

For each precision 12, 11, 10, 9 and 8, the worker encodes and reconstructs
the two-body vectors through the registered tree, refits all two-body weights
with those decoded vectors fixed, regenerates the one-body words, and runs the
pinned exact metrics. It keeps the identity offsets fixed, records each step's
bounded refit trace and metrics, and emits a strict NPZ and words only for a
passing step. The first failed step stops descent and preserves the last
passing precision. A capped, unconverged failing refit is `budget_limited`;
another unconverged failure is `inconclusive`. Neither establishes that the
precision is impossible. Expected coverage is
derived as `(N + R*B) * 64` for each result.

The supervised CLI takes `run PLAN OUTPUT`; the plan contains `{path, sha256}`
entries for `factorization`, `s2_registration`, `s2_decision`,
`s2_checkpoint_receipt`, `s2_continuous`, `s2_submission`, and `s2_words`,
plus `target_sha256` and `limits` (`evaluations_per_step`, at most 5000, and
`wall_seconds`). The process-tree supervisor provides the hard wall limit;
execution status is separate from the ladder's scientific decision. Output
must be fresh and separate from the S2 run.

Synthetic tests exercise exact-margin rejection, all-weight fitting, a capped
failure, first-failure stopping, source-hash rejection, and a complete mocked
worker with pinned decoding math. No eligible real S2 checkpoint exists, so
no real ladder, loader family, coverage confirmation or release claim has
been produced.

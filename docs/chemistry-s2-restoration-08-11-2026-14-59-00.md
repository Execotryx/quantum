# S2 identity-offset restoration and checkpoint groundwork

For fixed basis vectors and factor weights, the pinned energy gap is a constant
plus the trace norm minus the trace of an affine symmetric matrix, plus half
the squared identity-offset norm. The resulting function is convex in those
offsets. Added a box-bounded search using a smoothed trace-norm derivative;
proposed admission points are checked by the supplied exact evaluator. When
the minimum gap is below the registered target, a bounded segment search can
find a point within the gap and Lambda margins. A capped or failed search is
inconclusive and does not prove a shape or offset box infeasible.

Added bounded augmented-objective orchestration that requires an S1 `go` and
independently recomputes its continuous residual at the 19.0 mHa limit. It
rejects weaker project margins, records exact metrics at checkpoints, and
records the relative difference from the smoothed objective. The pinned
checkpoint helper regenerates decoded one-body words before evaluation. A
fresh development checkpoint writer stores uniquely numbered arrays with
SHA-256 receipts; the format is not a release NPZ. Elapsed limits are
cooperative and an external process-tree deadline is required for hard
preemption.

Synthetic tests cover rejected capped/forged S1 decisions, successful offset
restoration, rejected Lambda floors, inconclusive search, hashed persistence,
and checkpoint regeneration against pinned evaluator math. They do not
establish a production CLI, an eligible chemistry factorization, an S2 gain,
quantization-ladder readiness, or release acceptance. No short S1 pilot was
admitted to S2.

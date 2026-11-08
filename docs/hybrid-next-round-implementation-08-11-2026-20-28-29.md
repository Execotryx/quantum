# Hybrid next-round implementation

Imported the five supplied OpenSpec changes and their archive index. This pass
covers their specified code paths. Runtime tests, experiments, calibration and
release actions are pending.

- Inverse square root uses an opt-in sibling CNOT in both the coefficient
  lookup and the measurement repair walk. Protocol 6 starts with the frozen
  trimmed v5 control and requires two matching builds per lane, agreement
  between modeled and native costs, the registered coverage and the specified
  cost and width limits. Earlier formats retain the existing gate sequence.
- DQI has a scaled in-place evaluator and its adjoint. The supplied-locator
  tool exposes it through `--inplace-evaluator` and restores the syndrome prefix
  after the scan. The full routed decoder still needs a decision on the
  zero-discrepancy counter and a reversible overflow contract. History depth
  remains pending the registered sampling campaign.
- Chemistry can register the four alternating-projection lanes, retain their
  best checkpoints, polish within the evaluation cap and decode only after the
  continuous gate. Selection binds each terminal receipt. If different shapes
  pass, selection requires complete projected costs. The supplied rank table
  records preparation rotation cost only.
- Compressed chemistry plan preparation binds the eligible handoff and the
  existing target pin, S2 and S3 receipts. The plan writer takes the registered
  S2 offset bound and penalty explicitly. A passing S3 receipt is required to
  prepare loader ranking. Full verification and paired archive promotion depend
  on those measured results.

The release sequence is a procedural specification. This pass adds no release
orchestration or release evidence.

Pyright with the pinned Ubuntu interpreter, Ruff, and the Git whitespace check
passed. Strict OpenSpec validation and runtime testing are deferred.

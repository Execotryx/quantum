# OpenSpec review fixes

Imported the four review changes and the revisions to the previous OpenSpecs
from the supplied review archive.

- DQI now has a classical circular round model, a frozen-state generator,
  a full-width native round wrapper and a routed decoder emitter. A zero
  discrepancy increments the counter, including when the wrapped template
  word is nonzero.
- The history stack retains a persistent transfer word and overflow count.
  Reverse pops require a zero overflow count because a dirty transfer word
  on a failed input cannot clear the original pop selector reliably. The
  count remains visible to the verifier. The emitter requires a successful
  freed-nonzero probe and a complete registered 100-chunk depth campaign.
  The probe embeds the two active wires in the minimal verifier register
  layout. The depth runner keeps one full sampler allocation live at a time
  while recurrence workers process their chunks independently.
- Chemistry now derives the initial S2 offset bound from the pinned reference
  and fixes the penalty at 1.0. The plan binds the selected arrays, checkpoint,
  decision, target and settings. The supervisor reserves each primary plan
  once and allows a single bound-doubling contingency. A second active bound
  ends the handoff as budget-limited.
- Shape selection restores offsets for each passing lane, prices all native
  8-bit loader splits and batches with the pinned complete resource function,
  and applies the projected-cost, decoded-residual and lane-letter tie rule.
  The projection mode supplies selection evidence ahead of the separate S3
  accuracy gate.

Runtime checks, fixture generation, depth sampling, chemistry fits, strict
OpenSpec validation and release operations are deferred.

Pyright with the pinned Ubuntu interpreter, Ruff, and the Git whitespace
check passed.

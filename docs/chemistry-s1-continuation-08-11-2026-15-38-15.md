# Hash-bound continuation of the I3 fit

The `(9,143,40)` I3 fit reached 81.3991 mHa after 1500 evaluations and was
still improving, but did not pass the 19 mHa S1 gate. Added a distinct
`I3-resume` initializer that checks the registered parent registration,
terminal budget-limited decision, checkpoint receipt and checkpoint bytes;
it also hashes the reconstructed shifted target and independently rechecks
the parent residual. The original evidence is not modified.

The [two-evaluation smoke](evidence/chem-s1-resume-smoke-20261108/) reproduced
the parent's 0.08139909840093204 Ha residual and ended `budget_limited` at
the same value. This is a new L-BFGS optimization with reset optimizer state,
not a bitwise continuation of the original trajectory. Focused tests, Pyright
and Ruff passed. The separate 5000-evaluation plan is registered in
`tools/chem-s1-resume-5000.json`; it needs a fresh output and an external
process-tree supervisor for a hard wall-time limit. Neither the smoke nor its
parent authorizes S2, S3, or chemistry promotion.

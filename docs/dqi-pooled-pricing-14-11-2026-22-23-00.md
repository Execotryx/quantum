# Pooled pricing for public DQI candidates

The public DQI screen prices the one-sided 95% Poisson upper bound on
the pooled error count. It divides the bound by the number of salts,
rounds up to whole failures and applies the official scoring procedure
to a 102,400-shot run.

Both this rule and the existing routed DQI rule use the same receipt
checks for full coverage, disjoint error counts, verifier confidence
and gate cost. The routed rule retains its original worst-salt-plus-two
calculation. Tests cover the four examples in the public-candidate
specification.

The two-stage runner freezes the candidate build receipts, backend and
eight salts before running the pinned verifier. It preserves each
candidate's individual result and ranks the passing candidates before
spending the six finalist draws. A confidence rejection retains the
verifier's disjoint error counts.

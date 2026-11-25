# D4 full-grid prototype

The new builder wires pole-aware extraction, a coherent tail solve,
synthesis, and explicit residue evaluation over all 4,095 points.
Regular charts recover the weight-35 tail coefficients using the leading
two numerator equations and the derivative jet. Mixed charts try a
one-sided linear seed. The builder retains a rejection bit when the
trial pair has the wrong degree, zero denominator, or fails the original
moment congruence. It keeps a separate counter for repeated scan roots
where the first derivative cannot recover the residue.

The moment certificate uses the polynomial part of `P*S` for the
original moment series `S` and node polynomial `P`. It evaluates
`N + Q*D` modulo `P` by checking both `X²` and `P/X²`. This lets
the native product accumulate with an invertible shift and clean it back
up without saving intermediate polynomials. The portable check accepted
all eight prior native coefficient pairs and rejected a one-coefficient
mutation in each.

The full cloud driver requires matching independent builds and a replay
of all four captured batches before creating the eight new salts. It
retains per-role receipts and resumes only after checking each receipt's
registration, salt, circuit and coverage.

Ruff, strict OpenSpec validation, Windows Pyright, and seven portable
tests passed. Automatic approval review did not run the Ubuntu command
because its usage limit was reached. The native tail solver, certificate,
full-grid emission, matched gate and cloud campaign remain unverified.

[Prototype builder](../tools/dqi_repaired_candidate.py) ·
[Campaign driver](../tools/dqi_repair_campaign.py) ·
[OpenSpec checklist](../openspec/changes/repair-d4-extraction-poles/tasks.md)

## 1. Lanes

- [ ] 1.1 Run lanes A–D as registered. Record best checkpoints, continuous residuals and 12-bit decoded residuals.
- [ ] 1.2 Apply the qualification table. Stop if no lane qualifies.

## 2. Projection mode

- [ ] 2.1 Add `projection` mode to `tools/chem_loader_rank.py`: inputs are the words, tree, factorization NPZ and `λ_proj`. Native verification and `rank_complete_cost` are unchanged.
- [ ] 2.2 Test that the mode reproduces the reference-mode ranking when given the reference words and `λ_eff`.

## 3. Projected costs

- [ ] 3.1 For each qualifying lane, run one restoration with the preregistered settings and record `λ_proj` or the reason for exclusion.
- [ ] 3.2 Encode 8-bit words and run projection mode for `low_bits ∈ {4, 5, 6}`. Record every `(low_bits, J)` row.
- [ ] 3.3 Record each lane's minimum projected cost with its breakdown.

## 4. Selection

- [ ] 4.1 Apply the selection and tie rules. Write the selected lane's S1 `go` decision.
- [ ] 4.2 Hand off to plan binding and `promote-compressed-chemistry`.
- [ ] 4.3 Strict OpenSpec validation and a dated change log.

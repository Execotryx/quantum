## 1. Method

- [ ] 1.1 Implement `fit_alternating(target, vectors, weights, sweeps, record_every)` in `factorization.py` with the three steps of one sweep.
- [ ] 1.2 Unit tests on the eight-orbital synthetic instance:
  - each weight step does not increase the surrogate;
  - each vector step does not increase the surrogate;
  - the Procrustes step does not increase `‖X − QY‖`;
  - a planted exact factorization is recovered to `1e-8`.
- [ ] 1.3 Profile one full-size sweep at `(9, 143, 40)` with one BLAS thread. Record time and peak RSS.

## 2. Runner

- [ ] 2.1 Add `tools/chem_alternating.py` with the four fixed lane plans, checkpointing every 10 sweeps, and the polish stage.
- [ ] 2.2 Bind lane A's start arrays by recorded SHA-256, or record the regeneration fallback.

## 3. Runs

- [ ] 3.1 Run lanes A–D in parallel, one BLAS thread each. Record traces, best checkpoints and terminal records.
- [ ] 3.2 Compute both residuals for every lane's best checkpoint with the pinned evaluator.

## 4. Decision

- [ ] 4.1 Apply the gates and selection rule. Record the decision with all lane hashes.
- [ ] 4.2 Export the selected factorization to `promote-compressed-chemistry`, or record that no lane passed.
- [ ] 4.3 WSL tests, Ruff, Pyright, strict OpenSpec validation and a dated change log.

## 1. Input

- [ ] 1.1 Bind the handed-off factorization and its fit records by SHA-256. Write the S1 `go` decision in the `chem_s2.py` schema.
- [ ] 1.2 Compute and record the target pin.

## 2. S2

- [ ] 2.1 Register the S2 plan with the fixed limits and run it once.
- [ ] 2.2 Record the terminal decision. Stop the change if no checkpoint is eligible.

## 3. S3

- [ ] 3.1 Register the S3 plan from the S2 best checkpoint with the fixed limits and run it once.
- [ ] 3.2 Record the passing precision and its words.

## 4. Loader

- [ ] 4.1 Register the S3-mode loader plan and run it once.
- [ ] 4.2 Record the selected batch and both identical rebuilds.

## 5. Verification and archive

- [ ] 5.1 Two identical builds of the ANGLE family and NPZ.
- [ ] 5.2 Complete chemistry metric at full coverage and a fresh one-use confirmation.
- [ ] 5.3 Paired archive with the current inverse-square-root and DQI members. Run preflight and the drift gate.
- [ ] 5.4 Apply the 1.624×10⁹ gate and hand the archive to `sequence-hybrid-releases`.
- [ ] 5.5 Strict OpenSpec validation and a dated change log.

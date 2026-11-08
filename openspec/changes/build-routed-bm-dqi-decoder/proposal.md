## Why

DQI is still the pinned reference at 1.0× and is the largest remaining
lever. Every 2× on DQI multiplies the aggregate by 1.26. The tower-field
substitution showed that faster products alone do not move it: the
synchronized Euclidean schedule and the scan dominate.

Gu et al. (arXiv:2610.22367, SI I.1) replaced the locator with a
Berlekamp–Massey (BM) solver that routes both branches through one shared
multiply-subtract. They replaced the Forney scan with a phase-only test
that costs 23 Toffolis per position. Their decoder needs about 440,000
Toffolis at 1,837 qubits, against 5.1 million at 1,938 for their
reimplementation of the reference.

Their contract differs from this one. The pinned verifier uses field
polynomial `0x1053` and a fresh classical mask per shot, and this project
requires an exact decoder before any approximation. The plan therefore
rebuilds the method independently under the pinned contract: exact
first, approximate second.

## What Changes

- Arithmetic: a rank-minimal tower product (target 45 Toffoli-like gates,
  measured 54 today), measurement-based erasure of product registers with
  Clifford fix-ups, a norm-based inverse (target at most 110, measured 180).
- Locator: an exact routed BM solver with full reversal history, emitted
  as unrolled rounds.
- Phase tail: an exact phase-only scan over all 4,095 positions with the
  runtime mask, a precomputed reciprocal of the locator derivative, and
  incremental Chien evaluation.
- Assembly and promotion of the exact decoder with a 2× admission gate
  (expected 3.5–7×).
- A separately registered bounded-history lane with priced failures,
  opened only after the exact decoder qualifies.

## Impact

- Code: new `src/qcompile/dqi/{bilinear.py, bm_circuit.py, scan.py}`;
  `src/qcompile/dqi/{tower.py, reversible.py}`; `tools/dqi_prototype.py`,
  `tools/dqi_development.py`, `tools/dqi_decoder_screen.py`.
- Depends on `profile-dqi-reference-stages` for build order and on
  `harden-kaggle-operations` for salt policy and receipts.
- Full-size runs need the cloud VM. The phase-only scan trades Toffolis
  for tens of millions of Clifford gates. Track serialized operations,
  verifier wall time and memory against the reference's 86 million
  operations and 8.7 GiB peak.
